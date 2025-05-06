import asyncio
from copy import deepcopy
import datetime
from os import environ
import sys
import uuid
import inspect
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
from copy import deepcopy

logger = get_logger(__name__)

# Create a type variable for the function type
F = TypeVar("F", bound=Callable[..., Any])

# Add this line after the other type-related imports
P = ParamSpec("P")

T = TypeVar("T")

# Flag to track if nest_asyncio has been applied
_NEST_ASYNCIO_APPLIED = False


def _ensure_nest_asyncio():
    """Ensure nest_asyncio is applied if needed.

    Returns:
        bool: True if nest_asyncio is applied or not needed
    """
    global _NEST_ASYNCIO_APPLIED

    if _NEST_ASYNCIO_APPLIED:
        return True

    # Check if we're in an environment that typically needs nest_asyncio
    running_in_notebook = "ipykernel" in sys.modules
    running_in_colab = "google.colab" in sys.modules

    if running_in_notebook or running_in_colab or _is_event_loop_running():
        import nest_asyncio

        nest_asyncio.apply()
        _NEST_ASYNCIO_APPLIED = True
        logger.debug("nest_asyncio has been applied to support nested event loops")

    return True


def _is_event_loop_running():
    """Check if an event loop is currently running.

    Returns:
        bool: True if an event loop is running, False otherwise
    """
    try:
        loop = asyncio.get_event_loop()
        return loop.is_running()
    except RuntimeError:
        return False


class FactoryWrapper(Generic[T]):
    """Wrapper class that provides execution methods for data factory pipelines.

    This class acts as the interface returned by the @data_factory decorator,
    providing methods to run, dry-run, and resume data processing jobs.

    Attributes:
        factory (Factory): The underlying Factory instance
        state: Shared state object for tracking job state
    """

    def __init__(self, factory: Any, func: Callable[..., T]):
        """Initialize the FactoryWrapper instance.

        Args:
            factory (Any): The Factory instance to wrap
            func (Callable[..., T]): The data processing function to execute
        """
        self.factory = factory
        self.state = factory.state
        self.__func__ = func

    def run(self, *args: P.args, **kwargs: P.kwargs) -> List[dict[str, Any]]:
        """Execute the data processing pipeline with normal configuration.

        Args:
            *args: Positional arguments to pass to the data processing function
            **kwargs: Keyword arguments to pass to the data processing function

        Returns:
            T: Processed output data
        """
        self.factory.config.run_mode = RUN_MODE_NORMAL
        return FactoryExecutorManager.execute(self.factory, *args, **kwargs)

    def dry_run(self, *args: P.args, **kwargs: P.kwargs) -> List[dict[str, Any]]:
        """Test run with limited data for validation purposes.

        Args:
            *args: Positional arguments to pass to the data processing function
            **kwargs: Keyword arguments to pass to the data processing function

        Returns:
            T: Processed output data from the test run
        """
        self.factory.config.run_mode = RUN_MODE_DRY_RUN
        return FactoryExecutorManager.execute(self.factory, *args, **kwargs)

    def resume(
        self,
        storage: str = None,
        batch_size: int = None,
        target_count: int = None,
        max_concurrency: int = None,
        initial_state_values: Optional[Dict[str, Any]] = None,
        on_record_complete: Optional[List[Callable]] = None,
        on_record_error: Optional[List[Callable]] = None,
        show_progress: bool = None,
        task_runner_timeout: int = None,
        job_run_stop_threshold: int = None,
    ) -> List[Dict[str, Any]]:
        """continue current data generation job."""
        # Get all passed arguments
        passed_args = {
            "storage": storage,
            "batch_size": batch_size,
            "target_count": target_count,
            "max_concurrency": max_concurrency,
            "initial_state_values": initial_state_values,
            "on_record_complete": on_record_complete,
            "on_record_error": on_record_error,
            "show_progress": show_progress,
            "task_runner_timeout": task_runner_timeout,
            "job_run_stop_threshold": job_run_stop_threshold,
            "factory": self.factory,
        }

        # Filter and pass only explicitly provided arguments
        return FactoryExecutorManager.resume(**passed_args)

    def get_output_data(self, filter: str) -> List[dict[str, Any]]:
        return FactoryExecutorManager.process_output(self.factory, filter=filter)

    def get_output_completed(self) -> List[dict[str, Any]]:
        return FactoryExecutorManager.process_output(self.factory)

    def get_output_duplicate(self) -> List[dict[str, Any]]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_DUPLICATE)

    def get_output_filtered(self) -> List[dict[str, Any]]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_FILTERED)

    def get_output_failed(self) -> List[dict[str, Any]]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_FAILED)

    def get_input_data_in_dead_queue(self) -> List[dict[str, Any]]:
        return FactoryExecutorManager.process_dead_queue(self.factory)

    def get_input_data(self) -> List[dict[str, Any]]:
        return self.factory.original_input_data

    def get_index(self, filter: str) -> List[int]:
        return FactoryExecutorManager.process_output(self.factory, filter=filter, is_idx=True)

    def get_index_completed(self) -> List[int]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_COMPLETED, is_idx=True)

    def get_index_duplicate(self) -> List[int]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_DUPLICATE, is_idx=True)

    def get_index_filtered(self) -> List[int]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_FILTERED, is_idx=True)

    def get_index_failed(self) -> List[int]:
        return FactoryExecutorManager.process_output(self.factory, filter=STATUS_FAILED, is_idx=True)

    def get_index_dead_queue(self) -> List[int]:
        return FactoryExecutorManager.process_dead_queue(self.factory, is_idx=True)


