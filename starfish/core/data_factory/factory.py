import datetime
import uuid
import asyncio
import json
import hashlib
from functools import wraps
from queue import Queue
from typing import Any, Callable, Dict, List
from inspect import signature, Parameter
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn
from starfish.core.data_factory.event_loop import run_in_event_loop
from starfish.core.data_factory.job_manager import JobManager
from starfish.core.data_factory.constants import RECORD_STATUS, RUN_MODE_DRY_RUN, STATUS_MOJO_MAP, STATUS_TOTAL, TASK_RUNNER_TIMEOUT, TEST_DB_DIR, TEST_DB_URI, STATUS_COMPLETED, STATUS_DUPLICATE, STATUS_FILTERED, STATUS_FAILED, RUN_MODE, RUN_MODE_RE_RUN, RUN_MODE_NORMAL, PROGRESS_LOG_INTERVAL
from starfish.core.data_factory.storage.local.local_storage import LocalStorage
from starfish.core.data_factory.storage.in_memory.in_memory_storage import InMemoryStorage
from starfish.core.data_factory.state import MutableSharedState
from starfish.core.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)
from starfish.core.common.decorator import storage_action
from starfish.core.common.logger import get_logger
logger = get_logger(__name__)


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
        task_runner_timeout: int,
    ):
        # self.storage = storage
        self.batch_size = batch_size
        self.input_converter = input_converter
        self.input_data = Queue()
        self.job_config = {
            "max_concurrency": max_concurrency,
            "target_count": target_count,
            "state": state,
            "on_record_complete": on_record_complete,   
            "on_record_error": on_record_error,
            "show_progress": show_progress,
            "task_runner_timeout": task_runner_timeout,
        }

        self.storage = storage
        self.factory_storage = None
        self.func = None
        self.master_job_id = None

    def __call__(self, func: Callable):
        # self.job_manager.add_job(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            run_mode = self.job_config.get(RUN_MODE)
            err = None
            try:
                
                # Check for master_job_id in kwargs and assign if present
                if run_mode == RUN_MODE_RE_RUN:
                    self._setup_storage_and_job_manager()
                    self._set_input_data_from_master_job()
                    
                    self._init_progress_bar_update_job_config()
                elif run_mode == RUN_MODE_DRY_RUN:
                    # dry run mode
                    self.input_data = self.input_converter(*args, **kwargs)
                    # Get only first item but maintain Queue structure
                    first_item = self.input_data.get()
                    self.input_data = Queue()
                    self.input_data.put(first_item)
                    self._check_parameter_match()
                    self.job_manager = JobManager(job_config=self.job_config, storage=self.factory_storage)
                    self._update_job_config()
                else:
                    self.input_data = self.input_converter(*args, **kwargs)
                    self._check_parameter_match()
                    self.project_id = str(uuid.uuid4())
                    # self.project_id = "8de05a58-c8a4-4c10-8c23-568679c88e65"
                    self.master_job_id = str(uuid.uuid4())
                    self._setup_storage_and_job_manager()
                    self._save_project() 
                    self._save_request_config()
                    self._log_master_job_start()
                    # Start progress bar before any operations
                    # Process batches and keep progress bar alive
                    self._init_progress_bar_update_job_config()
                    self._update_master_job_status()
                
                self._process_batches()
                
                result = self._process_output()
                if len(result) == 0:
                    raise ValueError("No records generated")
                return result
            except TypeError as e:
                err = e
                logger.error(f"TypeError occurred: {str(e)}")
                raise
            except ValueError as e:
                err = e
                logger.error(f"ValueError occurred: {str(e)}")
                raise
            finally:
                # Only execute finally block if not TypeError
                if err is  None and run_mode != RUN_MODE_DRY_RUN:
                    self._complete_master_job()
                    self._close_storage()
                    self.show_job_progress_status()
        # Add run method to the wrapped function
        def run(*args, **kwargs):
            if 'master_job_id' in kwargs:
                # re_run mode
                self.master_job_id = kwargs['master_job_id']
                self.job_config[RUN_MODE] = RUN_MODE_RE_RUN
            return wrapper(*args, **kwargs)
        def dry_run(*args, **kwargs):
            self.job_config[RUN_MODE] = RUN_MODE_DRY_RUN
            return wrapper(*args, **kwargs)

        wrapper.run = run
        wrapper.re_run = run
        wrapper.dry_run = dry_run
        wrapper.state = self.job_config.get("state")
        self.func = func
        return wrapper
    
    def _process_output(self) -> List[Any]:
        result = []
        output = self.job_manager.job_output.queue
        for v in output:
            if v.get(RECORD_STATUS) == STATUS_COMPLETED:
                result.extend(v.get("output"))
        return result
    
    def _check_parameter_match(self):
        """Check if the parameters of the function match the parameters of the batches"""
        # Get the parameters of the function
        # func_params = inspect.signature(func).parameters
        # # Get the parameters of the batches
        # batches_params = inspect.signature(batches).parameters
        #from inspect import signature, Parameter
        func_sig = signature(self.func)
        
        # Validate batch items against function parameters
        batch_item = self.input_data.queue[0]
        for param_name, param in func_sig.parameters.items():
            # Skip if parameter has a default value
            if param.default is not Parameter.empty:
                continue
            # Check if required parameter is missing in batch
            if param_name not in batch_item:
                raise TypeError(
                    f"Batch item is missing required parameter '{param_name}' "
                    f"for function {self.func.__name__}"
                )
        # Check 2: Ensure all batch parameters exist in function signature
        for batch_param in batch_item.keys():
            if batch_param not in func_sig.parameters:
                raise TypeError(
                    f"Batch items contains unexpected parameter '{batch_param}' "
                    f"not found in function {self.func.__name__}"
                )
            
    
    def _setup_storage_and_job_manager(self):
        self.storage_setup()
        
        self.job_manager = JobManager(job_config=self.job_config, storage=self.factory_storage)

    def _process_batches(self) -> List[Any]:
        """Process batches with asyncio"""
        logger.info(f"Job started. Master Job ID: {self.master_job_id}. Logging progress every {PROGRESS_LOG_INTERVAL} seconds.")
        return self.job_manager.run_orchestration()
        

    @storage_action()
    async def _save_project(self):
        project = Project(project_id=self.project_id, name="Test Project", description="A test project for storage layer testing")
        await self.factory_storage.save_project(project)

    @storage_action()
    async def _save_request_config(self):
        logger.debug("\n2. Creating master job...")
        # First save the request config
        config_data = {"generator": "test_generator", "parameters": {"num_records": 10, "complexity": "medium"}, "input_data": list(self.input_data.queue)}
        self.config_ref = await self.factory_storage.save_request_config(self.master_job_id, config_data)
        logger.debug(f"  - Saved request config to: {self.config_ref}")
    

    @storage_action()
    async def _set_input_data_from_master_job(self):
        master_job = await self.factory_storage.get_master_job(self.master_job_id)
        if master_job:
            master_job_config_data = await self.factory_storage.get_request_config(master_job.request_config_ref)
            # Convert list to dict with count tracking using hash values
            input_data  = master_job_config_data.get("input_data")
        
            input_dict = {}
            for item in input_data:
                self.input_data.put(item)
                if isinstance(item, dict):
                    input_data_str = json.dumps(item, sort_keys=True)
                else:
                    input_data_str = str(item)
                input_data_hash = hashlib.sha256(input_data_str.encode()).hexdigest()
                if input_data_hash in input_dict:
                    input_dict[input_data_hash]["count"] += 1
                else:
                    input_dict[input_data_hash] = {
                        "data": item,
                        "data_str": input_data_str,
                        "count": 1
                    }
            self.job_config["input_dict"] = input_dict
            self.job_config[RUN_MODE] = RUN_MODE_RE_RUN


    @storage_action()
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
        logger.debug(f"  - Created master job: {master_job.name} ({self.master_job_id})")
    

    @storage_action()
    async def _update_master_job_status(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        await self.factory_storage.update_master_job_status(self.master_job_id, "running", now)
        logger.debug("  - Updated master job status to: running")

  

    @storage_action()
    async def _complete_master_job(self):
        #  Complete the master job
        logger.debug("\n7. Completing master job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        #todo : how to collect all the execution job status?
        summary = {STATUS_COMPLETED: self.job_manager.completed_count,
                    STATUS_FILTERED: self.job_manager.filtered_count,
                    STATUS_DUPLICATE: self.job_manager.duplicate_count,
                    STATUS_FAILED: self.job_manager.failed_count}
        await self.factory_storage.log_master_job_end(self.master_job_id, STATUS_COMPLETED, summary, now, now)
        logger.info(f"Master job {self.master_job_id} as completed")


    @storage_action()
    async def _close_storage(self): 
        await self.factory_storage.close()  


    def storage_setup(self):
        if self.storage == "local":
            self.factory_storage = LocalStorage(TEST_DB_URI)
            asyncio.run(self.factory_storage.setup())
        else:
            self.factory_storage = InMemoryStorage()
            asyncio.run(self.factory_storage.setup())

    def _init_progress_bar_update_job_config(self):
        self._update_job_config()
        self._init_progress_bar()
        

    def _update_job_config(self):
        target_acount = self.job_config.get("target_count")
        new_target_count = self.input_data.qsize() if target_acount == 0 else target_acount
        self.job_config.update({"target_count": new_target_count})
        self.job_manager.update_job_config(
            {
                "master_job_id": self.master_job_id,
                "user_func": self.func,
                "job_input_queue": self.input_data, 
                "target_count": new_target_count,
                RUN_MODE: self.job_config.get(RUN_MODE),
                "input_dict": self.job_config.get("input_dict"),
            }
        )
    

    def _init_progress_bar(self):
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            # BarColumn(),
            # TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("{task.fields[status]}"),
            # TimeRemainingColumn(),
        ) if self.job_config.get("show_progress") else None
        # Separate task IDs for each counter
        self.progress_tasks = {
            STATUS_COMPLETED: None,
            STATUS_FAILED: None,
            STATUS_FILTERED: None,
            STATUS_DUPLICATE: None,
            STATUS_TOTAL: None
        }
        if self.job_config.get("show_progress"):
            #self.progress.start()
            #with self.progress_lock:
            target_count = self.job_config.get("target_count")
            self.progress_tasks[STATUS_COMPLETED] = self.progress.add_task(
                "[green]Completed", total=target_count, status="✅ 0"
            )
            self.progress_tasks[STATUS_FAILED] = self.progress.add_task(
                "[red]Failed", total=target_count, status="❌ 0"
            )
            self.progress_tasks[STATUS_FILTERED] = self.progress.add_task(
                "[yellow]Filtered", total=target_count, status="🚫 0"
            )
            self.progress_tasks[STATUS_DUPLICATE] = self.progress.add_task(
                "[cyan]Duplicated", total=target_count, status="🔁 0"
            )
            # self.progress_tasks[STATUS_TOTAL] = self.progress.add_task(
            #     "[white]Attempted", total=target_count, status="📊 0"
            # )
            # self.job_config["progress"] = self.progress
            # self.job_config["progress_tasks"] = self.progress_tasks
            
    
    def show_job_progress_status(self):
        target_count = self.job_config.get("target_count")
        logger.info(f"Job finished. Final Stats: Completed: {self.job_manager.completed_count}/{target_count} | Attempted: {self.job_manager.total_count} (Failed: {self.job_manager.failed_count}, Filtered: {self.job_manager.filtered_count}, Duplicate: {self.job_manager.duplicate_count})")
        if self.job_config.get("show_progress"):
            self.progress.start()
            
            for counter_type, task_id in self.progress_tasks.items():
                count = getattr(self.job_manager, f"{counter_type}_count")
                emoji = STATUS_MOJO_MAP[counter_type]
                percentage = int((count / target_count) * 100) if target_count > 0 else 0
                if counter_type != STATUS_COMPLETED:
                    target_count = self.job_manager.total_count
                self.progress.update(
                    task_id, 
                    completed=count, 
                    status=f"{emoji} {count}/{target_count} ({percentage}%)"
                )
            self.progress.stop()


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
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT,
):
    state = MutableSharedState(initial_state_values)    

    return DataFactory(storage, batch_size, max_concurrency, target_count, state, on_record_complete, on_record_error, input_converter=input_converter, show_progress=show_progress, task_runner_timeout=task_runner_timeout)
