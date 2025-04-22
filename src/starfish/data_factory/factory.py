import asyncio
import datetime
import inspect
import uuid
from inspect import Parameter, signature
from queue import Queue
from typing import Any, Callable, Dict, Generic, List, Optional, ParamSpec, TypeVar, cast, Protocol

import cloudpickle

from starfish.common.logger import get_logger
from starfish.data_factory.config import NOT_COMPLETED_THRESHOLD, PROGRESS_LOG_INTERVAL, TASK_RUNNER_TIMEOUT
from starfish.data_factory.constants import (
    LOCAL_STORAGE_URI,
    RECORD_STATUS,
    RUN_MODE_DRY_RUN,
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
    def __init__(self, factory: Any, func: Callable[..., T]):
        self.factory = factory
        self.func = func
        self.state = factory.state

    def run(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute the data processing pipeline."""
        return event_loop_manager(self.factory, *args, **kwargs)

    def dry_run(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Test run with limited data."""
        self.factory.config.run_mode = RUN_MODE_DRY_RUN
        return event_loop_manager(self.factory, *args, **kwargs)

    def re_run(self, master_job_id: str, **kwargs) -> T:
        """Re-run a previously executed data generation job."""
        kwargs["factory"] = self.factory
        return re_run(master_job_id, **kwargs)


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
        telemetry_enabled (bool): Flag to control telemetry event sending
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

        Initializes:
            - Input data queue
            - Storage backend
            - Error tracking
            - Configuration reference
            - Telemetry settings
        """
        self.config = master_job_config
        self.state = None
        self.func = func
        self.input_data_queue = Queue()
        self.factory_storage = None
        self.err = None
        self.config_ref = None
        self.telemetry_enabled = True
        self.job_manager = None

    async def __call__(self, *args, **kwargs):
        """Execute the data processing pipeline based on the configured run mode.

        This method handles the main execution flow for different run modes:
        - Normal mode: Processes all input data
        - Re-run mode: Re-runs a previous job using stored configuration
        - Dry-run mode: Processes only the first input item for testing

        Args:
            *args: Positional arguments passed to the data processing function
            **kwargs: Keyword arguments passed to the data processing function
                - master_job_id: Required for re-run mode to specify which job to re-run

        Returns:
            List[Any]: Processed output data

        Raises:
            TypeError: If there's a parameter mismatch between input data and function signature
            ValueError: If no records are generated or if input data validation fails
            KeyboardInterrupt: If the job is interrupted by the user
        """
        run_mode = self.config.run_mode
        try:
            # Check for master_job_id in kwargs and assign if present
            if run_mode == RUN_MODE_RE_RUN:
                self.job_manager = JobManagerRerun(
                    job_config=self.config, state=self.state, storage=self.factory_storage, user_func=self.func, input_data_queue=self.input_data_queue
                )
            elif run_mode == RUN_MODE_DRY_RUN:
                # dry run mode
                self.input_data_queue = _default_input_converter(*args, **kwargs)
                # Get only first item but maintain Queue structure
                self._check_parameter_match()
                await self._storage_setup()
                self.job_manager = JobManagerDryRun(
                    job_config=self.config, state=self.state, storage=self.factory_storage, user_func=self.func, input_data_queue=self.input_data_queue
                )
            else:
                self.input_data_queue = _default_input_converter(*args, **kwargs)
                self._check_parameter_match()
                await self._storage_setup()
                self._update_job_config()
                self.config.project_id = str(uuid.uuid4())
                self.config.master_job_id = str(uuid.uuid4())
                self.job_manager = JobManager(
                    master_job_config=self.config, state=self.state, storage=self.factory_storage, input_data_queue=self.input_data_queue, user_func=self.func
                )
                await self._save_project()
                await self._save_request_config()
                await self._log_master_job_start()
            await self.job_manager.setup_input_output_queue()
            self._process_batches()

        except (TypeError, ValueError, KeyboardInterrupt) as e:
            self.err = e
        finally:
            self._send_telemetry_event()
            if not isinstance(self.err, TypeError):
                result = self._process_output()
                if len(result) == 0:
                    self.err = ValueError("No records generated")

                await self._complete_master_job()
                await self._close_storage()
                # Only execute finally block if not TypeError
                if self.err and not isinstance(self.err, ValueError):
                    err_msg = str(self.err)
                    if isinstance(self.err, KeyboardInterrupt):
                        err_msg = "KeyboardInterrupt"

                    logger.error(f"Error occurred: {err_msg}")
                    logger.info(
                        f"[RE-RUN INFO] 🚨 Job stopped unexpectedly. You can resume the job using " f'master_job_id by re_run("{self.config.master_job_id}")'
                    )
                self._show_job_progress_status()
                if isinstance(self.err, ValueError):
                    raise self.err
                else:
                    return result
            else:
                await self._close_storage()
                raise self.err

    def _send_telemetry_event(self):
        """Send telemetry data for the completed job.

        Collects and sends job metrics and error information if telemetry is enabled.
        """
        logger.info("Sending telemetry event")
        if self.telemetry_enabled:
            telemetry_data = TelemetryData(
                job_id=self.config.master_job_id,
                target_reached=False,
                run_mode=self.config.run_mode,
                num_inputs=self.input_data_queue.qsize(),
                library_version="starfish-core",  # This should be replaced with actual version
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
                telemetry_data.num_inputs = (self.job_manager.nums_input,)
                telemetry_data.target_reached = ((self.job_manager.completed_count >= self.job_manager.job_config.target_count),)
            analytics.send_event(event=Event(data=telemetry_data.to_dict(), name="starfish_job"))

    def _process_output(self) -> List[Any]:
        """Process and filter the job output queue to return only completed records.

        Returns:
            List[Any]: List of successfully processed outputs from completed records
        """
        result = []
        output = self.job_manager.job_output.queue
        for v in output:
            if v.get(RECORD_STATUS) == STATUS_COMPLETED:
                result.extend(v.get("output"))
        return result

    def _check_parameter_match(self):
        """Validate that input data parameters match the wrapped function's signature.

        Raises:
            TypeError: If there's a mismatch between input data parameters and function parameters
        """
        func_sig = signature(self.func)

        # Validate batch items against function parameters
        batch_item = self.input_data_queue.queue[0]
        for param_name, param in func_sig.parameters.items():
            # Skip if parameter has a default value
            if param.default is not Parameter.empty:
                continue
            # Check if required parameter is missing in batch
            if param_name not in batch_item:
                raise TypeError(f"Batch item is missing required parameter '{param_name}' " f"for function {self.func.__name__}")
        # Check 2: Ensure all batch parameters exist in function signature
        for batch_param in batch_item.keys():
            if batch_param not in func_sig.parameters:
                raise TypeError(f"Batch items contains unexpected parameter '{batch_param}' " f"not found in function {self.func.__name__}")

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
        logger.debug("\n2. Creating master job...")
        # First save the request config
        config_data = {
            "generator": "test_generator",
            "config": self.config.to_dict(),
            "state": self.state.to_dict(),
            "func": cloudpickle.dumps(self.func).hex(),
            "input_data": list(self.input_data_queue.queue),
        }
        self.config_ref = await self.factory_storage.save_request_config(self.config.master_job_id, config_data)
        logger.debug(f"  - Saved request config to: {self.config_ref}")

    async def _log_master_job_start(self):
        """Log the start of a master job to storage.

        Creates and stores a master job record with initial metadata.
        """
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
        target_count = self.config.target_count
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


def _default_input_converter(data: List[Dict[str, Any]] = None, **kwargs) -> Queue[Dict[str, Any]]:
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


class DataFactoryProtocol(Protocol[P, T]):
    """Protocol for the decorated function with additional methods."""

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    def run(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    def dry_run(self, *args: P.args, **kwargs: P.kwargs) -> T: ...
    def re_run(self, master_job_id: str, **kwargs) -> T: ...


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
    """Decorator for creating data processing pipelines."""
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

    def decorator(func: Callable[P, T]) -> DataFactoryProtocol[P, T]:
        factory = DataFactory(master_job_config, func)
        factory.state = MutableSharedState(initial_data=initial_state_values)

        wrapper = DataFactoryWrapper(factory, func)

        # Attach methods to the original function
        func.run = wrapper.run  # type: ignore
        func.dry_run = wrapper.dry_run  # type: ignore
        func.re_run = wrapper.re_run  # type: ignore

        return cast(DataFactoryProtocol[P, T], func)  # Return the function with added methods

    return decorator


async def _re_run_get_master_job_request_config(factory: DataFactory):
    master_job = await factory.factory_storage.get_master_job(factory.config.master_job_id)
    if master_job:
        master_job_config_data = await factory.factory_storage.get_request_config(master_job.request_config_ref)
        # Convert list to dict with count tracking using hash values
        return master_job_config_data, master_job
    else:
        await factory._close_storage()
        raise TypeError(f"Master job not found for master_job_id: {factory.config.master_job_id}")


async def async_re_run(*args, **kwargs) -> List[Any]:
    """Asynchronously re-run a previously executed data generation job.

    Args:
        master_job_id (str): ID of the master job to re-run
        **kwargs: Additional configuration overrides for the re-run

    Returns:
        List[Any]: Processed output data from the re-run

    Raises:
        TypeError: If master job ID is not provided or job not found
    """
    # call with instance
    if "factory" in kwargs:
        factory = kwargs["factory"]
    else:
        factory = DataFactory(FactoryMasterConfig(storage=STORAGE_TYPE_LOCAL))
    if len(args) == 1:
        factory.config.master_job_id = args[0]
    # Update config with any additional kwargs
    for key, value in kwargs.items():
        if hasattr(factory.config, key):
            setattr(factory.config, key, value)
    if not factory.config.master_job_id:
        raise TypeError("Master job id is required")

    await factory._storage_setup()
    master_job_config_data, master_job = await _re_run_get_master_job_request_config(factory=factory)
    factory.state = MutableSharedState(initial_data=master_job_config_data.get("state"))
    factory.config = FactoryMasterConfig.from_dict(master_job_config_data.get("config"))
    factory.config.run_mode = RUN_MODE_RE_RUN
    factory.config.prev_job = {"master_job": master_job, "input_data": master_job_config_data.get("input_data")}
    factory.func = cloudpickle.loads(bytes.fromhex(master_job_config_data.get("func")))
    factory.input_data = Queue()
    factory.err = None
    factory.config_ref = None
    # move to env
    factory.telemetry_enabled = True

    # Get the loaded function's signature
    if hasattr(factory.func, "__signature__"):
        original_sig = factory.func.__signature__
    else:
        original_sig = inspect.signature(factory.func)

    async_re_run.__signature__ = original_sig
    async_re_run.__annotations__ = factory.func.__annotations__

    # Call the __call__ method
    result = await factory()
    return result


def re_run(*args, **kwargs) -> List[Any]:
    """Re-run a previously executed data generation job.

    Args:
        master_job_id (str): ID of the master job to re-run
        **kwargs: Additional configuration overrides for the re-run

    Returns:
        List[Any]: Processed output data from the re-run

    Raises:
        TypeError: If master job ID is not provided or job not found
    """
    return event_loop_manager(async_re_run, *args, **kwargs)


# # Copy signature and annotations to re_run
re_run.__signature__ = inspect.signature(async_re_run)
re_run.__annotations__ = async_re_run.__annotations__


def event_loop_manager(callable_func: Callable, *args, **kwargs):
    """Manage the event loop for executing an async callable.

    Args:
        callable_func (Callable): The async function to execute
        *args: Positional arguments to pass to the callable
        **kwargs: Keyword arguments to pass to the callable

    Returns:
        Any: The result of the callable function

    Note:
        Handles event loop creation and cleanup for synchronous contexts
    """
    # Clean up existing event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.close()
    except RuntimeError:
        pass

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
                loop.close()
        except RuntimeError:
            pass
