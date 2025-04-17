from dataclasses import dataclass, field
from typing import Callable, List

from starfish.data_factory.config import TASK_RUNNER_TIMEOUT
from starfish.data_factory.constants import RUN_MODE_NORMAL, STORAGE_TYPE_LOCAL
from starfish.data_factory.utils.state import MutableSharedState


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
    state: MutableSharedState = field(default_factory=MutableSharedState)
    run_mode: str = RUN_MODE_NORMAL
    job_run_stop_threshold: int = 3


@dataclass
class FactoryJobConfig:
    """Configuration class for individual jobs in the data factory.

    Attributes:
        master_job_id: Identifier of the parent master job
        batch_size: Number of records to process in each batch
        target_count: Total number of records to process
        show_progress: Whether to display progress information
        task_runner_timeout: Timeout for task execution
        user_func: User-defined function to process records
        run_mode: Execution mode for the job
        max_concurrency: Maximum number of concurrent tasks
        on_record_complete: List of callbacks for record completion
        on_record_error: List of callbacks for record errors
        job_run_stop_threshold: Number of times to retry a failed job
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
