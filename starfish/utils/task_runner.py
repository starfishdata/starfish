import asyncio
from time import sleep
from typing import Any, Callable, Dict, List

from starfish.utils.event_loop import run_in_event_loop


class TaskRunner:
    def __init__(self, storage_option: str = "filesystem", batch_size: int = 100):
        self.storage_option = storage_option
        self.callbacks = {
            "on_task_start": None,
            "on_task_complete": None,
            "on_task_error": None,
        }

    # def _process_batches(self, func: Callable, batches: List[Dict]) -> List[Any]:
    #     """Process batches with ThreadPoolExecutor"""
    #     results = []
    #     with ThreadPoolExecutor() as executor:
    #         futures = [executor.submit(func, **batch) for batch in batches]

    #         for future in futures:
    #             try:
    #                 batch_result = future.result()
    #                 results.extend(batch_result)
    #                 self._execute_callbacks('on_batch_complete', batch_result)
    #             except Exception as e:
    #                 self._execute_callbacks('on_error', e)
    #     return results

    async def _async_run_batches(self, func: Callable, batches: List[Dict]) -> List[Any]:
        """Process batches with asyncio"""
        results = []
        tasks = [asyncio.create_task(func(**batch)) for batch in batches]

        for task in tasks:
            try:
                batch_result = await task
                results.extend(batch_result)

                self._execute_callbacks("on_task_complete", batch_result)
            except Exception as e:
                err_str = str(e)
                results.append(err_str)
                self._execute_callbacks("on_task_error", str(e))
        return results

    def run_batches(self, func: Callable, batches: List[Dict]) -> List[Any]:
        """Process batches with asyncio"""
        return run_in_event_loop(self._async_run_batches(func=func, batches=batches))

    async def run_task(self, func: Callable, input_data: Dict) -> List[Any]:
        """Process a single task with asyncio"""
        retries = 0
        max_retries = 0
        # maybe better to use retries in a single request instead in the batch level.
        while retries <= max_retries:
            try:
                output = await func(**input_data)
                return output

            except Exception as e:
                retries += 1
                if retries > max_retries:
                    raise e
                sleep(2**retries)  # exponential backoff

    def add_callback(self, event: str, callback: Callable):
        """Register callback functions"""
        if event in self.callbacks:
            self.callbacks[event] = callback

    def _execute_callbacks(self, event: str, *args):
        """Trigger registered callbacks"""
        if callback := self.callbacks.get(event):
            callback(*args)
