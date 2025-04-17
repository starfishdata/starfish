import asyncio
import datetime
import uuid
from functools import wraps
from inspect import Parameter, signature
from queue import Queue
from typing import Any, Callable, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory.config import PROGRESS_LOG_INTERVAL, TASK_RUNNER_TIMEOUT
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
from starfish.data_factory.utils.data_class import FactoryMasterConfig
from starfish.data_factory.utils.decorator import async_wrapper
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)


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
        input_data (Queue): Queue holding input data to be processed
        factory_storage: Storage backend instance
        config_ref: Reference to the stored configuration
        err: Error object if any occurred during processing
    """

    def __init__(self, master_job_config: FactoryMasterConfig, func: Callable):
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
                - input_converter: Function to convert input data to Queue format
                - state: Shared state object for tracking job state
            func (Callable): The data processing function to be wrapped
        """
        self.config = master_job_config
        self.func = func
        self.input_data = Queue()
        self.factory_storage = None
        self.config.master_job_id = None
        self.err = None
        self.config_ref = None

    def __call__(self, *args, **kwargs):
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
        # self.job_manager.add_job(func)
        self._storage_setup()
        run_mode = self.config.run_mode
        try:
            # Check for master_job_id in kwargs and assign if present
            if run_mode == RUN_MODE_RE_RUN:
                self.job_manager = JobManagerRerun(job_config=self.config, storage=self.factory_storage, user_func=self.func)
            elif run_mode == RUN_MODE_DRY_RUN:
                # dry run mode
                self.input_data = self.config.input_converter(*args, **kwargs)
                # Get only first item but maintain Queue structure
                self._check_parameter_match()
                self.job_manager = JobManagerDryRun(job_config=self.config, storage=self.factory_storage, user_func=self.func, input_data_queue=self.input_data)
            else:
                self.input_data = self.config.input_converter(*args, **kwargs)
                self._check_parameter_match()
                self._update_job_config()
                self.config.project_id = str(uuid.uuid4())
                # self.project_id = "8de05a58-c8a4-4c10-8c23-568679c88e65"
                self.config.master_job_id = str(uuid.uuid4())

                self.job_manager = JobManager(
                    master_job_config=self.config, storage=self.factory_storage, input_data_queue=self.input_data, user_func=self.func
                )

                self._save_project()
                self._save_request_config()
                self._log_master_job_start()
            self.job_manager.setup_input_output_queue()
            self._process_batches()

        except (TypeError, ValueError, KeyboardInterrupt) as e:
            self.err = e
            # raise e
        finally:
            if not isinstance(self.err, TypeError):
                result = self._process_output()
                if len(result) == 0:
                    self.err = ValueError("No records generated")

                self._complete_master_job()
                self._close_storage()
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
                self._close_storage()
                raise self.err

    def _process_output(self) -> List[Any]:
        result = []
        output = self.job_manager.job_output.queue
        for v in output:
            if v.get(RECORD_STATUS) == STATUS_COMPLETED:
                result.extend(v.get("output"))
        return result

    def _check_parameter_match(self):
        """Check if the parameters of the function match the parameters of the batches."""
        # Get the parameters of the function
        # func_params = inspect.signature(func).parameters
        # # Get the parameters of the batches
        # batches_params = inspect.signature(batches).parameters
        # from inspect import signature, Parameter
        func_sig = signature(self.func)

        # Validate batch items against function parameters
        batch_item = self.input_data.queue[0]
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
        """Process batches with asyncio."""
        if self.config.run_mode != RUN_MODE_RE_RUN:
            logger.info(
                f"\033[1m[JOB START]\033[0m "
                f"\033[36mMaster Job ID: {self.config.master_job_id}\033[0m | "
                f"\033[33mLogging progress every {PROGRESS_LOG_INTERVAL} seconds\033[0m"
            )
        return self.job_manager.run_orchestration()

    @async_wrapper()
    async def _save_project(self):
        project = Project(project_id=self.config.project_id, name="Test Project", description="A test project for storage layer testing")
        await self.factory_storage.save_project(project)

    @async_wrapper()
    async def _save_request_config(self):
        logger.debug("\n2. Creating master job...")
        # First save the request config
        config_data = {"generator": "test_generator", "parameters": {"num_records": 10, "complexity": "medium"}, "input_data": list(self.input_data.queue)}
        self.config_ref = await self.factory_storage.save_request_config(self.config.master_job_id, config_data)
        logger.debug(f"  - Saved request config to: {self.config_ref}")

    @async_wrapper()
    async def _log_master_job_start(self):
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

    @async_wrapper()
    async def _complete_master_job(self):
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

    @async_wrapper()
    async def _close_storage(self):
        if self.factory_storage:
            await self.factory_storage.close()

    def _storage_setup(self):
        if self.config.storage == STORAGE_TYPE_LOCAL:
            self.factory_storage = LocalStorage(LOCAL_STORAGE_URI)
            asyncio.run(self.factory_storage.setup())
        else:
            self.factory_storage = InMemoryStorage()
            asyncio.run(self.factory_storage.setup())

    def _update_job_config(self):
        target_count = self.config.target_count
        new_target_count = self.input_data.qsize() if target_count == 0 else target_count
        self.config.target_count = new_target_count

    def _show_job_progress_status(self):
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


