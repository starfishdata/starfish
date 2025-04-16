import asyncio
import datetime
import hashlib
import json
import uuid
from queue import Queue
from typing import Any, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory.config import MAX_CONCURRENT_TASKS, PROGRESS_LOG_INTERVAL
from starfish.data_factory.constants import (
    RECORD_STATUS,
    RUN_MODE,
    RUN_MODE_DRY_RUN,
    RUN_MODE_RE_RUN,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
)
from starfish.data_factory.event_loop import run_in_event_loop
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.storage.models import GenerationJob, Record
from starfish.data_factory.task_runner import TaskRunner

logger = get_logger(__name__)


class JobManager:
    """Manages the execution of data generation jobs.

    This class handles the orchestration of tasks, including task execution,
    progress tracking, and result storage. It manages concurrency and provides
    mechanisms for job monitoring and control.

    Args:
        job_config (Dict[str, Any]): Configuration dictionary containing job parameters
            including max_concurrency, target_count, and task configurations.
        storage (Storage): Storage instance for persisting job results and metadata.
    """

    def __init__(self, job_config: Dict[str, Any], storage: Storage):
        """Initialize the JobManager with job configuration and storage.

        Args:
            job_config: Dictionary containing job configuration parameters including:
                - max_concurrency: Maximum number of concurrent tasks
                - target_count: Target number of records to generate
                - user_func: Function to execute for each task
                - on_record_complete: List of hooks to run after record completion
                - on_record_error: List of hooks to run on record error
            storage: Storage instance for persisting job results and metadata
        """
        self.job_config = job_config
        self.storage = storage
        self.state = job_config.get("state", {})
        self.semaphore = asyncio.Semaphore(job_config.get("max_concurrency", MAX_CONCURRENT_TASKS))
        self.lock = asyncio.Lock()
        self.task_runner = TaskRunner(timeout=job_config.get("task_runner_timeout"))
        self.job_input_queue = Queue()
        # it shall be a thread safe queue
        self.job_output = Queue()
        # Job counters
        self.completed_count = 0
        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.job_run_stop_threshold = 3

    async def create_execution_job(self, job_uuid: str, input_data: Dict[str, Any]):
        """Create and log a new execution job in storage.

        Args:
            job_uuid: Unique identifier for the execution job
            input_data: Dictionary containing input data for the job
        """
        logger.debug("\n3. Creating execution job...")
        input_data_str = json.dumps(input_data)
        self.job = GenerationJob(
            job_id=job_uuid,
            master_job_id=self.job_config["master_job_id"],
            status="running",
            worker_id="test-worker-1",
            run_config=input_data_str,
            run_config_hash=hashlib.sha256(input_data_str.encode()).hexdigest(),
        )
        await self.storage.log_execution_job_start(self.job)
        logger.debug(f"  - Created execution job: {job_uuid}")

    async def _job_save_record_data(self, records, task_status: str, input_data: Dict[str, Any]) -> List[str]:
        output_ref_list = []
        if self.job_config.get(RUN_MODE) == RUN_MODE_DRY_RUN:
            return output_ref_list
        logger.debug("\n5. Saving record data...")
        storage_class_name = self.storage.__class__.__name__
        if storage_class_name == "LocalStorage":
            job_uuid = str(uuid.uuid4())
            await self.create_execution_job(job_uuid, input_data)
            for i, record in enumerate(records):
                record_uid = str(uuid.uuid4())
                output_ref = await self.storage.save_record_data(record_uid, self.job_config["master_job_id"], job_uuid, record)
                record["job_id"] = job_uuid
                record["master_job_id"] = self.job_config["master_job_id"]
                record["status"] = task_status
                record["output_ref"] = output_ref
                record["end_time"] = datetime.datetime.now(datetime.timezone.utc)
                record_model = Record(**record)
                await self.storage.log_record_metadata(record_model)
                logger.debug(f"  - Saved data for record {i}: {output_ref}")
                output_ref_list.append(output_ref)
            await self._complete_execution_job(job_uuid)
        return output_ref_list

    async def _complete_execution_job(self, job_uuid: str):
        logger.debug("\n6. Completing execution job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        counts = {
            STATUS_COMPLETED: self.completed_count,
            STATUS_FILTERED: self.filtered_count,
            STATUS_DUPLICATE: self.duplicate_count,
            STATUS_FAILED: self.failed_count,
        }
        await self.storage.log_execution_job_end(job_uuid, STATUS_COMPLETED, counts, now, now)
        logger.debug("  - Marked execution job as completed")

    def _is_job_to_stop(self) -> bool:
        items_check = list(self.job_output.queue)[-1 * self.job_run_stop_threshold :]
        consecutive_not_completed = len(items_check) == self.job_run_stop_threshold and all(item[RECORD_STATUS] != STATUS_COMPLETED for item in items_check)
        # consecutive_not_completed and
        completed_tasks_reach_target = self.completed_count >= self.target_count
        # total_tasks_reach_target = (self.total_count >= self.target_count)
        return consecutive_not_completed or completed_tasks_reach_target
        # return completed_tasks_reach_target or (total_tasks_reach_target and consecutive_not_completed)

    def run_orchestration(self):
        """Process batches with asyncio."""
        self.job_input_queue = self.job_config["job_input_queue"]
        self.target_count = self.job_config.get("target_count")
        run_mode = self.job_config.get(RUN_MODE)
        if run_mode == RUN_MODE_RE_RUN:
            self.job_input_queue = Queue()
            run_in_event_loop(self._async_run_orchestration_re_run())
        elif run_mode == RUN_MODE_DRY_RUN:
            run_in_event_loop(self._async_run_orchestration())
        else:
            run_in_event_loop(self._async_run_orchestration())

    async def _async_run_orchestration_re_run(self):
        input_dict = self.job_config.get("input_dict", {})
        for input_data_hash, input_data in input_dict.items():
            runned_tasks = await self.storage.list_execution_jobs_by_master_id_and_config_hash(
                self.job_config["master_job_id"], input_data_hash, STATUS_COMPLETED
            )
            logger.debug("Task already runned, returning output from storage")
            # put the runned tasks output to the job output
            for task in runned_tasks:
                records_metadata = await self.storage.list_record_metadata(self.job_config["master_job_id"], task.job_id)
                for record in records_metadata:
                    record_data = await self.storage.get_record_data(record.output_ref)
                    output_tmp = {RECORD_STATUS: STATUS_COMPLETED, "output": record_data}
                    self.job_output.put(output_tmp)
                    self.total_count += 1
                    self.completed_count += 1
            # run the rest of the tasks
            logger.debug("Task not runned, running task")
            for _ in range(input_data["count"] - len(runned_tasks)):
                self.job_input_queue.put(input_data["data"])
                # self._create_single_task(input_data["data"])
        await self._async_run_orchestration()

    async def _progress_ticker(self):
        """Log a message every 5 seconds."""
        while not self._is_job_to_stop():
            logger.info(
                f"[JOB PROGRESS] "
                f"\033[32mCompleted: {self.completed_count}/{self.target_count}\033[0m | "
                f"\033[33mRunning: {self.job_config.get('max_concurrency') - self.semaphore._value}\033[0m | "
                f"\033[36mAttempted: {self.total_count}\033[0m"
                f"    (\033[32mCompleted: {self.completed_count}\033[0m, "
                f"\033[31mFailed: {self.failed_count}\033[0m, "
                f"\033[35mFiltered: {self.filtered_count}\033[0m, "
                f"\033[34mDuplicate: {self.duplicate_count}\033[0m)"
            )
            await asyncio.sleep(PROGRESS_LOG_INTERVAL)

    async def _async_run_orchestration(self):
        """Main orchestration loop for the job."""
        # Start the ticker task
        _progress_ticker_task = asyncio.create_task(self._progress_ticker())
        # Store all running tasks
        running_tasks = set()

        try:
            while not self._is_job_to_stop():
                logger.debug("Job is not to stop, checking job input queue")
                if not self.job_input_queue.empty():
                    logger.debug("Job input queue is not empty, acquiring semaphore")
                    await self.semaphore.acquire()
                    logger.debug("Semaphore acquired, waiting for task to complete")
                    input_data = self.job_input_queue.get()
                    task = self._create_single_task(input_data)
                    running_tasks.add(task)
                    task.add_done_callback(running_tasks.discard)
                else:
                    await asyncio.sleep(1)
        finally:
            # Ensure the ticker task is cancelled when the orchestration ends
            _progress_ticker_task.cancel()
            try:
                await _progress_ticker_task
            except asyncio.CancelledError:
                pass

            # Cancel all running tasks
            # todo whether openai call will close
            for task in running_tasks:
                task.cancel()
            # Wait for all tasks to be cancelled
            await asyncio.gather(*running_tasks, return_exceptions=True)

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
            Dictionary containing task status, output references, and output data
        """
        output = []
        output_ref = []
        task_status = STATUS_COMPLETED

        try:
            # Execute the main task
            output = await self.task_runner.run_task(self.job_config["user_func"], input_data)

            # Run completion hooks
            hooks_output = [hook(output, self.state) for hook in self.job_config.get("on_record_complete", [])]

            # Determine task status based on hooks
            if STATUS_DUPLICATE in hooks_output:
                task_status = STATUS_DUPLICATE
            elif STATUS_FILTERED in hooks_output:
                task_status = STATUS_FILTERED

            # Save record data if task was successful
            if task_status == STATUS_COMPLETED:
                output_ref = await self._job_save_record_data(output.copy(), task_status, input_data)

        except Exception as e:
            logger.error(f"Error running task: {e}")
            # Run error hooks
            for hook in self.job_config.get("on_record_error", []):
                hook(str(e), self.state)
            task_status = STATUS_FAILED

        # Handle incomplete tasks
        if task_status != STATUS_COMPLETED:
            logger.debug(f"Task is not completed as {task_status}, putting input data back to the job input queue")
            self.job_input_queue.put(input_data)

        return {RECORD_STATUS: task_status, "output_ref": output_ref, "output": output}

    async def _handle_task_completion(self, task):
        """Handle task completion and update counters."""
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

    def _prepare_next_input(self):
        """Prepare input data for the next task."""
        # Implementation depends on specific use case
        pass

    def update_job_config(self, job_config: Dict[str, Any]):
        """Update job config by merging new values with existing config."""
        self.job_config = {**self.job_config, **job_config}
