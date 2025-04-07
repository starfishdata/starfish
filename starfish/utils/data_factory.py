import os
import json
import inspect
from functools import wraps
from typing import Callable, Dict, List, Any, Union
import uuid
from queue import Queue
from starfish.utils.job_manager import JobManager
class DataFactory:
    def __init__(self, storage: str, batch_size: int,max_concurrency:int,
                 target_count:int,state:Dict[str,Any],on_record_complete:List[Callable],
                 on_record_error:List[Callable],input_converter:Callable):
        # self.storage = storage
        self.batch_size = batch_size
        self.input_converter = input_converter
        self.job_config={
                'max_concurrency':max_concurrency,
                'target_count':target_count,
                'storage':storage,
                'state':state,
                'on_record_complete':on_record_complete,
                'on_record_error':on_record_error
            }
        # self.batch_counter = 0  # Add batch counter
        self.job_manager = JobManager(

            job_config=self.job_config,
            storage=storage,state=state)
        
    def __call__(self, func: Callable):
        #self.job_manager.add_job(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            #self._execute_callbacks('on_start')
            
            # Get batchable parameters from type hints
            #batchable_params = self._get_batchable_params(func)
            batches = self.input_converter(*args, **kwargs)
            # batches = Queue()
            # for data in converted_data:
            #     batches.put(data)

            # Prepare batches
            #batches = self._create_batches(func, batchable_params, *args, **kwargs)
            
            # Process batches in parallel
            self._process_batches(func, batches)

            self._save_master_job()
            
            # Store final results
            #self._store_results(results)
            
            #return results
        # Add run method to the wrapped function
        def run(*args, **kwargs):
            return wrapper(*args, **kwargs) 
        wrapper.run = run
        wrapper.state = self.job_manager.state
        return wrapper
    
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
                      *args, **kwargs) -> Queue[Dict[str, Any]]:
        """Split batchable parameters into chunks"""
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        batches = Queue()
        for param in batchable_params:
            values = bound_args.arguments[param]
            for i in range(0, len(values), self.batch_size):
                batch_args = bound_args.arguments.copy()
                batch_args[param] = values[i:i+self.batch_size]
                batches.put(batch_args)

        return batches
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        self.batch_counter += 1
        return f"batch_{self.batch_counter:04d}"
    
    def _process_batches(self, func: Callable, batches: Queue) -> List[Any]:
        """Process batches with asyncio"""
        target_acount = self.job_config.get('target_count')
        self.job_manager.update_job_config({
            'master_job_id':str(uuid.uuid4()) ,
            "user_func":func,
            "job_input_queue":batches,
            "target_count": batches.qsize() if target_acount == 0 else target_acount
        })
        self.job_manager.run_orchestration()
        
    # def _store_results(self, results: List[Any]):
    #     """Handle storage based on configured option"""
    #     if self.storage == 'filesystem':
    #         os.makedirs('data_factory_output', exist_ok=True)
    #         with open('data_factory_output/results.json', 'w') as f:
    #             json.dump(results, f)
    #     elif self.storage == 's3':
    #         # Add AWS S3 integration here
    #         pass

    def add_callback(self, event: str, callback: Callable):
        """Register callback functions"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _execute_callbacks(self, event: str, *args):
        """Trigger registered callbacks"""
        if callbacks := self.callbacks.get(event):
            for callback in callbacks:
                callback(*args)
    
    def _on_start(self):
        """Initialize job statistics"""
        pass

    def _on_complete(self, batch_result):
        """Update stats and cache successful batches"""
        
        self._execute_callbacks('on_batch_complete', batch_result)

    def _on_error(self, error :str):
        """Handle failed batches"""
        self._execute_callbacks('on_error', error)

    def _on_record_complete(self, data: Any):
        """Handle record completion"""
        self._execute_callbacks('on_record_complete', data)

    def _save_master_job(self):
        
        pass



def default_input_converter(data, **kwargs) -> Queue[Dict[str, Any]]:
    # Determine parallel sources
    parallel_sources = {}
    if isinstance(data, list):
        parallel_sources['data'] = data
    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)):
            parallel_sources[key] = value

    # Validate parallel sources have same length
    lengths = [len(v) for v in parallel_sources.values()]
    if len(set(lengths)) > 1:
        raise ValueError("All parallel sources must have the same length")

    # Determine batch size (L)
    batch_size = lengths[0] if lengths else 1

    # Prepare results
    results = Queue()
    for i in range(batch_size):
        record = {}
        
        # Add data if exists
        if 'data' in parallel_sources:
            record.update(parallel_sources['data'][i])
        
        # Add parallel kwargs
        for key in parallel_sources:
            if key != 'data':
                record[key] = parallel_sources[key][i]
        
        # Add broadcast kwargs
        for key, value in kwargs.items():
            if not isinstance(value, (list, tuple)):
                record[key] = value
        
        results.put(record)
    
    return results

# Public decorator interface
def data_factory(storage: str = 'filesystem',
                  batch_size: int = 1,
                  target_count:int=0,
                  max_concurrency:int=50,
                  state:Dict[str,Any]={},
                  on_record_complete:List[Callable]=[],
                  on_record_error:List[Callable]=[],
                  input_converter=default_input_converter
                  ):
    return DataFactory(storage, batch_size,max_concurrency,target_count,state,on_record_complete,
                       on_record_error, input_converter = input_converter)