# Public decorator interface
def data_factory(
    storage: str = "local",
    batch_size: int = 1,
    target_count: int = 0,
    max_concurrency: int = 50,
    initial_state_values: Dict[str, Any] = None,
    on_record_complete: List[Callable] = None,
    on_record_error: List[Callable] = None,
    show_progress: bool = True,
    input_converter=_default_input_converter,
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT,
    job_run_stop_threshold: int = 3,
):
    """Decorator factory for creating data processing pipelines.

    Args:
        storage (str): Storage backend to use ('local' or 'in_memory'). Defaults to 'local'.
        batch_size (int): Number of records to process in each batch. Defaults to 1.
        target_count (int): Target number of records to generate. 0 means process all input. Defaults to 0.
        max_concurrency (int): Maximum number of concurrent tasks. Defaults to 50.
        initial_state_values (Dict[str, Any]): Initial values for shared state. Defaults to empty dict.
        on_record_complete (List[Callable]): Callbacks to execute after each successful record processing.
        on_record_error (List[Callable]): Callbacks to execute after each failed record processing.
        show_progress (bool): Whether to display progress bar. Defaults to True.
        input_converter (Callable): Function to convert input data to Queue format. Defaults to _default_input_converter.
        task_runner_timeout (int): Timeout in seconds for task execution. Defaults to TASK_RUNNER_TIMEOUT.
        job_run_stop_threshold (int): Number of times to retry a failed job. Defaults to 3.

    Returns:
        DataFactory: Configured data factory instance to be used as a decorator.

    Example:
        @data_factory(storage='local', max_concurrency=50)
        def process_data(item):
            # data processing logic
            return processed_data
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
        input_converter=input_converter,
        state=MutableSharedState(initial_state_values),
        job_run_stop_threshold=job_run_stop_threshold,
    )

    def decorator(func: Callable):
        factory = DataFactory(master_job_config, func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return factory(*args, **kwargs)

        wrapper.state = factory.config.state

        # Add run method to the wrapped function
        def run(*args, **kwargs):
            return wrapper(*args, **kwargs)

        def re_run(*args, **kwargs):
            if len(args) == 1:
                factory.config.master_job_id = args[0]
            elif "master_job_id" in kwargs:
                factory.config.master_job_id = kwargs.get("master_job_id")
            else:
                raise TypeError("Master job id is required")
            factory.config.run_mode = RUN_MODE_RE_RUN
            return wrapper(*args, **kwargs)

        def dry_run(*args, **kwargs):
            factory.config.run_mode = RUN_MODE_DRY_RUN
            return wrapper(*args, **kwargs)

        wrapper.run = run
        wrapper.re_run = re_run
        wrapper.dry_run = dry_run
        return wrapper

    return decorator
