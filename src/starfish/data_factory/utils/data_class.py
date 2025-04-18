from dataclasses import dataclass, field
from typing import Callable, List

from starfish.data_factory.config import TASK_RUNNER_TIMEOUT
from starfish.data_factory.constants import RUN_MODE_NORMAL, STORAGE_TYPE_LOCAL


@dataclass
class FactoryMasterConfig:
    """Configuration class for the master job in the data factory.

    Attributes:
        storage: Storage type to use (default: local)
        master_job_id: Unique identifier for the master job
        project_id: Identifier for the associated project
        batch_size: Number of records to process in each batch
        target_count: Total number of records to process
        max_concurrency: Maximum number of concurrent tasks
        show_progress: Whether to display progress information
        task_runner_timeout: Timeout for task execution
        on_record_complete: List of callbacks for record completion
        on_record_error: List of callbacks for record errors
        input_converter: Function to convert input data
        state: Shared state object for job coordination
        run_mode: Execution mode for the job
        job_run_stop_threshold: Number of times to retry a failed job
    """

    storage: str = STORAGE_TYPE_LOCAL
    master_job_id: str = None
    project_id: str = None
    batch_size: int = 1
    target_count: int = 0
    max_concurrency: int = 50
    show_progress: bool = True
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT
    on_record_complete: List[Callable] = field(default_factory=list)
    on_record_error: List[Callable] = field(default_factory=list)
    input_converter: Callable = None
    run_mode: str = RUN_MODE_NORMAL
    job_run_stop_threshold: int = 3

    @classmethod
    def from_dict(cls, data: dict):
        """Create a FactoryMasterConfig instance from a dictionary.

        Args:
            data (dict): Dictionary containing the configuration data. Expected keys:
                - storage: Storage type string
                - master_job_id: Unique job identifier
                - project_id: Project identifier
                - batch_size: Number of records per batch
                - target_count: Total records to process
                - max_concurrency: Maximum concurrent tasks
                - show_progress: Whether to show progress
                - task_runner_timeout: Task timeout in seconds
                - on_record_complete: List of callable strings for record completion
                - on_record_error: List of callable strings for record errors
                - input_converter: Callable string for input conversion
                - run_mode: Execution mode string
                - job_run_stop_threshold: Job retry threshold

        Returns:
            FactoryMasterConfig: A new instance of FactoryMasterConfig
        """
        import importlib

        # Handle callables
        def _import_callable(callable_str: str):
            """Convert string representation back to callable."""
            if not callable_str:
                return None
            module_name, func_name = callable_str.rsplit(".", 1)
            module = importlib.import_module(module_name)
            return getattr(module, func_name)

        data = data.copy()

        # Deserialize callables
        data["on_record_complete"] = [_import_callable(c) for c in data.get("on_record_complete", [])]
        data["on_record_error"] = [_import_callable(c) for c in data.get("on_record_error", [])]
        data["input_converter"] = _import_callable(data.get("input_converter"))

        # Initialize a fresh state object instead of trying to deserialize it
        from starfish.data_factory.utils.state import MutableSharedState

        data["state"] = MutableSharedState()

        return cls(**data)

    def to_dict(self):
        """Convert the FactoryMasterConfig instance to a dictionary.

        Handles serialization of callables and removes non-serializable state.

        Returns:
            dict: Dictionary representation of the configuration
        """
        import dataclasses

        def _serialize_callable(callable_obj):
            """Convert callable to string representation."""
            if callable_obj is None:
                return None
            return f"{callable_obj.__module__}.{callable_obj.__name__}"

        result = dataclasses.asdict(self)

        # Remove state before serialization as it may contain locks
        if "state" in result:
            del result["state"]

        # Serialize callables
        result["on_record_complete"] = [_serialize_callable(c) for c in self.on_record_complete]
        result["on_record_error"] = [_serialize_callable(c) for c in self.on_record_error]
        result["input_converter"] = _serialize_callable(self.input_converter)

        return result

    def to_json(self):
        """Convert the FactoryMasterConfig instance to a JSON string.

        Returns:
            str: JSON string representation of the configuration
        """
        import json

        return json.dumps(self.to_dict(), indent=2)


@dataclass
class FactoryJobConfig:
    """Configuration class for individual jobs in the data factory.

    Attributes:
        master_job_id (str): Identifier of the parent master job
        batch_size (int): Number of records to process in each batch
        target_count (int): Total number of records to process
        show_progress (bool): Whether to display progress information
        task_runner_timeout (int): Timeout for task execution in seconds
        user_func (Callable): User-defined function to process records
        run_mode (str): Execution mode for the job
        max_concurrency (int): Maximum number of concurrent tasks
        on_record_complete (List[Callable]): List of callbacks for record completion
        on_record_error (List[Callable]): List of callbacks for record errors
        job_run_stop_threshold (int): Number of times to retry a failed job
    """

    master_job_id: str = None
    batch_size: int = 1
    target_count: int = 0
    show_progress: bool = True
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT
    user_func: Callable = None
    run_mode: str = RUN_MODE_NORMAL
    max_concurrency: int = 50
    on_record_complete: List[Callable] = field(default_factory=list)
    on_record_error: List[Callable] = field(default_factory=list)
    job_run_stop_threshold: int = 3
