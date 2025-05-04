import hashlib
import json
from queue import Queue
from typing import Any, Callable, Dict
import copy  # Added this import at the top of the file

from starfish.common.logger import get_logger
from starfish.data_factory.constants import (
    IDX,
    RECORD_STATUS,
    STATUS_COMPLETED,
)
from starfish.data_factory.job_manager import JobManager
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)


class JobManagerRerun(JobManager):
    """Manages the re-execution of data generation jobs from where they left off.

    This class extends JobManager to handle job reruns by:
    - Retrieving previous job state from storage
    - Skipping already completed tasks
    - Continuing execution of incomplete tasks
    - Maintaining accurate counters for completed/failed/duplicate/filtered records

    Args:
        job_config (Dict[str, Any]): Configuration dictionary containing job parameters
            including max_concurrency, target_count, and task configurations.
        storage (Storage): Storage instance for persisting job results and metadata.
        user_func (Callable): User-defined function to execute for each task.
        input_data_queue (Queue, optional): Queue containing input data for the job.
            Defaults to an empty Queue.

    Attributes:
        Inherits all attributes from JobManager and adds:
        - total_count (int): Total records processed in previous run
        - failed_count (int): Failed records from previous run
        - duplicate_count (int): Duplicate records from previous run
        - filtered_count (int): Filtered records from previous run
        - completed_count (int): Completed records from previous run
    """

    def __init__(self, job_config: Dict[str, Any], state: MutableSharedState, storage: Storage, user_func: Callable, input_data_queue: Queue = None):
        """Initialize the JobManager with job configuration and storage.

        Args:
            job_config: Dictionary containing job configuration parameters including:
                - max_concurrency: Maximum number of concurrent tasks
                - target_count: Target number of records to generate
                - user_func: Function to execute for each task
                - on_record_complete: List of hooks to run after record completion
                - on_record_error: List of hooks to run on record error
            state: MutableSharedState instance for storing job state
            storage: Storage instance for persisting job results and metadata
            user_func: User-defined function to execute for each task
            input_data_queue: Queue containing input data for the job. Defaults to an empty Queue.
        """
        # self.setup_input_output_queue()
        super().__init__(job_config, state, storage, user_func, input_data_queue)

    async def setup_input_output_queue(self):
        """Initialize input/output queues for job resume."""
        # Extract and clean up previous job data
        input_data = self._extract_previous_job_data()
        master_job = self._extract_master_job()

        # Log resume status
        self._log_resume_status(master_job, input_data)

        # Initialize counters from previous run
        self._initialize_counters_rerun(master_job, len(input_data))

        # Process input data and handle completed tasks
        input_dict = self._process_input_data(input_data)
        await self._handle_completed_tasks(input_dict)

        # Queue remaining tasks for execution
        self._queue_remaining_tasks(input_dict)

    def _extract_previous_job_data(self) -> list:
        """Extract and clean up previous job data."""
        # input_data = copy.deepcopy(self.prev_job["input_data"])
        # no need to deepcopy as it is a separate object from original_input_data in factory
        input_data = self.prev_job["input_data"]
        del self.prev_job["input_data"]
        return input_data

    def _extract_master_job(self):
        """Extract and clean up master job reference."""
        master_job = self.prev_job["master_job"]
        del self.prev_job["master_job"]
        del self.prev_job
        return master_job

    def _log_resume_status(self, master_job, input_data: list) -> None:
        """Log the status of the job at resume time."""
        logger.info("\033[1m[JOB RESUME START]\033[0m \033[33mPICKING UP FROM WHERE THE JOB WAS LEFT OFF...\033[0m\n")
        logger.info(
            f"\033[1m[RESUME PROGRESS] STATUS AT THE TIME OF RESUME:\033[0m "
            f"\033[32mCompleted: {master_job.completed_record_count} / {len(input_data)}\033[0m | "
            f"\033[31mFailed: {master_job.failed_record_count}\033[0m | "
            f"\033[31mDuplicate: {master_job.duplicate_record_count}\033[0m | "
            f"\033[33mFiltered: {master_job.filtered_record_count}\033[0m"
        )

    def _initialize_counters_rerun(self, master_job, input_data_length: int) -> None:
        """Initialize counters from previous run."""
        self.total_count = (
            master_job.completed_record_count + master_job.failed_record_count + master_job.duplicate_record_count + master_job.filtered_record_count
        )
        self.failed_count = master_job.failed_record_count
        self.duplicate_count = master_job.duplicate_record_count
        self.filtered_count = master_job.filtered_record_count
        self.completed_count = master_job.completed_record_count
        self.job_config.target_count = input_data_length

    def _process_input_data(self, input_data: list) -> dict:
        """Process input data and create a hash map for tracking."""
        input_dict = {}
        idx = 0  # Initialize external counter to avoid use enumerate
        for item in input_data:
            # Create a deep copy of the item to avoid modifying the original
            # item_copy = {k: v for k, v in item.items() if k != IDX}

            input_data_str = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
            input_data_hash = hashlib.sha256(input_data_str.encode()).hexdigest()

            if input_data_hash in input_dict:
                input_dict[input_data_hash]["count"].append(idx)
            else:
                input_dict[input_data_hash] = {"data": item, "data_str": input_data_str, "count": [idx]}
            idx += 1  # Increment counter after processing each item
        return input_dict

    async def _handle_completed_tasks(self, input_dict: dict) -> None:
        """Handle already completed tasks by retrieving their outputs from storage."""
        for input_data_hash, item in input_dict.items():
            completed_tasks = await self.storage.list_execution_jobs_by_master_id_and_config_hash(self.master_job_id, input_data_hash, STATUS_COMPLETED)

            if not completed_tasks:
                continue

            logger.debug("Task already run, returning output from storage")
            await self._process_completed_tasks(completed_tasks, item)

    async def _process_completed_tasks(self, completed_tasks: list, item: dict) -> None:
        """Process completed tasks and add their outputs to the job queue."""
        record_idx = None
        idx_list = item["count"]
        logger.debug(idx_list)
        for task in completed_tasks:
            records_metadata = await self.storage.list_record_metadata(self.master_job_id, task.job_id)
            record_data_list = await self._get_record_data(records_metadata)
            try:
                idx_list = item["count"]
                logger.debug(idx_list)
                # logger.info("the item['count'] is ======= %s", item["count"])
                # if len(idx_list) > 0:
                record_idx = item["count"].pop()
                logger.debug(record_idx)
                output_tmp = {IDX: record_idx, RECORD_STATUS: STATUS_COMPLETED, "output": record_data_list}
            except Exception as e:
                logger.error(e)
            self.job_output.put(output_tmp)

    async def _get_record_data(self, records_metadata: list) -> list:
        """Retrieve record data from storage."""
        record_data_list = []
        for record in records_metadata:
            record_data = await self.storage.get_record_data(record.output_ref)
            record_data_list.append(record_data)
        return record_data_list

    def _queue_remaining_tasks(self, input_dict: dict) -> None:
        """Queue remaining tasks for execution."""
        for item in input_dict.values():
            # item["count"] is mutable, already updated in process_complete by deducting
            # the completed tasks
            remaining_count = len(item["count"])
            if remaining_count > 0:
                logger.debug("Task not run, queuing for execution")
                try:
                    for _ in range(remaining_count):
                        item["data"][IDX] = item["count"].pop()
                        self.job_input_queue.put(item["data"])
                except Exception as e:
                    logger.error(str(e))

    def pop_from_list(ls: list):
        try:
            return ls.pop()
        except Exception as e:
            logger.error(str(e))
