import asyncio
import datetime
from os import environ
import uuid
from inspect import Parameter, signature
from queue import Queue
from typing import Any, Callable, Dict, Generic, List, Optional, ParamSpec, TypeVar, cast, Protocol
# from types import MappingProxyType

import cloudpickle
from starfish.data_factory.utils.errors import InputError, OutputError, NoResumeSupportError
from starfish.data_factory.utils.util import get_platform_name
from starfish.version import __version__
from starfish.common.logger import get_logger
from starfish.data_factory.config import NOT_COMPLETED_THRESHOLD, PROGRESS_LOG_INTERVAL, TASK_RUNNER_TIMEOUT
from starfish.data_factory.constants import (
    IDX,
    LOCAL_STORAGE_URI,
    RECORD_STATUS,
    RUN_MODE_DRY_RUN,
    RUN_MODE_NORMAL,
    RUN_MODE_RE_RUN,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory.job_manager import JobManager
from starfish.data_factory.job_manager_dry_run import JobManagerDryRun
from starfish.data_factory.job_manager_re_run import JobManagerRerun
from starfish.data_factory.storage.in_memory.in_memory_storage import InMemoryStorage
from starfish.data_factory.storage.local.local_storage import LocalStorage
from starfish.data_factory.storage.models import GenerationMasterJob, Project
from starfish.data_factory.utils.data_class import FactoryMasterConfig, TelemetryData
from starfish.data_factory.utils.state import MutableSharedState
from starfish.telemetry.posthog_client import Event, analytics

logger = get_logger(__name__)

# Create a type variable for the function type
F = TypeVar("F", bound=Callable[..., Any])

# Add this line after the other type-related imports
P = ParamSpec("P")

T = TypeVar("T")


class DataFactoryWrapper(Generic[T]):
    """Wrapper class that provides execution methods for data factory pipelines.

    This class acts as the interface returned by the @data_factory decorator,
    providing methods to run, dry-run, and resume data processing jobs.

    Attributes:
        factory (DataFactory): The underlying DataFactory instance
        state: Shared state object for tracking job state
    """

    filter_mapping = {("duplicated",): STATUS_DUPLICATE, ("completed",): STATUS_COMPLETED, ("failed",): STATUS_FAILED, ("filtered",): STATUS_FILTERED}
    valid_status = (STATUS_DUPLICATE, STATUS_COMPLETED, STATUS_FILTERED, STATUS_FAILED)

    def __init__(self, factory: Any, func: Callable[..., T]):
        """Initialize the DataFactoryWrapper instance.

        Args:
            factory (Any): The DataFactory instance to wrap
            func (Callable[..., T]): The data processing function to execute
        """
        self.factory = factory
        self.state = factory.state
        self.__func__ = func

    def run(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute the data processing pipeline with normal configuration.

        Args:
            *args: Positional arguments to pass to the data processing function
            **kwargs: Keyword arguments to pass to the data processing function

        Returns:
            T: Processed output data
        """
        self.factory.config.run_mode = RUN_MODE_NORMAL
        return event_loop_manager(self.factory, *args, **kwargs)

    def dry_run(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Test run with limited data for validation purposes.

        Args:
            *args: Positional arguments to pass to the data processing function
            **kwargs: Keyword arguments to pass to the data processing function

        Returns:
            T: Processed output data from the test run
        """
        self.factory.config.run_mode = RUN_MODE_DRY_RUN
        return event_loop_manager(self.factory, *args, **kwargs)

    def resume(self, **kwargs) -> T:
        """continue current data generation job.

        Args:
            master_job_id (str): ID of the master job to resume


        Returns:
            T: Processed output data from the resume
        """
        kwargs["factory"] = self.factory
        return resume_from_checkpoint(**kwargs)

    def get_output_data(self, filter: str) -> T:
        result = None
        _filter = self._convert_filter(filter=filter)
        if self._valid_filter(_filter):
            result = self.factory._process_output(_filter)
        else:
            raise InputError(f"Invalid filter '{filter}'. Supported filters are: {list(self.__class__.filter_mapping.keys())}")
        return result

    def get_output_completed(self) -> T:
        return self.factory._process_output()

    def get_output_duplicate(self) -> T:
        return self.factory._process_output(STATUS_DUPLICATE)

    def get_output_filtered(self) -> T:
        return self.factory._process_output(STATUS_FILTERED)

    def get_output_failed(self) -> T:
        return self.factory._process_output(STATUS_FAILED)

    def get_input_data(self) -> T:
        return self.factory.original_input_data

    def get_index(self, filter: str) -> T:
        result = None
        _filter = self._convert_filter(filter)
        if self._valid_filter(_filter):
            result = self.factory._process_output(_filter, is_idx=True)
        else:
            raise InputError(f"Invalid filter '{filter}'. Supported filters are: {list(self.__class__.filter_mapping.keys())}")
        return result

    def get_index_completed(self) -> T:
        return self.factory._process_output(is_idx=True)

    def get_index_duplicate(self) -> T:
        return self.factory._process_output(STATUS_DUPLICATE, is_idx=True)

    def get_index_filtered(self) -> T:
        return self.factory._process_output(STATUS_FILTERED, is_idx=True)

    def get_index_failed(self) -> T:
        return self.factory._process_output(STATUS_FAILED, is_idx=True)

    def _valid_filter(self, filter: str) -> bool:
        return filter in self.__class__.valid_status

    def _convert_filter(self, filter: str) -> str:
        for keys, status in self.__class__.filter_mapping.items():
            if filter in keys:
                filter = status
                break
        return filter


class DataFactoryProtocol(Protocol[P, T]):
    """Protocol for the decorated function with additional methods."""

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    def run(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    def dry_run(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    def resume(self, **kwargs) -> T: ...
    def get_output_data(self, filter: str) -> T: ...
    def get_output_completed(self) -> T: ...
    def get_output_duplicate(self) -> T: ...
    def get_output_filtered(self) -> T: ...
    def get_output_failed(self) -> T: ...
    def get_input_data(self) -> T: ...
    def get_index(self, filter: str) -> T: ...
    def get_index_completed(self) -> T: ...
    def get_index_duplicate(self) -> T: ...
    def get_index_filtered(self) -> T: ...
    def get_index_failed(self) -> T: ...


class DataFactory:
    """Core class for managing data generation pipelines.

    This class handles the orchestration of data generation tasks, including:
    - Input data processing
    - Job management and execution
    - Storage configuration
    - Progress tracking
    - Error handling

    Attributes:
        config (FactoryMasterConfig): Configuration for the data generation job
        func (Callable): The data processing function to be executed
        input_data_queue (Queue): Queue holding input data to be processed
        factory_storage: Storage backend instance
        config_ref: Reference to the stored configuration
        err: Error object if any occurred during processing
        state: Shared state object for tracking job state
        job_manager: Job manager instance handling the execution
    """

    def __init__(self, master_job_config: FactoryMasterConfig, func: Callable = None):
        """Initialize the DataFactory instance.

        Args:
            master_job_config (FactoryMasterConfig): Configuration object containing:
                - storage: Storage backend to use ('local' or 'in_memory')
                - batch_size: Number of records to process in each batch
                - max_concurrency: Maximum number of concurrent tasks
                - target_count: Target number of records to generate (0 means process all input)
                - show_progress: Whether to display progress bar
                - task_runner_timeout: Timeout in seconds for task execution
                - on_record_complete: List of callbacks to execute after successful record processing
                - on_record_error: List of callbacks to execute after failed record processing
                - state: Shared state object for tracking job state
            func (Callable, optional): The data processing function to be wrapped. Defaults to None.

        """
        self.config = master_job_config
        self.target_count = self.config.target_count
        self.state = None
        self.func = func
        self.input_data_queue = Queue()
        self.factory_storage = None
        self.err = None
        self.config_ref = None
        self.job_manager = None
        self.same_session = False
        self.original_input_data = []
        self.result_idx = []
        self._output_cache = {}

    def _clean_up_in_same_session(self):
        # same session, reset err and factory_storage
        if self.factory_storage or self.job_manager:
            self.same_session = True
        if self.same_session:
            self.err = None
            self.factory_storage = None
            # self.config_ref = None
            self.job_manager = None
            self.result_idx = []
            self._output_cache = {}
        # todo reuse the state from last same-factory state or a new state

    async def __call__(self, *args, **kwargs) -> List[Dict]:
        """Execute the data processing pipeline based on the configured run mode."""
        try:
            # Initialize job based on run mode
            await self._initialize_job(*args, **kwargs)
            # Setup and execute job
            await self._setup_job_execution()
            self._execute_job()

        except (InputError, OutputError, KeyboardInterrupt, Exception) as e:
            self.err = e
        finally:
            return await self._finalize_and_cleanup_job()

    async def _initialize_job(self, *args, **kwargs) -> None:
        """Initialize job configuration and manager based on run mode."""

        if self.config.run_mode == RUN_MODE_RE_RUN:
            self._setup_rerun_job()
        elif self.config.run_mode == RUN_MODE_DRY_RUN:
            await self._setup_dry_run_job(*args, **kwargs)
        else:
            await self._setup_normal_job(*args, **kwargs)

    def _setup_rerun_job(self) -> None:
        """Configure job for resume mode."""
        self.job_manager = JobManagerRerun(
            job_config=self.config, state=self.state, storage=self.factory_storage, user_func=self.func, input_data_queue=self.input_data_queue
        )

    async def _setup_dry_run_job(self, *args, **kwargs) -> None:
        """Configure job for dry-run mode."""
        self.input_data_queue, _ = _default_input_converter(*args, **kwargs)
        self._check_parameter_match()
        await self._storage_setup()
        self.job_manager = JobManagerDryRun(
            job_config=self.config, state=self.state, storage=self.factory_storage, user_func=self.func, input_data_queue=self.input_data_queue
        )

    async def _setup_normal_job(self, *args, **kwargs) -> None:
        """Configure job for normal execution mode."""
        self._clean_up_in_same_session()
        self.input_data_queue, self.original_input_data = _default_input_converter(*args, **kwargs)
        self._check_parameter_match()
        await self._storage_setup()
        self._update_job_config()
        self.config.project_id = str(uuid.uuid4())
        self.config.master_job_id = str(uuid.uuid4())
        self.job_manager = JobManager(
            master_job_config=self.config, state=self.state, storage=self.factory_storage, input_data_queue=self.input_data_queue, user_func=self.func
        )

    async def _setup_job_execution(self) -> None:
        """Prepare job for execution."""

        if self.config.run_mode == RUN_MODE_NORMAL:
            await self._save_project()
            await self._log_master_job_start()
        await self.job_manager.setup_input_output_queue()

    def _execute_job(self) -> None:
        """Execute the main job processing."""
        self._process_batches()

    async def _finalize_job(self) -> List[Dict]:
        """Complete job execution and return results."""
        result = None
        if self.job_manager:
            result = self._process_output()
            if len(result) == 0:
                self.err = OutputError("No records generated")
                # raise self.err

            await self._complete_master_job()
            self._show_job_progress_status()

        return result

    async def _finalize_and_cleanup_job(self) -> None:
        result = await self._finalize_job()
        """Handle job cleanup and error reporting."""
        self._send_telemetry_event()

        if self.err:
            if isinstance(self.err, (InputError, OutputError)):
                await self._close_storage()
                raise self.err
            else:
                # log the error
                err_msg = "KeyboardInterrupt" if isinstance(self.err, KeyboardInterrupt) else str(self.err)
                logger.error(f"Error occurred: {err_msg}")
                logger.info(
                    f"[RESUME INFO] 🚨 Job stopped unexpectedly. You can resume the job by calling resume_from_checkpoint(master_job_id='{self.config.master_job_id}')"
                )
        # save request config and close storage
        await self._save_request_config()
        await self._close_storage()
        return result

    def _send_telemetry_event(self):
        """Send telemetry data for the completed job.

        Collects and sends job metrics and error information to the analytics service.
        """
        telemetry_data = TelemetryData(
            job_id=self.config.master_job_id,
            target_reached=False,
            run_mode=self.config.run_mode,
            run_time_platform=get_platform_name(),
            num_inputs=self.input_data_queue.qsize(),
            library_version=__version__,  # Using the version here
            config={
                "batch_size": self.config.batch_size,
                "target_count": self.config.target_count,
                "max_concurrency": self.config.max_concurrency,
                "task_runner_timeout": self.config.task_runner_timeout,
                "job_run_stop_threshold": self.config.job_run_stop_threshold,
            },
            error_summary={
                "err": str(self.err),
            },
        )
        if self.job_manager:
            telemetry_data.count_summary = {
                "completed": self.job_manager.completed_count,
                "failed": self.job_manager.failed_count,
                "filtered": self.job_manager.filtered_count,
                "duplicate": self.job_manager.duplicate_count,
            }
            telemetry_data.execution_time = self.job_manager.execution_time
            telemetry_data.error_summary = {
                "total_errors": self.job_manager.failed_count,
                "error_types": self.job_manager.err_type_counter,
            }
            telemetry_data.num_inputs = (len(self.original_input_data),)
            telemetry_data.target_reached = ((self.job_manager.completed_count >= self.job_manager.job_config.target_count),)
        analytics.send_event(event=Event(data=telemetry_data.to_dict(), name="starfish_job"))

    def _process_output(self, status_filter: str = STATUS_COMPLETED, is_idx: bool = False) -> List[Any]:
        """Process and filter the job output queue to return only records matching the status filter.

        Args:
            status_filter: Status to filter records by (default: STATUS_COMPLETED)
            is_idx: If True, return indices instead of output data

        Returns:
            List[Any]: List of processed outputs or indices from matching records
        """

        # Check if cache is already populated for this status
        if status_filter in self._output_cache:
            return self._output_cache[status_filter].get(IDX, []) if is_idx else self._output_cache[status_filter].get("result", [])
        else:
            # init the output_cache
            self._output_cache = {
                STATUS_COMPLETED: {"result": [], IDX: []},
                STATUS_DUPLICATE: {"result": [], IDX: []},
                STATUS_FAILED: {"result": [], IDX: []},
                STATUS_FILTERED: {"result": [], IDX: []},
            }
        # Process records and populate cache
        for record in self.job_manager.job_output.queue:
            record_idx = record.get(IDX)
            status = record.get(RECORD_STATUS)
            record_output = record.get("output", []) if status != STATUS_FAILED else record.get("err", [])

            # Update cache
            self._output_cache[status][IDX].extend([record_idx] * len(record_output))
            self._output_cache[status]["result"].extend(record_output)

        return self._output_cache[status_filter].get(IDX, []) if is_idx else self._output_cache[status_filter].get("result", [])

    def _check_parameter_match(self):
        """Validate that input data parameters match the wrapped function's signature.

        Raises:
            TypeError: If there's a mismatch between input data parameters and function parameters
        """
        func_sig = signature(self.func)

        # Validate batch items against function parameters
        batch_item = self.original_input_data[0]
        for param_name, param in func_sig.parameters.items():
            # Skip if parameter has a default value
            if param.default is not Parameter.empty:
                continue
            # Check if required parameter is missing in batch
            if param_name not in batch_item:
                raise InputError(f"Batch item is missing required parameter '{param_name}' " f"for function {self.func.__name__}")
        # Check 2: Ensure all batch parameters exist in function signature
        for batch_param in batch_item.keys():
            if batch_param not in func_sig.parameters:
                raise InputError(f"Batch items contains unexpected parameter '{batch_param}' " f"not found in function {self.func.__name__}")

    def _process_batches(self) -> List[Any]:
        """Initiate batch processing through the job manager.

        Returns:
            List[Any]: Processed output from the job manager

        Note:
            Logs job start information and progress interval
        """
        if self.config.run_mode != RUN_MODE_RE_RUN:
            logger.info(
                f"\033[1m[JOB START]\033[0m "
                f"\033[36mMaster Job ID: {self.config.master_job_id}\033[0m | "
                f"\033[33mLogging progress every {PROGRESS_LOG_INTERVAL} seconds\033[0m"
            )

        # if self.config.run_mode == RUN_MODE_NORMAL:

        return self.job_manager.run_orchestration()

    async def _save_project(self):
        """Save project metadata to storage.

        Creates a new project entry with test data for storage layer testing.
        """
        project = Project(project_id=self.config.project_id, name="Test Project", description="A test project for storage layer testing")
        await self.factory_storage.save_project(project)

    async def _save_request_config(self):
        """Save the job configuration and input data to storage.

        Serializes and stores the function, configuration, state, and input data
        for potential re-runs.
        """
        if self.config.run_mode != RUN_MODE_DRY_RUN:
            logger.debug("\n2. Creating master job...")
            # First save the request config
            config_data = {
                "generator": "test_generator",
                "state": self.state.to_dict(),
                "input_data": self.original_input_data,
            }
            func_hex = None
            config_serialize = None

            try:
                func_hex = cloudpickle.dumps(self.func).hex()
            except TypeError as e:
                logger.warning(f"Cannot serialize function for resume due to unsupported type: {str(e)}")
            except Exception as e:
                logger.warning(f"Unexpected error serializing function: {str(e)}")

            try:
                config_serialize = self.config.to_dict()
            except TypeError as e:
                logger.warning(f"Cannot serialize config for resume due to unsupported type: {str(e)}")
            except Exception as e:
                logger.warning(f"Unexpected error serializing config: {str(e)}")

            config_data["func"] = func_hex
            config_data["config"] = config_serialize
            await self.factory_storage.save_request_config(self.config_ref, config_data)
            logger.debug(f"  - Saved request config to: {self.config_ref}")

    async def _log_master_job_start(self):
        """Log the start of a master job to storage.

        Creates and stores a master job record with initial metadata.
        """
        self.config_ref = self.factory_storage.generate_request_config_path(self.config.master_job_id)
        # Now create the master job
        master_job = GenerationMasterJob(
            master_job_id=self.config.master_job_id,
            project_id=self.config.project_id,
            name="Test Master Job",
            status="running",
            request_config_ref=self.config_ref,
            output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            storage_uri=LOCAL_STORAGE_URI,
            target_record_count=10,
        )
        await self.factory_storage.log_master_job_start(master_job)
        logger.debug(f"  - Created master job: {master_job.name} ({self.config.master_job_id})")

    async def _complete_master_job(self):
        """Finalize and log the completion of a master job.

        Updates the job status and records summary statistics to storage.

        Raises:
            Exception: If there's an error during job completion
        """
        #  Complete the master job
        if self.config.run_mode != RUN_MODE_DRY_RUN:
            try:
                logger.debug("\n7. Stopping master job...")
                now = datetime.datetime.now(datetime.timezone.utc)
                status = STATUS_FAILED if self.err else STATUS_COMPLETED

                summary = {
                    STATUS_COMPLETED: self.job_manager.completed_count,
                    STATUS_FILTERED: self.job_manager.filtered_count,
                    STATUS_DUPLICATE: self.job_manager.duplicate_count,
                    STATUS_FAILED: self.job_manager.failed_count,
                }
                if self.factory_storage:
                    await self.factory_storage.log_master_job_end(self.config.master_job_id, status, summary, now, now)
            except Exception as e:
                raise e

    async def _close_storage(self):
        """Clean up and close the storage connection.

        Ensures proper closure of storage resources when the job completes.
        """
        if self.factory_storage:
            await self.factory_storage.close()

    async def _storage_setup(self):
        """Initialize the storage backend based on configuration.

        Sets up either local or in-memory storage based on the config.
        """
        if not self.factory_storage:
            if self.config.storage == STORAGE_TYPE_LOCAL:
                self.factory_storage = LocalStorage(LOCAL_STORAGE_URI)
            else:
                self.factory_storage = InMemoryStorage()
            await self.factory_storage.setup()

    def _update_job_config(self):
        """Update job configuration based on input data.

        Adjusts the target count based on the input queue size if target_count is 0.
        """
        target_count = self.target_count
        new_target_count = self.input_data_queue.qsize() if target_count == 0 else target_count
        self.config.target_count = new_target_count

    def _show_job_progress_status(self):
        """Display final job statistics and completion status.

        Logs the final counts of completed, failed, filtered, and duplicate records.
        """
        target_count = self.config.target_count
        logger.info(
            f"[JOB FINISHED] "
            f"\033[1mFinal Status:\033[0m "
            f"\033[32mCompleted: {self.job_manager.completed_count}/{target_count}\033[0m | "
            f"\033[33mAttempted: {self.job_manager.total_count}\033[0m "
            f"(Failed: {self.job_manager.failed_count}, "
            f"Filtered: {self.job_manager.filtered_count}, "
            f"Duplicate: {self.job_manager.duplicate_count})"
        )


def _default_input_converter(data: List[Dict[str, Any]] = None, **kwargs) -> tuple[Queue[Dict[str, Any]], list[Dict[str, Any]]]:
    """Convert input data into a queue of records for processing.

    Args:
        data (List[Dict[str, Any]], optional): List of input data records. Defaults to None.
        **kwargs: Additional parameters that can be either parallel sources or broadcast values

    Returns:
        Queue[Dict[str, Any]]: Queue of records ready for processing

    Raises:
        ValueError: If parallel sources have different lengths

    Note:
        - Parallel sources are lists/tuples that will be zipped together
        - Broadcast values are single values that will be added to all records
    """
    # Determine parallel sources
    if data is None:
        data = []
    parallel_sources = {}
    if isinstance(data, list) and len(data) > 0:
        parallel_sources["data"] = data
    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)):
            parallel_sources[key] = value

    # Validate parallel sources have same length
    lengths = [len(v) for v in parallel_sources.values()]
    if len(set(lengths)) > 1:
        raise InputError("All parallel sources must have the same length")

    # Determine batch size (L)
    batch_size = lengths[0] if lengths else 1

    # Prepare results
    results = Queue()
    original_input_data = []
    for i in range(batch_size):
        record = {IDX: i}

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

        original_input_data.append({k: v for k, v in record.items() if k != IDX})

    # Convert the list to an immutable tuple
    return results, original_input_data


def data_factory(
    storage: str = STORAGE_TYPE_LOCAL,
    batch_size: int = 1,
    target_count: int = 0,
    max_concurrency: int = 10,
    initial_state_values: Optional[Dict[str, Any]] = None,
    on_record_complete: Optional[List[Callable]] = None,
    on_record_error: Optional[List[Callable]] = None,
    show_progress: bool = True,
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT,
    job_run_stop_threshold: int = NOT_COMPLETED_THRESHOLD,
) -> Callable[[Callable[P, T]], DataFactoryProtocol[P, T]]:
    """Decorator for creating data processing pipelines.

    Args:
        storage (str): Storage backend to use ('local' or 'in_memory')
        batch_size (int): Number of records to process in each batch
        target_count (int): Target number of records to generate (0 means process all input)
        max_concurrency (int): Maximum number of concurrent tasks
        initial_state_values (Optional[Dict[str, Any]]): Initial values for shared state
        on_record_complete (Optional[List[Callable]]): Callbacks to execute after successful record processing
        on_record_error (Optional[List[Callable]]): Callbacks to execute after failed record processing
        show_progress (bool): Whether to display progress bar
        task_runner_timeout (int): Timeout in seconds for task execution
        job_run_stop_threshold (int): Threshold for stopping job if too many records fail

    Returns:
        Callable[[Callable[P, T]], DataFactoryProtocol[P, T]]: Decorated function with additional execution methods
    """
    if on_record_error is None:
        on_record_error = []
    if on_record_complete is None:
        on_record_complete = []
    if initial_state_values is None:
        initial_state_values = {}
    master_job_config = FactoryMasterConfig(
        storage=storage,
        batch_size=batch_size,
        target_count=target_count,
        max_concurrency=max_concurrency,
        show_progress=show_progress,
        task_runner_timeout=task_runner_timeout,
        on_record_complete=on_record_complete,
        on_record_error=on_record_error,
        job_run_stop_threshold=job_run_stop_threshold,
    )
    _factory = None

    def decorator(func: Callable[P, T]) -> DataFactoryProtocol[P, T]:
        nonlocal _factory  # Use nonlocal instead of global for better scoping
        if _factory is None:  # Only create new factory if one doesn't exist
            factory = DataFactory(master_job_config, func)
            factory.state = MutableSharedState(initial_data=initial_state_values)
            _factory = factory
        else:
            # Update existing factory with new config
            _factory.config = master_job_config
            _factory.func = func
            _factory.state = MutableSharedState(initial_data=initial_state_values)

        wrapper = DataFactoryWrapper(_factory, func)
        return cast(DataFactoryProtocol[P, T], wrapper)

    def _resume_from_checkpoint(master_job_id: str, **kwargs) -> List[Dict]:
        """Re-run a previously executed data generation job.

        Args:
            master_job_id (str): ID of the master job to resume
            **kwargs: Additional configuration overrides for the resume

        Returns:
            List[Dict]: Processed output data from the resume
        """
        nonlocal _factory
        if _factory is None:
            raise RuntimeError("Factory not initialized. Please decorate a function first.")
        # kwargs["factory"] = _factory
        return resume_from_checkpoint(master_job_id, **kwargs)

    data_factory.resume_from_checkpoint = _resume_from_checkpoint

    return decorator


async def _re_run_get_master_job_request_config(factory: DataFactory):
    master_job = await factory.factory_storage.get_master_job(factory.config.master_job_id)
    if master_job:
        master_job_config_data = await factory.factory_storage.get_request_config(master_job.request_config_ref)
        # Convert list to dict with count tracking using hash values
        return master_job_config_data, master_job
    else:
        await factory._close_storage()
        raise InputError(f"Master job not found for master_job_id: {factory.config.master_job_id}")


async def async_re_run(*args, **kwargs) -> List[Any]:
    """Asynchronously resume a previously executed data generation job.

    Args:
        master_job_id (str): ID of the master job to resume
        **kwargs: Additional configuration overrides for the resume

    Returns:
        List[Any]: Processed output data from the resume

    Raises:
        TypeError: If master job ID is not provided or job not found
    """
    # call with instance
    if "factory" in kwargs:
        factory = kwargs["factory"]
        factory._clean_up_in_same_session()
    else:
        factory = DataFactory(FactoryMasterConfig(storage=STORAGE_TYPE_LOCAL))
        if len(args) == 1:
            factory.config.master_job_id = args[0]
        else:
            raise InputError("Master job id is required, please pass it in the paramters")
    # Update config with any additional kwargs
    for key, value in kwargs.items():
        if hasattr(factory.config, key):
            setattr(factory.config, key, value)
    if not factory.config.master_job_id:
        raise InputError("Master job id is required")

    await factory._storage_setup()
    master_job_config_data, master_job = await _re_run_get_master_job_request_config(factory=factory)
    if not factory.same_session:
        factory.state = MutableSharedState(initial_data=master_job_config_data.get("state"))
        factory.config = FactoryMasterConfig.from_dict(master_job_config_data.get("config"))
        func_serilized = master_job_config_data.get("func")
        if func_serilized:
            factory.func = cloudpickle.loads(bytes.fromhex(master_job_config_data.get("func")))
    if not factory.func or not factory.config:
        await factory._close_storage()
        raise NoResumeSupportError("do not support resume_from_checkpoint, please update the function to support cloudpickle serilization")
    factory.config.run_mode = RUN_MODE_RE_RUN
    factory.config.prev_job = {"master_job": master_job, "input_data": master_job_config_data.get("input_data")}
    # missing the idx but the input_data order keep the same; so add idx back in the job_maanger
    factory.original_input_data = [dict(item) for item in factory.config.prev_job["input_data"]]
    factory.config_ref = factory.factory_storage.generate_request_config_path(factory.config.master_job_id)
    # Call the __call__ method
    result = await factory()
    return result


def resume_from_checkpoint(*args, **kwargs) -> List[Dict]:
    """Re-run a previously executed data generation job.

    This is the synchronous interface for re-running jobs.

    Args:
        master_job_id (str): ID of the master job to resume
        storage (str): Storage backend to use ('local' or 'in_memory')
        batch_size (int): Number of records to process in each batch
        target_count (int): Target number of records to generate (0 means process all input)
        max_concurrency (int): Maximum number of concurrent tasks
        initial_state_values (Optional[Dict[str, Any]]): Initial values for shared state
        on_record_complete (Optional[List[Callable]]): Callbacks to execute after successful record processing
        on_record_error (Optional[List[Callable]]): Callbacks to execute after failed record processing
        show_progress (bool): Whether to display progress bar
        task_runner_timeout (int): Timeout in seconds for task execution
        job_run_stop_threshold (int): Threshold for stopping job if too many records fail

    Returns:
        List[Any]: Processed output data from the resume

    Raises:
        TypeError: If master job ID is not provided or job not found
    """
    return event_loop_manager(async_re_run, *args, **kwargs)


def event_loop_manager(callable_func: Callable, *args, **kwargs) -> List[Dict]:
    """Manage the event loop for executing an async callable in synchronous contexts.

    Args:
        callable_func (Callable): The async function to execute
        *args: Positional arguments to pass to the callable
        **kwargs: Keyword arguments to pass to the callable

    Returns:
        Any: The result of the callable function

    Note:
        Handles event loop creation and cleanup, ensuring proper resource management
        when calling async functions from synchronous code.
    """
    # Clean up existing event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.close()  # Close if running
        elif not loop.is_closed():
            loop.close()  # Close if not running and not closed
    except RuntimeError:  # Handle case where loop is closed or doesn't exist
        pass  # No loop to close, proceed to create a new one

    # Create new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Execute the callable
    try:
        result = loop.run_until_complete(callable_func(*args, **kwargs))
        return result
    finally:
        # Clean up after execution
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.close()  # Close if running
            elif not loop.is_closed():
                loop.close()  # Close if not running and not closed
        except RuntimeError:
            pass
