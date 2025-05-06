from typing import Any, Callable, Dict, Generic, List, Optional, ParamSpec, TypeVar, Protocol
from starfish.data_factory.constants import (
    RUN_MODE_DRY_RUN,
    RUN_MODE_NORMAL,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory.config import NOT_COMPLETED_THRESHOLD, TASK_RUNNER_TIMEOUT
from starfish.data_factory.factory_ import Factory
from starfish.data_factory.factory_executor_manager import FactoryExecutorManager
from starfish.common.logger import get_logger

logger = get_logger(__name__)

# Create a type variable for the function type
F = TypeVar("F", bound=Callable[..., Any])

# Add this line after the other type-related imports
P = ParamSpec("P")

T = TypeVar("T")


class FactoryWrapper(Generic[T]):
    """Wrapper class that provides execution methods for data factory pipelines.

    This class acts as the interface returned by the @data_factory decorator,
    providing methods to run, dry-run, and resume data processing jobs.

    Attributes:
        factory (Factory): The underlying Factory instance
        state: Shared state object for tracking job state
    """

    def __init__(self, factory: Factory, func: Callable[..., T]):
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