class DataFactoryProtocol(Protocol[P, T]):
    """Protocol for the decorated function with additional methods."""

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> List[Dict[str, Any]]: ...
    def run(self, *args: P.args, **kwargs: P.kwargs) -> List[Dict[str, Any]]: ...
    def dry_run(self, *args: P.args, **kwargs: P.kwargs) -> List[Dict[str, Any]]: ...
    def resume(
        self,
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
    ) -> List[Dict[str, Any]]: ...
    def get_output_data(self, filter: str) -> List[Dict[str, Any]]: ...
    def get_output_completed(self) -> List[Dict[str, Any]]: ...
    def get_output_duplicate(self) -> List[Dict[str, Any]]: ...
    def get_output_filtered(self) -> List[Dict[str, Any]]: ...
    def get_output_failed(self) -> List[Dict[str, Any]]: ...
    def get_input_data_in_dead_queue(self) -> List[Dict[str, Any]]: ...
    def get_input_data(self) -> List[Dict[str, Any]]: ...
    def get_index(self, filter: str) -> List[int]: ...
    def get_index_completed(self) -> List[int]: ...
    def get_index_duplicate(self) -> List[int]: ...
    def get_index_filtered(self) -> List[int]: ...
    def get_index_failed(self) -> List[int]: ...
    def get_index_dead_queue(self) -> List[int]: ...

    # def _get_dead_queue_indices_and_data(self) -> tuple[List[Dict[str, Any]], List[int]]: ...


