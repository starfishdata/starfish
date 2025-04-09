
from time import sleep
from typing import Any, Callable, Dict, List


class TaskRunner:
    def __init__(self, max_retries: int = 1):
        self.max_retries = max_retries


    async def run_task(self, func: Callable, input_data: Dict) -> List[Any]:
        """Process a single task with asyncio"""
        retries = 0
        # maybe better to use retries in a single request instead in the batch level.
        while retries <= self.max_retries:
            try:
                # todo if paramter not match, then fail earlier
                output = await func(**input_data)
                return output
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    raise e
                sleep(2**retries)  # exponential backoff
