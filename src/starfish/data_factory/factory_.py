import asyncio
from copy import deepcopy
import datetime
import uuid
from inspect import Parameter, signature
from asyncio import Queue, QueueFull
from typing import Any, Callable, Dict, List

import cloudpickle
from starfish.data_factory.utils.errors import InputError, OutputError
from starfish.data_factory.utils.util import get_platform_name
from starfish.version import __version__
from starfish.common.logger import get_logger
from starfish.data_factory.config import PROGRESS_LOG_INTERVAL
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
from starfish.telemetry.posthog_client import Event, analytics
from copy import deepcopy

logger = get_logger(__name__)


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
            self._show_final_job_progress_status()

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
                logger.info(f"[RESUME INFO] 🚨 Job stopped unexpectedly. You can resume the job by calling .resume()")
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
        # Directly iterate through the underlying deque for performance
        # 1,No Concurrency: no other coroutines or threads are modifying the queue (e.g., adding or removing items).
        # 2. No Further Use of the Queue: The queue will not be used again after this step, so it doesn't matter if the items remain in the queue.
        # 3,No Size Limits: The queue does not have a maxsize limit that could be violated by leaving items in the queue.
        for record in self.job_manager.job_output._queue:
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
            if batch_param != IDX and batch_param not in func_sig.parameters:
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

    def _show_final_job_progress_status(self):
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

        # Add DLQ retrieval information if there are items in the dead queue
        if self.job_manager.dead_queue_count > 0:
            logger.warning(
                f"\033[1;31m[DLQ]\033[0m {self.job_manager.dead_queue_count} items failed after {self.config.dead_queue_threshold} retries. "
                f"Retrieve its index with: \033[1mfunction_name.get_index_dead_queue()\033[0m"
            )


def _default_input_converter(data: List[Dict[str, Any]] = None, **kwargs) -> tuple[Queue[Dict[str, Any]], list[Dict[str, Any]]]:
    """Convert input data into a queue of records for processing.

    Args:
        data (List[Dict[str, Any]], optional): List of input data records. Defaults to None.
        **kwargs: Additional parameters that can be either parallel sources or broadcast values

    Returns:
        asyncio.Queue[Dict[str, Any]]: Queue of records ready for processing

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
    # Prepare input data queue and records
    input_data_queue = Queue()
    records = []

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

        records.append(record)

    # Add all records to the queue
    for record in records:
        try:
            input_data_queue.put_nowait(record)
        except QueueFull:
            raise InputError("Queue is full - cannot add more items")

    return input_data_queue, deepcopy(records)