class Factory:
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
        """Initialize the Factory instance.

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
            self.input_data_queue = Queue()

    async def __call__(self, *args, **kwargs) -> List[dict[str, Any]]:
        """Execute the data processing pipeline based on the configured run mode."""
        try:
            # Initialize job based on run mode
            await self._initialize_job(*args, **kwargs)
            await self._setup_job_execution()
            self._execute_job()
        except (InputError, OutputError, KeyboardInterrupt, Exception) as e:
            self.err = e
        finally:
            return await self._finalize_and_cleanup_job()

    async def _initialize_job(self, *args, **kwargs) -> None:
        """Initialize job configuration and manager based on run mode."""

        # Define job manager mapping
        job_manager_mapping = {
            RUN_MODE_RE_RUN: {
                "manager": JobManagerRerun,
                "setup": lambda: (),  # No additional setup needed for re-run
            },
            RUN_MODE_DRY_RUN: {
                "manager": JobManagerDryRun,
                "setup": lambda: (
                    self._clean_up_in_same_session(),
                    self._set_input_data(*args, **kwargs),
                    self._check_parameter_match(),
                    asyncio.create_task(self._storage_setup()),
                ),
            },
            RUN_MODE_NORMAL: {
                "manager": JobManager,
                "setup": lambda: (
                    self._clean_up_in_same_session(),
                    self._set_input_data(*args, **kwargs),
                    self._check_parameter_match(),
                    asyncio.create_task(self._storage_setup()),
                    self._generate_ids_and_update_target_count(),
                ),
            },
        }

        # Get the appropriate configuration
        config = job_manager_mapping.get(self.config.run_mode, job_manager_mapping[RUN_MODE_NORMAL])

        # Execute setup steps
        if config["setup"]:
            setup_results = config["setup"]()
            # Await any async tasks in the setup results
            for result in setup_results:
                if asyncio.isfuture(result) or isinstance(result, asyncio.Task):
                    await result

        # Initialize the job manager
        self.job_manager = config["manager"](
            master_job_config=self.config, state=self.state, storage=self.factory_storage, user_func=self.func, input_data_queue=self.input_data_queue
        )

    def _set_input_data(self, *args, **kwargs) -> None:
        """Helper method to set input data and original input data."""
        self.input_data_queue, self.original_input_data = _default_input_converter(*args, **kwargs)

    def _generate_ids_and_update_target_count(self) -> None:
        """Helper method to generate project and master job IDs."""
        self.config.project_id = str(uuid.uuid4())
        self.config.master_job_id = str(uuid.uuid4())
        # Adjusts the target count based on the input queue size if target_count is 0.
        target_count = self.target_count
        new_target_count = self.input_data_queue.qsize() if target_count == 0 else target_count
        self.config.target_count = new_target_count

    async def _setup_job_execution(self) -> None:
        """Prepare job for execution."""

        if self.config.run_mode == RUN_MODE_NORMAL:
            await self._save_project()
            await self._log_master_job_start()
        await self.job_manager.setup_input_output_queue()

    async def _finalize_job(self) -> List[dict[str, Any]]:
        """Complete job execution and return results."""
        result = None
        if self.job_manager:
            result = self._process_output()
            if len(result) == 0:
                self.err = OutputError("No records generated")

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
                "dead_queue_threshold": self.config.dead_queue_threshold,
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
            result = self._output_cache[status_filter].get(IDX, []) if is_idx else self._output_cache[status_filter].get("result", [])
            if len(result) == 0 and self._check_process_out(status_filter=status_filter) != 0:
                logger.warning("_output_cache is not correct, going to repopelate the cache")
            else:
                return result

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

        result = self._output_cache[status_filter].get(IDX, []) if is_idx else self._output_cache[status_filter].get("result", [])
        return result

    def _check_process_out(self, status_filter: str):
        res = None
        if status_filter == STATUS_COMPLETED:
            res = self.job_manager.completed_count
        elif status_filter == STATUS_DUPLICATE:
            res = self.job_manager.duplicate_count
        elif status_filter == STATUS_FAILED:
            res = self.job_manager.failed_count
        elif status_filter == STATUS_FILTERED:
            res = self.job_manager.filtered_count
        return res

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

    def _execute_job(self):
        """Initiate batch processing through the job manager.
        Note:
            Logs job start information and progress interval
        """
        if self.config.run_mode != RUN_MODE_RE_RUN:
            logger.info(
                f"\033[1m[JOB START]\033[0m "
                f"\033[36mMaster Job ID: {self.config.master_job_id}\033[0m | "
                f"\033[33mLogging progress every {PROGRESS_LOG_INTERVAL} seconds\033[0m"
            )

        self.job_manager.run_orchestration()

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

    async def _close_storage(self):
        """Clean up and close the storage connection.

        Ensures proper closure of storage resources when the job completes.
        """
        if self.factory_storage:
            await self.factory_storage.close()

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
            f"Duplicate: {self.job_manager.duplicate_count}, "
            f"InDeadQueue: {self.job_manager.dead_queue_count})"
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

        original_input_data.append({k: deepcopy(v) for k, v in record.items() if k != IDX})

    # Convert the list to an immutable tuple
    return results, original_input_data


def data_factory(
    storage: str = STORAGE_TYPE_LOCAL,
    batch_size: int = 1,
    target_count: int = 0,
    dead_queue_threshold: int = 3,
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
        storage: Storage backend to use ('local' or 'in_memory')
        batch_size: Number of records to process in each batch
        target_count: Target number of records to generate (0 means process all input)
        max_concurrency: Maximum number of concurrent tasks
        initial_state_values: Initial values for shared state
        on_record_complete: Callbacks to execute after successful record processing
        on_record_error: Callbacks to execute after failed record processing
        show_progress: Whether to display progress bar
        task_runner_timeout: Timeout in seconds for task execution
        job_run_stop_threshold: Threshold for stopping job if too many records fail

    Returns:
        Decorated function with additional execution methods
    """
    # Initialize default values
    on_record_error = on_record_error or []
    on_record_complete = on_record_complete or []
    initial_state_values = initial_state_values or {}

    # Create configuration
    config = FactoryMasterConfig(
        storage=storage,
        batch_size=batch_size,
        target_count=target_count,
        dead_queue_threshold=dead_queue_threshold,
        max_concurrency=max_concurrency,
        show_progress=show_progress,
        task_runner_timeout=task_runner_timeout,
        on_record_complete=on_record_complete,
        on_record_error=on_record_error,
        job_run_stop_threshold=job_run_stop_threshold,
    )

    # Initialize factory instance
    _factory = None

    def decorator(func: Callable[P, T]) -> DataFactoryProtocol[P, T]:
        """Actual decorator that wraps the function."""
        nonlocal _factory
        _factory = _initialize_or_update_factory(_factory, config, func, initial_state_values)
        wrapper = FactoryWrapper(_factory, func)
        return cast(DataFactoryProtocol[P, T], wrapper)

    # Add resume capability as a static method
    data_factory.resume_from_checkpoint = resume_from_checkpoint

    return decorator


