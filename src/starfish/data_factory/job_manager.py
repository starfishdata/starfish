import asyncio
import copy
import datetime
import hashlib
import json
import uuid
from queue import Queue
from typing import Any, Callable, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory.config import PROGRESS_LOG_INTERVAL
from starfish.data_factory.constants import (
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
from starfish.data_factory.utils.decorator import async_wrapper
from starfish.data_factory.utils.errors import TimeoutErrorAsyncio

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
    """

    def __init__(self, master_job_config: FactoryMasterConfig, storage: Storage, user_func: Callable, input_data_queue: Queue = None):
        """Initialize the JobManager with job configuration and storage.

        Args:
            master_job_config (FactoryMasterConfig): Configuration for the master job
            storage (Storage): Storage instance for persisting job results and metadata
            user_func (Callable): Function to execute for each task
            input_data_queue (Queue, optional): Queue for input data. Defaults to None.
        """
        self.master_job_id = master_job_config.master_job_id
        self.job_config = FactoryJobConfig(
            batch_size=master_job_config.batch_size,
            target_count=master_job_config.target_count,
            show_progress=master_job_config.show_progress,
            user_func=user_func,
            run_mode=master_job_config.run_mode,
            max_concurrency=master_job_config.max_concurrency,
            on_record_complete=master_job_config.on_record_complete,
            on_record_error=master_job_config.on_record_error,
            job_run_stop_threshold=master_job_config.job_run_stop_threshold,
        )
        self.storage = storage
        self.state = master_job_config.state
        self.semaphore = asyncio.Semaphore(master_job_config.max_concurrency)
        self.lock = asyncio.Lock()
        self.task_runner = TaskRunner(timeout=master_job_config.task_runner_timeout)
        self.job_input_queue = input_data_queue if input_data_queue else Queue()
        # it shall be a thread safe queue
        self.job_output = Queue()
        # Job counters
        self.completed_count = 0
        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.active_operations = set()
        self._progress_ticker_task = None

    @async_wrapper()
    async def setup_input_output_queue(self):
        """Initialize and configure the input and output queues for the job.

        This method is responsible for setting up the necessary queues for job processing.
        It prepares the input queue for task data and the output queue for results.
        """
        pass

    async def _create_execution_job(self, job_uuid: str, input_data: Dict[str, Any]):
        """Create and log a new execution job in storage.

        Args:
            job_uuid: Unique identifier for the execution job
            input_data: Dictionary containing input data for the job
        """
        logger.debug("\n3. Creating execution job...")
        input_data_str = json.dumps(input_data)
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

    async def _cancel_operations(self):
        for task in self.active_operations:
            task.cancel()
        await asyncio.gather(*self.active_operations, return_exceptions=True)

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
        counts = {
            STATUS_COMPLETED: num_records,
            STATUS_FILTERED: num_records,
            STATUS_DUPLICATE: num_records,
            STATUS_FAILED: num_records,
        }
        await self.storage.log_execution_job_end(job_uuid, status, counts, now, now)
        logger.debug("  - Marked execution job as completed")

    def _is_job_to_stop(self) -> bool:
        queue_size = len(self.job_output.queue)
        if queue_size == 0:
            return False

        items_check = list(self.job_output.queue)[-min(self.job_config.job_run_stop_threshold, queue_size) :]
        consecutive_not_completed = len(items_check) == self.job_config.job_run_stop_threshold and all(
            item[RECORD_STATUS] != STATUS_COMPLETED for item in items_check
        )
        # consecutive_not_completed and
        completed_tasks_reach_target = self.completed_count >= self.job_config.target_count
        if consecutive_not_completed:
            logger.error(f"consecutive_not_completed: in {self.job_config.job_run_stop_threshold} times, stopping job")

        return consecutive_not_completed or completed_tasks_reach_target
        # return completed_tasks_reach_target or (total_tasks_reach_target and consecutive_not_completed)

    def run_orchestration(self):
        """Start the job orchestration process.

        This method initiates the main event loop for processing tasks, managing concurrency,
        and handling task completion. It runs until either the target count is reached or
        the stop threshold is triggered.
        """
        run_in_event_loop(self._async_run_orchestration())

    async def _progress_ticker(self):
        """Log a message every 5 seconds."""
        while not self._is_job_to_stop():
            logger.info(
                f"[JOB PROGRESS] "
                f"\033[32mCompleted: {self.completed_count}/{self.job_config.target_count}\033[0m | "
                f"\033[33mRunning: {self.job_config.max_concurrency - self.semaphore._value}\033[0m | "
                f"\033[36mAttempted: {self.total_count}\033[0m"
                f"    (\033[32mCompleted: {self.completed_count}\033[0m, "
                f"\033[31mFailed: {self.failed_count}\033[0m, "
                f"\033[35mFiltered: {self.filtered_count}\033[0m, "
                f"\033[34mDuplicate: {self.duplicate_count}\033[0m)"
            )
            await asyncio.sleep(PROGRESS_LOG_INTERVAL)

    async def _del_progress_ticker(self):
        """Delete the progress ticker."""
        # Ensure the ticker task is cancelled when the orchestration ends
        if self._progress_ticker_task:
            self._progress_ticker_task.cancel()
            try:
                await self._progress_ticker_task
            except asyncio.CancelledError:
                pass

    async def _del_running_tasks(self):
        # Cancel all running tasks
        # todo whether openai call will close
        for task in self.running_tasks:
            task.cancel()
        # Wait for all tasks to be cancelled
        await asyncio.gather(*self.running_tasks, return_exceptions=True)

    async def _async_run_orchestration(self):
        """Main asynchronous orchestration loop for the job.

        This method manages the core job execution loop, including:
        - Starting the progress ticker
        - Processing tasks from the input queue
        - Managing concurrency with semaphores
        - Handling task completion and cleanup
        """
        # Start the ticker task
        if self.job_config.show_progress:
            self._progress_ticker_task = asyncio.create_task(self._progress_ticker())
        # Store all running tasks
        self.running_tasks = set()

        try:
            while not self._is_job_to_stop():
                logger.debug("Job is not to stop, checking job input queue")
                if not self.job_input_queue.empty():
                    logger.debug("Job input queue is not empty, acquiring semaphore")
                    await self.semaphore.acquire()
                    logger.debug("Semaphore acquired, waiting for task to complete")
                    input_data = self.job_input_queue.get()
                    task = self._create_single_task(input_data)
                    self.running_tasks.add(task)
                    task.add_done_callback(self.running_tasks.discard)
                else:
                    await asyncio.sleep(1)
        finally:
            await self._del_progress_ticker()

            await self._del_running_tasks()

            await self._cancel_operations()

    def _create_single_task(self, input_data) -> asyncio.Task:
        task = asyncio.create_task(self._run_single_task(input_data))
        asyncio.create_task(self._handle_task_completion(task))
        logger.debug("Task created, waiting for task to complete")
        return task

    async def _run_single_task(self, input_data) -> List[Dict[str, Any]]:
        """Run a single task with error handling and storage.

        Args:
            input_data: Input data for the task

        Returns:
            Dict[str, Any]: Dictionary containing:
                - RECORD_STATUS: Status of the task (completed, failed, etc.)
                - output_ref: List of storage references for the output
                - output: The actual output data from the task
        """
        output = []
        output_ref = []
        task_status = STATUS_COMPLETED

        try:
            # Execute the main task
            output = await self.task_runner.run_task(self.job_config.user_func, input_data)

            hooks_output = []
            for hook in self.job_config.on_record_complete:
                hooks_output.append(hook(output, self.state))
            if hooks_output.count(STATUS_DUPLICATE) > 0:
                # duplicate filtered need retry
                task_status = STATUS_DUPLICATE
            elif hooks_output.count(STATUS_FILTERED) > 0:
                task_status = STATUS_FILTERED

            output_ref = await self._save_record_data(copy.deepcopy(output), task_status, input_data)

        except (Exception, TimeoutErrorAsyncio) as e:
            logger.error(f"Error running task: {e}")
            # Run error hooks
            for hook in self.job_config.on_record_error:
                hook(str(e), self.state)
            # async with self.lock:  # Acquire lock for status update
            task_status = STATUS_FAILED

        # Handle incomplete tasks
        if task_status != STATUS_COMPLETED:
            logger.debug(f"Task is not completed as {task_status}, putting input data back to the job input queue")
            # async with self.lock:  # Acquire lock for queue operation
            self.job_input_queue.put(input_data)

        return {RECORD_STATUS: task_status, "output_ref": output_ref, "output": output}

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
            self.job_output.put(result)
            self.total_count += 1
            task_status = result[RECORD_STATUS]
            # Update counters based on task status
            if task_status == STATUS_COMPLETED:
                self.completed_count += 1
            elif task_status == STATUS_DUPLICATE:
                self.duplicate_count += 1
            elif task_status == STATUS_FILTERED:
                self.filtered_count += 1
            else:
                self.failed_count += 1
            # await self._update_progress(task_status, STATUS_MOJO_MAP[task_status])
            self.semaphore.release()
