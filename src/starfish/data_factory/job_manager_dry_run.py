from asyncio import Queue
from typing import Any, Callable, Dict

from starfish.common.logger import get_logger
from starfish.data_factory.job_manager import JobManager
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)


class JobManagerDryRun(JobManager):
    """Manages dry-run execution of data generation jobs.

    This class extends JobManager to handle job dry runs by:
    - Limiting execution to a single task
    - Preventing actual storage of results
    - Providing a way to test job execution without side effects

    Args:
        master_job_config (Dict[str, Any]): Configuration dictionary containing job parameters
            including max_concurrency, target_count, and task configurations.
        storage (Storage): Storage instance (results won't be persisted).
        user_func (Callable): User-defined function to execute for the test task.
        input_data_queue (Queue, optional): Queue containing input data for the job.
            Defaults to None.

    Attributes:
        Inherits all attributes from JobManager.
    """

    def __init__(self, master_job_config: Dict[str, Any], state: MutableSharedState, storage: Storage, user_func: Callable, input_data_queue: Queue = None):
        """Initialize the JobManager with job configuration and storage.

        Args:
            master_job_config: Dictionary containing job configuration parameters including:
                - max_concurrency: Maximum number of concurrent tasks
                - target_count: Target number of records to generate
                - user_func: Function to execute for each task
                - on_record_complete: List of hooks to run after record completion
                - on_record_error: List of hooks to run on record error
            state: MutableSharedState instance for storing job state
            storage: Storage instance for persisting job results and metadata
            user_func: User-defined function to execute for each task
            input_data_queue: Queue containing input data for the job. Defaults to None.
        """
        super().__init__(master_job_config, state, storage, user_func, input_data_queue)

    async def setup_input_output_queue(self):
        """Initialize input/output queues for dry run.

        This method:
        1. Takes a single item from the input queue
        2. Creates a new queue with just that item
        3. Sets target count to 1 for single task execution

        Note:
            The dry run will only process one task regardless of the input queue size.
        """
        first_item = await self.job_input_queue.get()
        self.job_input_queue = Queue()
        await self.job_input_queue.put(first_item)
        self.job_config.target_count = 1
