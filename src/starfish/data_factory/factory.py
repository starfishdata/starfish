from typing import Any, Callable, Dict, List, Optional, cast
from starfish.common.logger import get_logger
from starfish.data_factory.config import NOT_COMPLETED_THRESHOLD, TASK_RUNNER_TIMEOUT
from starfish.data_factory.constants import STORAGE_TYPE_LOCAL
from starfish.data_factory.factory_ import Factory
from starfish.data_factory.factory_wrapper import FactoryWrapper, DataFactoryProtocol, P, T
from starfish.data_factory.factory_executor_manager import FactoryExecutorManager
from starfish.data_factory.utils.data_class import FactoryMasterConfig
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)


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


def resume_from_checkpoint(*args, **kwargs) -> List[dict[str, Any]]:
    """Decorator for creating data processing pipelines.

    Args:
        master_job_id : resume for this master job
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
        List[Dict(str,Any)]
    """
    return FactoryExecutorManager.resume(*args, **kwargs)
