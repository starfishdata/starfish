
import uuid
from functools import wraps
from queue import Queue
from typing import Any, Callable, Dict, List
from inspect import signature, Parameter
from starfish.utils.job_manager import JobManager
from starfish.utils.enums import RecordStatus
from starfish.utils.constants import RECORD_STATUS

class DataFactory:
    def __init__(
        self,
        storage: str,
        batch_size: int,
        max_concurrency: int,
        target_count: int,
        state: Dict[str, Any],
        on_record_complete: List[Callable],
        on_record_error: List[Callable],
        input_converter: Callable,
    ):
        # self.storage = storage
        self.batch_size = batch_size
        self.input_converter = input_converter
        self.job_config = {
            "max_concurrency": max_concurrency,
            "target_count": target_count,
            "storage": storage,
            "state": state,
            "on_record_complete": on_record_complete,
            "on_record_error": on_record_error,
        }
        # self.batch_counter = 0  # Add batch counter
        self.job_manager = JobManager(job_config=self.job_config, storage=storage, state=state)

    def __call__(self, func: Callable):
        # self.job_manager.add_job(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # self._execute_callbacks('on_start')

            # Get batchable parameters from type hints
            # batchable_params = self._get_batchable_params(func)
            batches = self.input_converter(*args, **kwargs)
            self._check_parameter_match(func, batches)
            # Process batches in parallel
            output = self._process_batches(func, batches)
            result = []
            for v in output:
                if v.get(RECORD_STATUS) == RecordStatus.COMPLETED:
                    result.append(v.get("output_ref"))
          
            #result = [v for v in output if v.get(RECORD_STATUS) == RecordStatus.COMPLETED]
            # Exception due to all requests failing
            if len(result) == 0:
                raise Exception("No records completed")

            self._save_master_job()
            return result
        # Add run method to the wrapped function
        def run(*args, **kwargs):
            return wrapper(*args, **kwargs)

        wrapper.run = run
        wrapper.state = self.job_manager.state
        return wrapper
    
    def _check_parameter_match(self, func: Callable, batches: Queue):
        """Check if the parameters of the function match the parameters of the batches"""
        # Get the parameters of the function
        # func_params = inspect.signature(func).parameters
        # # Get the parameters of the batches
        # batches_params = inspect.signature(batches).parameters
        #from inspect import signature, Parameter
        func_sig = signature(func)
        
        # Validate batch items against function parameters
        batch_item = batches.queue[0]
        for param_name, param in func_sig.parameters.items():
            # Skip if parameter has a default value
            if param.default is not Parameter.empty:
                continue
            # Check if required parameter is missing in batch
            if param_name not in batch_item:
                raise TypeError(
                    f"Batch item is missing required parameter '{param_name}' "
                    f"for function {func.__name__}"
                )
        # Check 2: Ensure all batch parameters exist in function signature
        for batch_param in batch_item.keys():
            if batch_param not in func_sig.parameters:
                raise TypeError(
                    f"Batch items contains unexpected parameter '{batch_param}' "
                    f"not found in function {func.__name__}"
                )
            
    def _process_batches(self, func: Callable, batches: Queue) -> List[Any]:
        """Process batches with asyncio"""
        
        target_acount = self.job_config.get("target_count")
        self.job_manager.update_job_config(
            {
                "master_job_id": str(uuid.uuid4()),
                "user_func": func,
                "job_input_queue": batches,
                "target_count": batches.qsize() if target_acount == 0 else target_acount,
            }
        )
        return self.job_manager.run_orchestration()

    # def _store_results(self, results: List[Any]):
    #     """Handle storage based on configured option"""
    #     if self.storage == 'filesystem':
    #         os.makedirs('data_factory_output', exist_ok=True)
    #         with open('data_factory_output/results.json', 'w') as f:
    #             json.dump(results, f)
    #     elif self.storage == 's3':
    #         # Add AWS S3 integration here
    #         pass


    def _save_master_job(self):
        pass


def default_input_converter(data : List[Dict[str, Any]]=[], **kwargs) -> Queue[Dict[str, Any]]:
    # Determine parallel sources
    parallel_sources = {}
    if isinstance(data, list) and len(data) > 0:
        parallel_sources["data"] = data
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
        if "data" in parallel_sources:
            record.update(parallel_sources["data"][i])

        # Add parallel kwargs
        for key in parallel_sources:
            if key != "data":
                record[key] = parallel_sources[key][i]

        # Add broadcast kwargs
        for key, value in kwargs.items():
            if not isinstance(value, (list, tuple)):
                record[key] = value

        results.put(record)

    return results


# Public decorator interface
def data_factory(
    storage: str = "filesystem",
    batch_size: int = 1,
    target_count: int = 0,
    max_concurrency: int = 50,
    state: Dict[str, Any] = {},
    on_record_complete: List[Callable] = [],
    on_record_error: List[Callable] = [],
    input_converter=default_input_converter,
):
    return DataFactory(storage, batch_size, max_concurrency, target_count, state, on_record_complete, on_record_error, input_converter=input_converter)