def _initialize_or_update_factory(
    factory: Optional[Factory], config: FactoryMasterConfig, func: Callable[P, T], initial_state_values: Dict[str, Any]
) -> Factory:
    """Initialize or update a Factory instance."""
    if factory is None:
        factory = Factory(config, func)
        factory.state = MutableSharedState(initial_data=initial_state_values)
    else:
        factory.config = config
        factory.func = func
        factory.state = MutableSharedState(initial_data=initial_state_values)
    return factory


class FactoryExecutorManager:
    class Filters:
        """Handles filter-related operations"""

        filter_mapping = {("duplicated",): STATUS_DUPLICATE, ("completed",): STATUS_COMPLETED, ("failed",): STATUS_FAILED, ("filtered",): STATUS_FILTERED}
        valid_status = (STATUS_DUPLICATE, STATUS_COMPLETED, STATUS_FILTERED, STATUS_FAILED)

        @staticmethod
        def is_valid(filter: str) -> bool:
            """Check if a filter is valid"""
            return filter in FactoryExecutorManager.Filters.valid_status

        @staticmethod
        def convert(filter: str) -> str:
            """Convert a filter string to its corresponding status"""
            for keys, status in FactoryExecutorManager.Filters.filter_mapping.items():
                if filter in keys:
                    return status
            return filter

    class EventLoop:
        """Manages event loop operations"""

        @staticmethod
        def execute(callable_func: Callable, *args, **kwargs) -> List[dict[str, Any]]:
            """Execute an async callable in synchronous contexts"""
            _ensure_nest_asyncio()

            try:
                loop = asyncio.get_event_loop()
                logger.debug("Using existing event loop for execution")
                return loop.run_until_complete(callable_func(*args, **kwargs))
            except RuntimeError as e:
                logger.debug(f"Creating new event loop: {str(e)}")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(callable_func(*args, **kwargs))
                finally:
                    loop.close()
                    logger.debug("Closed newly created event loop")

    class DeadQueue:
        """Handles dead queue operations"""

        @staticmethod
        def get_indices_and_data(factory: Factory) -> tuple[List[dict], List[int]]:
            """Get dead queue indices and data"""
            if not hasattr(factory.job_manager, "dead_queue"):
                return [], []

            dead_input_data = []
            dead_input_indices = []
            for task_data in list(factory.job_manager.dead_queue.queue):
                dead_input_data.append(task_data)
                dead_input_indices.append(task_data[IDX])

            return dead_input_data, dead_input_indices

    class Resume:
        @staticmethod
        async def _not_same_session_factory(*args, **kwargs):
            factory = Factory(FactoryMasterConfig(storage=STORAGE_TYPE_LOCAL))
            if len(args) == 1:
                factory.config.master_job_id = args[0]
            else:
                raise InputError("Master job id is required, please pass it in the parameters")

            await factory._storage_setup()
            master_job_config_data, master_job = None, None
            master_job = await factory.factory_storage.get_master_job(factory.config.master_job_id)
            if master_job:
                master_job_config_data = await factory.factory_storage.get_request_config(master_job.request_config_ref)
            else:
                await factory._close_storage()
                raise InputError(f"Master job not found for master_job_id: {factory.config.master_job_id}")

            master_job = {
                "duplicate_count": master_job.duplicate_record_count,
                "failed_count": master_job.failed_record_count,
                "filtered_count": master_job.filtered_record_count,
                "completed_count": master_job.completed_record_count,
                "total_count": (
                    master_job.duplicate_record_count + master_job.failed_record_count + master_job.filtered_record_count + master_job.completed_record_count
                ),
            }

            factory.state = MutableSharedState(initial_data=master_job_config_data.get("state"))
            factory.config = FactoryMasterConfig.from_dict(master_job_config_data.get("config"))

            if func_serialized := master_job_config_data.get("func"):
                factory.func = cloudpickle.loads(bytes.fromhex(func_serialized))

            factory.config.prev_job = {"master_job": master_job, "input_data": master_job_config_data.get("input_data")}
            factory.original_input_data = [dict(item) for item in factory.config.prev_job["input_data"]]
            return factory

        @staticmethod
        async def _same_session_factory(*args, **kwargs):
            factory = kwargs["factory"]
            master_job = {
                "duplicate_count": factory.job_manager.duplicate_count,
                "failed_count": factory.job_manager.failed_count,
                "filtered_count": factory.job_manager.filtered_count,
                "completed_count": factory.job_manager.completed_count,
                "total_count": factory.job_manager.total_count,
            }
            factory._clean_up_in_same_session()
            factory.config.prev_job = {"master_job": master_job, "input_data": factory.original_input_data}
            return factory

        @staticmethod
        async def async_re_run(*args, **kwargs) -> List[Any]:
            factory = await (
                FactoryExecutorManager.Resume._same_session_factory if "factory" in kwargs else FactoryExecutorManager.Resume._not_same_session_factory
            )(*args, **kwargs)

            # Update config with any additional kwargs
            for key, value in kwargs.items():
                if hasattr(factory.config, key):
                    setattr(factory.config, key, value)

            await factory._storage_setup()

            if not factory.func or not factory.config:
                await factory._close_storage()
                raise NoResumeSupportError("Function does not support resume_from_checkpoint. Please ensure it supports cloudpickle serialization")

            factory.config.run_mode = RUN_MODE_RE_RUN
            factory.config_ref = factory.factory_storage.generate_request_config_path(factory.config.master_job_id)

            return await factory()

    @staticmethod
    def execute(callable_func: Callable, *args, **kwargs) -> List[dict[str, Any]]:
        """Execute an async callable"""
        return FactoryExecutorManager.EventLoop.execute(callable_func, *args, **kwargs)

    @staticmethod
    def resume(*args, **kwargs) -> List[dict[str, Any]]:
        """Re-run a previously executed data generation job"""
        valid_args = {
            "storage",
            "batch_size",
            "target_count",
            "max_concurrency",
            "initial_state_values",
            "on_record_complete",
            "on_record_error",
            "show_progress",
            "task_runner_timeout",
            "job_run_stop_threshold",
            "factory",
        }
        filtered_args = {k: v for k, v in kwargs.items() if k in valid_args and v is not None}
        return FactoryExecutorManager.execute(FactoryExecutorManager.Resume.async_re_run, *args, **filtered_args)

    @staticmethod
    def process_output(factory: Factory, filter: str = STATUS_COMPLETED, is_idx: bool = False) -> List[dict[str, Any]]:
        """Process and filter output data"""
        _filter = FactoryExecutorManager.Filters.convert(filter)
        if FactoryExecutorManager.Filters.is_valid(_filter):
            return factory._process_output(_filter, is_idx)
        raise InputError(f"Invalid filter '{filter}'. Supported filters are: {list(FactoryExecutorManager.Filters.filter_mapping.keys())}")

    @staticmethod
    def process_dead_queue(factory: Factory, is_idx: bool = False) -> List:
        """Process dead queue data"""
        result = FactoryExecutorManager.DeadQueue.get_indices_and_data(factory)
        return result[1] if is_idx else result[0]


# ====================
# Argument Handling
# ====================
def resume_from_checkpoint(*args, **kwargs) -> List[dict[str, Any]]:
    return FactoryExecutorManager.resume(*args, **kwargs)
