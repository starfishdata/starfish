import asyncio
import copy
import datetime
import hashlib
import json
import uuid
from asyncio import Queue
from typing import Any, Callable, Dict, List
import traceback

from starfish.common.logger import get_logger
from starfish.data_factory.config import PROGRESS_LOG_INTERVAL
from starfish.data_factory.constants import (
    IDX,
    RECORD_STATUS,
    RUN_MODE_DRY_RUN,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
)
from starfish.data_factory.event_loop import run_in_event_loop
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.storage.models import GenerationJob, Record
from starfish.data_factory.task_runner import TaskRunner
from starfish.data_factory.utils.data_class import FactoryJobConfig, FactoryMasterConfig
from starfish.data_factory.utils.errors import TimeoutErrorAsyncio
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)


class JobManager:
    """Manages the execution of data generation jobs.

    This class handles the orchestration of tasks, including task execution,
    progress tracking, and result storage. It manages concurrency and provides
    mechanisms for job monitoring and control.

    Attributes:
        master_job_id (str): ID of the master job
        job_config (FactoryJobConfig): Configuration for the job
        storage (Storage): Storage instance for persisting results
        state (dict): Current state of the job
        semaphore (asyncio.Semaphore): Semaphore for concurrency control
        lock (asyncio.Lock): Lock for thread-safe operations
        task_runner (TaskRunner): Runner for executing tasks
        job_input_queue (Queue): Queue for input data
        job_output (Queue): Queue for output data
        completed_count (int): Count of completed tasks
        duplicate_count (int): Count of duplicate tasks
        filtered_count (int): Count of filtered tasks
        failed_count (int): Count of failed tasks
        total_count (int): Total number of tasks attempted
        job_run_stop_threshold (int): Threshold for stopping job
        active_operations (set): Set of active operations
        _progress_ticker_task (asyncio.Task): Task for progress logging
        dead_queue (Queue): Queue for failed tasks
        task_failure_count (dict): Track failure count per task
    """

    # ====================
    # Initialization
    # ====================
    def __init__(
        self, master_job_config: FactoryMasterConfig, state: MutableSharedState, storage: Storage, user_func: Callable, input_data_queue: Queue = None
    ):
        """Initialize the JobManager with job configuration and storage.

        Args:
            master_job_config (FactoryMasterConfig): Configuration for the master job
            state (MutableSharedState): Shared state object for job state management
            storage (Storage): Storage instance for persisting job results and metadata
            user_func (Callable): Function to execute for each task
            input_data_queue (Queue, optional): Queue for input data. Defaults to None.
        """
        self.master_job_id = master_job_config.master_job_id
        self.job_config = FactoryJobConfig(
            batch_size=master_job_config.batch_size,
            target_count=master_job_config.target_count,
            dead_queue_threshold=master_job_config.dead_queue_threshold,
            show_progress=master_job_config.show_progress,
            user_func=user_func,
            run_mode=master_job_config.run_mode,
            max_concurrency=master_job_config.max_concurrency,
            on_record_complete=master_job_config.on_record_complete,
            on_record_error=master_job_config.on_record_error,
            job_run_stop_threshold=master_job_config.job_run_stop_threshold,
        )
        self.storage = storage
        self.state = state
        self.task_runner = TaskRunner(timeout=master_job_config.task_runner_timeout)
        self.job_input_queue = input_data_queue if input_data_queue else Queue()
        self.job_output = Queue()
        self.prev_job = master_job_config.prev_job
        # Initialize counters
        self._initialize_counters()
        self.active_operations = set()
        self._progress_ticker_task = None
        self.execution_time = 0
        self.err_type_counter = {}
        self.dead_queue = Queue()  # Add dead queue for failed tasks
        self.task_failure_count = {}  # Track failure count per task

    def _initialize_counters(self):
        """Initialize all job counters."""
        self.completed_count = 0
        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.dead_queue_count = 0

    async def setup_input_output_queue(self):
        pass

    # ====================
    # Job Execution
    # ====================
    def run_orchestration(self):
        """Start the job orchestration process.

        This method initiates the main event loop for processing tasks, managing concurrency,
        and handling task completion. It runs until either the target count is reached or
        the stop threshold is triggered.
        """
        start_time = datetime.datetime.now(datetime.timezone.utc)
        run_in_event_loop(self._async_run_orchestration())
        self.execution_time = int((datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds())

    async def _async_run_orchestration(self):
        """Main asynchronous orchestration loop for the job.

        This method manages the core job execution loop, including:
        - Starting the progress ticker
        - Processing tasks from the input queue
        - Managing concurrency with semaphores
        - Handling task completion and cleanup
        """
        self._initialize_concurrency_controls()

        if self.job_config.show_progress:
            self._progress_ticker_task = asyncio.create_task(self._progress_ticker())

        self.running_tasks = set()

        try:
            if not self.job_input_queue.empty():
                await self._process_tasks()
        finally:
            await self._cleanup()

    def _initialize_concurrency_controls(self):
        """Initialize semaphore and lock for concurrency control."""
        if hasattr(self, "semaphore"):
            del self.semaphore
        if hasattr(self, "lock"):
            del self.lock
        self.semaphore = asyncio.Semaphore(self.job_config.max_concurrency)
        self.lock = asyncio.Lock()

    async def _process_tasks(self):
        """Process tasks from the input queue until stop condition is met."""
        while not self._is_job_to_stop():
            if not self.job_input_queue.empty():
                await self.semaphore.acquire()
                input_data = await self.job_input_queue.get()
                task = self._create_single_task(input_data)
                self.running_tasks.add(task)
                task.add_done_callback(self.running_tasks.discard)
            else:
                await asyncio.sleep(1)

    # ====================
    # Task Management
    # ====================
    def _create_single_task(self, input_data) -> asyncio.Task:
        """Create and manage a single task."""
        task = asyncio.create_task(self._run_single_task(input_data))
        asyncio.create_task(self._handle_task_completion(task))
        return task

    async def _run_single_task(self, input_data) -> List[Dict[str, Any]]:
        """Execute a single task with error handling."""
        output = []
        output_ref = []
        task_status = STATUS_COMPLETED
        err_output = {}
        input_data_idx = input_data.get(IDX, None)
        if input_data_idx == None:
            logger.warning(f"found an input_data without index ")

        try:
            output = await self.task_runner.run_task(self.job_config.user_func, input_data, input_data_idx)
            task_status = self._evaluate_task_output(output)
            output_ref = await self._save_record_data(copy.deepcopy(output), task_status, input_data)
        except (Exception, TimeoutErrorAsyncio) as e:
            task_status, err_output = self._handle_task_error(e)

        if task_status != STATUS_COMPLETED:
            await self._requeue_task(input_data, input_data_idx)

        return self._create_task_result(input_data_idx, task_status, output_ref, output, err_output)

    def _evaluate_task_output(self, output):
        """Evaluate task output and determine status."""
        hooks_output = [hook(output, self.state) for hook in self.job_config.on_record_complete]
        if STATUS_DUPLICATE in hooks_output:
            return STATUS_DUPLICATE
        if STATUS_FILTERED in hooks_output:
            return STATUS_FILTERED
        return STATUS_COMPLETED

    def _handle_task_error(self, error):
        """Handle task errors and update state."""
        err_str = str(error)
        # [-1]
        err_trace = traceback.format_exc().splitlines()
        logger.error(f"Error running task: {err_str}")

        for hook in self.job_config.on_record_error:
            hook(err_str, self.state)

        return STATUS_FAILED, {"err_str": err_str, "err_trace": err_trace}

    async def _requeue_task(self, input_data, input_data_idx):
        """Requeue a task that needs to be retried or move to dead queue if failed too many times."""
        task_key = str(input_data_idx)
        async with self.lock:
            self.task_failure_count[task_key] = self.task_failure_count.get(task_key, 0) + 1
            if self.task_failure_count[task_key] >= self.job_config.dead_queue_threshold:
                await self.dead_queue.put(input_data)
                self.dead_queue_count += 1
                logger.warning(f"Task {task_key} failed 3 times, moving to dead queue")
            else:
                await self.job_input_queue.put(input_data)
                logger.debug(f"Requeuing task {task_key} (failure count: {self.task_failure_count[task_key]})")

    def _create_task_result(self, input_data_idx, task_status, output_ref, output, err_output):
        """Create a standardized task result dictionary."""
        return {IDX: input_data_idx, RECORD_STATUS: task_status, "output_ref": output_ref, "output": output, "err": [err_output]}

    async def _handle_task_completion(self, task):
        """Handle task completion and update counters.

        Args:
            task (asyncio.Task): The completed task

        Updates:
            - Job counters (completed, failed, etc.)
            - Output queue
            - Semaphore
        """
        result = await task
        async with self.lock:
            await self.job_output.put(result)
            self.total_count += 1
            task_status = result.get(RECORD_STATUS)
            # Update counters based on task status
            if task_status == STATUS_COMPLETED:
                self.completed_count += 1
            elif task_status == STATUS_DUPLICATE:
                self.duplicate_count += 1
            elif task_status == STATUS_FILTERED:
                self.filtered_count += 1
            elif task_status == STATUS_FAILED:
                self.failed_count += 1
                # Safely extract error information with better type checking
                err_output = result.get("err", [{}])[0]  # Default to empty dict if no error
                err_str = err_output.get("err_str", "Unknown error").strip()  # Clean up whitespace

                # Normalize error string for consistent counting
                normalized_err = err_str.lower().strip()
                self.err_type_counter[normalized_err] = self.err_type_counter.get(normalized_err, 0) + 1
                # Optionally log the error count for this type
                logger.debug(f"Error type '{normalized_err}' count: {self.err_type_counter[normalized_err]}")
            # await self._update_progress(task_status, STATUS_MOJO_MAP[task_status])
            self.semaphore.release()

    # ====================
    # Cleanup & Utilities
    # ====================
    async def _cleanup(self):
        """Clean up resources after job completion."""
        await self._del_progress_ticker()
        await self._del_running_tasks()
        await self._cancel_operations()

    async def _del_running_tasks(self):
        """Cancel all running tasks."""
        for task in self.running_tasks:
            task.cancel()
        await asyncio.gather(*self.running_tasks, return_exceptions=True)

    async def _cancel_operations(self):
        """Cancel all active operations."""
        for task in self.active_operations:
            task.cancel()
        await asyncio.gather(*self.active_operations, return_exceptions=True)

    async def _create_execution_job(self, job_uuid: str, input_data: Dict[str, Any]):
        """Create and log a new execution job in storage.

        Args:
            job_uuid: Unique identifier for the execution job
            input_data: Dictionary containing input data for the job
        """
        logger.debug("\n3. Creating execution job...")
        input_data_str = json.dumps(input_data, sort_keys=True) if isinstance(input_data, dict) else str(input_data)
        # input_data_str = json.dumps(input_data)
        self.job = GenerationJob(
            job_id=job_uuid,
            master_job_id=self.master_job_id,
            status="pending",
            worker_id="test-worker-1",
            run_config=input_data_str,
            run_config_hash=hashlib.sha256(input_data_str.encode()).hexdigest(),
        )
        await self.storage.log_execution_job_start(self.job)
        logger.debug(f"  - Created execution job: {job_uuid}")

    async def _save_record_data(self, *args, **kwargs):
        task = asyncio.create_task(self._job_save_record_data(*args, **kwargs))
        self.active_operations.add(task)
        try:
            return await task
        finally:
            self.active_operations.discard(task)

    async def _job_save_record_data(self, records, task_status: str, input_data: Dict[str, Any]) -> List[str]:
        output_ref_list = []
        if self.job_config.run_mode == RUN_MODE_DRY_RUN:
            return output_ref_list
        logger.debug("\n5. Saving record data...")
        storage_class_name = self.storage.__class__.__name__
        if storage_class_name == "LocalStorage":
            job_uuid = str(uuid.uuid4())
            await self._create_execution_job(job_uuid, input_data)
            for i, record in enumerate(records):
                record_uid = str(uuid.uuid4())
                output_ref = await self.storage.save_record_data(record_uid, self.master_job_id, job_uuid, record)
                record["job_id"] = job_uuid
                record["master_job_id"] = self.master_job_id
                record["status"] = task_status
                record["output_ref"] = output_ref
                record["end_time"] = datetime.datetime.now(datetime.timezone.utc)
                record_model = Record(**record)
                await self.storage.log_record_metadata(record_model)
                logger.debug(f"  - Saved data for record {i}: {output_ref}")
                output_ref_list.append(output_ref)
            await self._complete_execution_job(job_uuid, status=task_status, num_records=len(records))
        return output_ref_list

    async def _complete_execution_job(self, job_uuid: str, status: str, num_records: int):
        logger.debug("\n6. Completing execution job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        completed_num_records = 0
        fitered_num_records = 0
        duplicated_num_records = 0
        if status == STATUS_COMPLETED:
            completed_num_records = num_records
        elif status == STATUS_FILTERED:
            fitered_num_records = num_records
        elif status == STATUS_DUPLICATE:
            duplicated_num_records = num_records

        counts = {
            STATUS_COMPLETED: completed_num_records,
            STATUS_FILTERED: fitered_num_records,
            STATUS_DUPLICATE: duplicated_num_records,
        }
        await self.storage.log_execution_job_end(job_uuid, status, counts, now, now)
        logger.debug("  - Marked execution job as completed")

    def _is_job_to_stop(self) -> bool:
        # Immutable Snapshot: Creates a snapshot of the queue at the time of the list() call, so modifications to the queue during iteration won't affect the loop.
        job_output_list = list(self.job_output._queue)
        queue_size = len(job_output_list)
        if queue_size == 0:
            return False

        items = []
        for _ in range(min(self.job_config.job_run_stop_threshold, queue_size)):
            items.append(job_output_list[-1])

        consecutive_not_completed = len(items) == self.job_config.job_run_stop_threshold and all(item[RECORD_STATUS] != STATUS_COMPLETED for item in items)

        if consecutive_not_completed:
            logger.error(
                f"consecutive_not_completed: in {self.job_config.job_run_stop_threshold} times, "
                f"stopping this job; please adjust factory config and input data then "
                f"resume_from_checkpoint({self.master_job_id})"
            )
        target_not_reach_count = self.job_config.target_count - self.completed_count
        completed_tasks_reach_target = target_not_reach_count <= 0
        if target_not_reach_count > 0 and target_not_reach_count == self.dead_queue_count:
            logger.warning(f"there are {target_not_reach_count} input data not able to process, pls remove them")
            completed_tasks_reach_target = True

        return consecutive_not_completed or completed_tasks_reach_target

    # ====================
    # Progress Tracking
    # ====================
    async def _progress_ticker(self):
        """Log job progress at regular intervals."""
        while not self._is_job_to_stop():
            """Format and log the current job progress."""
            logger.info(
                f"[JOB PROGRESS] "
                f"\033[32mCompleted: {self.completed_count}/{self.job_config.target_count}\033[0m | "
                f"\033[33mRunning: {self.job_config.max_concurrency - self.semaphore._value}\033[0m | "
                f"\033[36mAttempted: {self.total_count}\033[0m"
                f"    (\033[32mCompleted: {self.completed_count}\033[0m, "
                f"\033[31mFailed: {self.failed_count}\033[0m, "
                f"\033[35mFiltered: {self.filtered_count}\033[0m, "
                f"\033[34mDuplicate: {self.duplicate_count}\033[0m, "
                f"\033[1;31mInDeadQueue: {self.dead_queue_count}\033[0m)"
            )
            await asyncio.sleep(PROGRESS_LOG_INTERVAL)

    async def _del_progress_ticker(self):
        """Safely stop the progress ticker."""
        if self._progress_ticker_task:
            self._progress_ticker_task.cancel()
            try:
                await self._progress_ticker_task
            except asyncio.CancelledError:
                pass

    # reserve this function for reference
    # async def _async_run_orchestration_3_11(self):
    #     """Main asynchronous orchestration loop for the job.

    #     This method manages the core job execution loop, including:
    #     - Starting the progress ticker
    #     - Processing tasks from the input queue
    #     - Managing concurrency with semaphores
    #     - Handling task completion and cleanup
    #     """
    #     # Start the ticker task
    #     if self.job_config.show_progress:
    #         self._progress_ticker_task = asyncio.create_task(self._progress_ticker())

    #     try:
    #         async with asyncio.TaskGroup() as tg:
    #             while not self._is_job_to_stop():
    #                 logger.debug("Job is not to stop, checking job input queue")
    #                 if not self.job_input_queue.empty():
    #                     logger.debug("Job input queue is not empty, acquiring semaphore")
    #                     await self.semaphore.acquire()
    #                     logger.debug("Semaphore acquired, waiting for task to complete")
    #                     input_data = self.job_input_queue.get()
    #                     task = tg.create_task(self._run_single_task(input_data))
    #                     asyncio.create_task(self._handle_task_completion(task))
    #     finally:
    #         await self._del_progress_ticker()
    #         await self._cancel_operations()
