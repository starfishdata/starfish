import asyncio
import time
from typing import Any, Callable, Dict, List
from starfish.common.logger import get_logger
logger = get_logger(__name__)

class TaskRunner:
    def __init__(self, max_retries: int = 1, timeout: int = 30):
        self.max_retries = max_retries
        self.timeout = timeout


    async def run_task(self, func: Callable, input_data: Dict) -> List[Any]:
        """Process a single task with asyncio"""
        retries = 0
        start_time = time.time()
        # maybe better to use retries in a single request instead in the batch level.
        while retries <= self.max_retries:
            try:
                output = await asyncio.wait_for(func(**input_data), timeout=self.timeout)
                logger.debug(f"Task execution completed in {time.time() - start_time:.2f} seconds")
                return output
            except asyncio.TimeoutError as timeout_error:
                logger.error(f"Task execution timed out after {self.timeout} seconds")
                raise TimeoutError(f"Task execution timed out after {self.timeout} seconds") from timeout_error
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Task execution failed after {self.max_retries} retries")
                    raise e
                await asyncio.sleep(2**retries)  # exponential backoff
