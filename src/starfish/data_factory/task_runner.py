import asyncio
import time
from typing import Any, Callable, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory.config import TASK_RUNNER_TIMEOUT
from starfish.data_factory.utils.errors import TimeoutErrorAsyncio

logger = get_logger(__name__)


# from starfish.common.logger_new import logger
class TaskRunner:
    """A task runner that executes asynchronous tasks with retry logic and timeout handling.

    Attributes:
        max_retries: Maximum number of retry attempts for failed tasks
        timeout: Maximum execution time allowed for each task
        master_job_id: Optional identifier for the parent job
    """

    def __init__(self, max_retries: int = 1, timeout: int = TASK_RUNNER_TIMEOUT, master_job_id: str = None):
        """Initializes the TaskRunner with configuration parameters.

        Args:
            max_retries: Maximum number of retry attempts (default: 1)
            timeout: Timeout in seconds for task execution (default: TASK_RUNNER_TIMEOUT)
            master_job_id: Optional identifier for the parent job (default: None)
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.master_job_id = master_job_id

    async def run_task(self, func: Callable, input_data: Dict) -> List[Any]:
        """Process a single task with asyncio."""
        retries = 0
        start_time = time.time()
        result = None
        # maybe better to use retries in a single request instead in the batch level.
        while retries <= self.max_retries:
            try:
                result = await asyncio.wait_for(func(**input_data), timeout=self.timeout)
                logger.debug(f"Task execution completed in {time.time() - start_time:.2f} seconds")
                break
            except asyncio.TimeoutError as timeout_error:
                logger.error(
                    f"Task execution timed out after {self.timeout} seconds, "
                    "please set the timeout in data_factory decorator like this: "
                    "task_runner_timeout=60"
                )
                raise TimeoutErrorAsyncio(f"Task execution timed out after {self.timeout} seconds") from timeout_error
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    # logger.error(f"Task execution failed after {self.max_retries} retries")
                    raise e
                await asyncio.sleep(2**retries)  # exponential backoff

        return result
