import hashlib
import json
from queue import Queue
from typing import Any, Callable, Dict

from starfish.common.logger import get_logger
from starfish.data_factory.constants import (
    RECORD_STATUS,
    STATUS_COMPLETED,
)
from starfish.data_factory.job_manager import JobManager
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.utils.decorator import async_wrapper

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

    def __init__(self, job_config: Dict[str, Any], storage: Storage, user_func: Callable, input_data_queue: Queue = None):
        """Initialize the JobManager with job configuration and storage.

        Args:
            job_config: Dictionary containing job configuration parameters including:
                - max_concurrency: Maximum number of concurrent tasks
                - target_count: Target number of records to generate
                - user_func: Function to execute for each task
                - on_record_complete: List of hooks to run after record completion
                - on_record_error: List of hooks to run on record error
            storage: Storage instance for persisting job results and metadata
            user_func: User-defined function to execute for each task
            input_data_queue: Queue containing input data for the job. Defaults to an empty Queue.
        """
        super().__init__(job_config, storage, user_func, input_data_queue)

    @async_wrapper()
    async def setup_input_output_queue(self):
        """Initialize input/output queues for job rerun.

        This method:
        1. Retrieves the master job and its configuration from storage
        2. Updates job counters with previous run's statistics
        3. Processes input data to identify already completed tasks
        4. Puts completed task outputs into job output queue
        5. Queues remaining tasks for execution

        Raises:
            RuntimeError: If master job cannot be retrieved from storage
        """
        master_job = await self.storage.get_master_job(self.master_job_id)
        if master_job:
            master_job_config_data = await self.storage.get_request_config(master_job.request_config_ref)
            # Convert list to dict with count tracking using hash values
            input_data = master_job_config_data.get("input_data")
            logger.info("\033[1m[JOB RE-RUN START]\033[0m " "\033[33mPICKING UP FROM WHERE THE JOB WAS LEFT OFF...\033[0m\n")
            logger.info(
                f"\033[1m[RE-RUN PROGRESS] STATUS AT THE TIME OF RE-RUN:\033[0m "
                f"\033[32mCompleted: {master_job.completed_record_count} / {len(input_data)}\033[0m | "
                f"\033[31mFailed: {master_job.failed_record_count}\033[0m | "
                f"\033[31mDuplicate: {master_job.duplicate_record_count}\033[0m | "
                f"\033[33mFiltered: {master_job.filtered_record_count}\033[0m"
            )
            # update job manager counters; completed is not included; will be updated in the job manager
            self.total_count = (
                master_job.completed_record_count + master_job.failed_record_count + master_job.duplicate_record_count + master_job.filtered_record_count
            )
            self.failed_count = master_job.failed_record_count
            self.duplicate_count = master_job.duplicate_record_count
            self.filtered_count = master_job.filtered_record_count
            self.completed_count = master_job.completed_record_count
            self.job_config.target_count = len(input_data)
            input_dict = {}
            for item in input_data:
                if isinstance(item, dict):
                    input_data_str = json.dumps(item, sort_keys=True)
                else:
                    input_data_str = str(item)
                input_data_hash = hashlib.sha256(input_data_str.encode()).hexdigest()
                if input_data_hash in input_dict:
                    input_dict[input_data_hash]["count"] += 1
                else:
                    input_dict[input_data_hash] = {"data": item, "data_str": input_data_str, "count": 1}
            for input_data_hash, input_data in input_dict.items():
                runned_tasks = await self.storage.list_execution_jobs_by_master_id_and_config_hash(self.master_job_id, input_data_hash, STATUS_COMPLETED)
                logger.debug("Task already runned, returning output from storage")
                # put the runned tasks output to the job output
                for task in runned_tasks:
                    records_metadata = await self.storage.list_record_metadata(self.master_job_id, task.job_id)
                    record_data_list = []
                    for record in records_metadata:
                        record_data = await self.storage.get_record_data(record.output_ref)
                        record_data_list.append(record_data)

                    output_tmp = {RECORD_STATUS: STATUS_COMPLETED, "output": record_data_list}
                    self.job_output.put(output_tmp)
                    # to prevent db write actions still going on wehn job finished

                # run the rest of the tasks
                logger.debug("Task not runned, running task")
                for _ in range(input_data["count"] - len(runned_tasks)):
                    self.job_input_queue.put(input_data["data"])
        else:
            raise TypeError(f"Master job not found for master_job_id: {self.master_job_id}")
