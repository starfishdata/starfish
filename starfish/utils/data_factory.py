import os
import json
import inspect
import asyncio
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Any, Union
from starfish.utils.event_loop import run_in_event_loop
#from starfish.utils.job_manager import JobManager
class DataFactory:
    def __init__(self, storage_option: str = 'filesystem', batch_size: int = 100):
        self.storage_option = storage_option
        self.batch_size = batch_size
        self.callbacks = {
            'on_start': None,
            'on_batch_complete': None,
            'on_error': None
        }
        self.batch_counter = 0  # Add batch counter

    def __call__(self, func: Callable):
        #self.job_manager.add_job(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            self._execute_callbacks('on_start')
            
            # Get batchable parameters from type hints
            batchable_params = self._get_batchable_params(func)
            
            # Prepare batches
            batches = self._create_batches(func, batchable_params, *args, **kwargs)
            
            # Process batches in parallel
            results = self._process_batches(func, batches)
            
            # Store final results
            self._store_results(results)
            
            return results

        # Add callback registration methods
        wrapper.add_callback = self.add_callback
        return wrapper
    
    #def run(self, func: Callable, *args, **kwargs):
        

    def _get_batchable_params(self, func: Callable) -> List[str]:
        """Identify parameters with List type hints"""
        type_hints = inspect.get_annotations(func)
        #and param != "return"
        keys = [
            param for param, hint in type_hints.items()
            if getattr(hint, '__origin__', None) is list 
        ]
        if len(keys) == 0:
            raise ValueError("No batchable parameters found")
        return [keys[0]]

    def _create_batches(self, func: Callable, batchable_params: List[str], 
                      *args, **kwargs) -> List[Dict[str, Any]]:
        """Split batchable parameters into chunks"""
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        batches = []
        for param in batchable_params:
            values = bound_args.arguments[param]
            for i in range(0, len(values), self.batch_size):
                batch_args = bound_args.arguments.copy()
                batch_args[param] = values[i:i+self.batch_size]
                batches.append(batch_args)
        return batches

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

    async def _async_process_batches(self, func: Callable, batches: List[Dict]) -> List[Any]:
        """Process batches with asyncio"""
        results = []
        tasks = [asyncio.create_task(func(**batch)) for batch in batches]
        
        for task in tasks:
            try:
                batch_result = await task
                results.extend(batch_result)
                batch_id = self._generate_batch_id()  # Generate batch ID
                # stored the input data for each batch 
                cached_data = []
                for result in batch_result:
                    # city
                    cached_data.append(result[0]['question'])
                self._execute_callbacks('on_batch_complete', ",".join(cached_data), batch_id)  # Pass batch ID
            except Exception as e:
                batch_id = self._generate_batch_id()  # Generate batch ID even for errors
                self._execute_callbacks('on_error', str(e), batch_id)  # Pass batch ID
        return results
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        self.batch_counter += 1
        return f"batch_{self.batch_counter:04d}"
    
    def _process_batches(self, func: Callable, batches: List[Dict]) -> List[Any]:
        """Process batches with asyncio"""
        return run_in_event_loop(self._async_process_batches(
            func=func,
            batches=batches
        ))
        

    def _store_results(self, results: List[Any]):
        """Handle storage based on configured option"""
        if self.storage_option == 'filesystem':
            os.makedirs('data_factory_output', exist_ok=True)
            with open('data_factory_output/results.json', 'w') as f:
                json.dump(results, f)
        elif self.storage_option == 's3':
            # Add AWS S3 integration here
            pass

    def add_callback(self, event: str, callback: Callable):
        """Register callback functions"""
        if event in self.callbacks:
            self.callbacks[event] = callback

    def _execute_callbacks(self, event: str, *args):
        """Trigger registered callbacks"""
        if callback := self.callbacks.get(event):
            callback(*args)

# Public decorator interface
def data_factory(storage_option: str = 'filesystem', batch_size: int = 100):
    return DataFactory(storage_option, batch_size)