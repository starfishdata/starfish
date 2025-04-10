
import datetime
import uuid
import asyncio
from functools import wraps
from queue import Queue
from typing import Any, Callable, Dict, List
from inspect import signature, Parameter
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn

from starfish.utils.event_loop import run_in_event_loop
from starfish.utils.job_manager import JobManager
from starfish.utils.constants import RECORD_STATUS, TEST_DB_DIR, TEST_DB_URI, RECORD_STATUS_COMPLETED, RECORD_STATUS_DUPLICATE, RECORD_STATUS_FILTERED, RECORD_STATUS_FAILED
from starfish.new_storage.local.local_storage import LocalStorage
from starfish.new_storage.in_memory.in_memory_storage import InMemoryStorage
from starfish.utils.state import MutableSharedState
from starfish.new_storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)


class DataFactory:
    def __init__(
        self,
        storage: str,
        batch_size: int,
        max_concurrency: int,
        target_count: int,
        state: MutableSharedState,
        on_record_complete: List[Callable],
        on_record_error: List[Callable],
        input_converter: Callable,
        show_progress: bool,
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
            "show_progress": show_progress,
        }

        self.project_id = str(uuid.uuid4())
        # self.project_id = "8de05a58-c8a4-4c10-8c23-568679c88e65"
        self.master_job_id = str(uuid.uuid4())
        self.storage = storage
        self.factory_storage = None
        self.storage_setup()
        self.save_project()
        self.job_manager = JobManager(master_job_id=self.master_job_id, job_config=self.job_config, storage=self.factory_storage, 
                                      state=state)

    def __call__(self, func: Callable):
        # self.job_manager.add_job(func)

        @wraps(func)
        def wrapper(*args, **kwargs):

            # todo batches is a list of dicts
            batches = self.input_converter(*args, **kwargs)
            self._check_parameter_match(func, batches)
            self.save_request_config()
            self.log_master_job_start()

            # Process batches in parallel
            output = self._process_batches(func, batches)
            result = []
            for v in output:
                if v.get(RECORD_STATUS) == RECORD_STATUS_COMPLETED:
                    result.append(v.get("output"))
          
            #result = [v for v in output if v.get(RECORD_STATUS) == RecordStatus.COMPLETED]
            # Exception due to all requests failing
            if len(result) == 0:
                raise Exception("No records completed")

            self.complete_master_job()
            self.close_storage()
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
                "master_job_id": self.master_job_id,
                "user_func": func,
                "job_input_queue": batches,
                "target_count": batches.qsize() if target_acount == 0 else target_acount,
            }
        )
        self.update_master_job_status()
        return self.job_manager.run_orchestration()

    async def _save_project(self):
        project = Project(project_id=self.project_id, name="Test Project", description="A test project for storage layer testing")
        await self.factory_storage.save_project(project)

    def save_project(self):
        asyncio.run(self._save_project())
        #return run_in_event_loop(self._save_project())

    async def _save_request_config(self):
        print("\n2. Creating master job...")
        # First save the request config
        config_data = {"generator": "test_generator", "parameters": {"num_records": 10, "complexity": "medium"}}
        self.config_ref = await self.factory_storage.save_request_config(self.master_job_id, config_data)
        print(f"  - Saved request config to: {self.config_ref}")
    
    def save_request_config(self):
        asyncio.run(self._save_request_config())
        #return run_in_event_loop(self._save_request_config())


    async def _log_master_job_start(self):
        # Now create the master job
        master_job = GenerationMasterJob(
            master_job_id=self.master_job_id,
            project_id=self.project_id,
            name="Test Master Job",
            status="pending",
            request_config_ref=self.config_ref,
            output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            storage_uri=TEST_DB_URI,
            target_record_count=10,
        )
        await self.factory_storage.log_master_job_start(master_job)
        print(f"  - Created master job: {master_job.name} ({master_job.master_job_id})")
    
    def log_master_job_start(self):
        asyncio.run(self._log_master_job_start())
        #return run_in_event_loop(self._log_master_job_start())

    async def _update_master_job_status(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        await self.factory_storage.update_master_job_status(self.master_job_id, "running", now)
        print("  - Updated master job status to: running")

    def update_master_job_status(self):
        asyncio.run(self._update_master_job_status())
        #return run_in_event_loop(self._update_master_job_status())
    

    async def _complete_master_job(self):
        #  Complete the master job
        print("\n7. Completing master job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        #todo : how to collect all the execution job status?
        summary = {"completed": 5, "filtered": 0, "duplicate": 0, "failed": 0}
        await self.factory_storage.log_master_job_end(self.master_job_id, "completed", summary, now, now)
        print("  - Marked master job as completed")


    def complete_master_job(self):
        asyncio.run(self._complete_master_job())
        #return run_in_event_loop(self._complete_master_job())

    async def _close_storage(self): 
        await self.factory_storage.close()  

    def close_storage(self):
        asyncio.run(self._close_storage())
        #return run_in_event_loop(self._close_storage())

    def storage_setup(self):
        if self.storage == "local":
            self.factory_storage = LocalStorage(TEST_DB_URI)
            asyncio.run(self.factory_storage.setup())
        else:
            self.factory_storage = InMemoryStorage()
            asyncio.run(self.factory_storage.setup())

    def add_job_status(self):
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("{task.fields[status]}"),
            TimeRemainingColumn(),
        ) if self.show_progress else None
        # Separate task IDs for each counter
        self.progress_task_ids = {
            "completed": None,
            "failed": None,
            "filtered": None,
            "duplicate": None
        }
            


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
    initial_state_values: Dict[str, Any] = {},
    on_record_complete: List[Callable] = [],
    on_record_error: List[Callable] = [],
    show_progress: bool = True,
    input_converter=default_input_converter,
):
    state = MutableSharedState(initial_state_values)    

    return DataFactory(storage, batch_size, max_concurrency, target_count, state, on_record_complete, on_record_error, input_converter=input_converter, show_progress=show_progress)
