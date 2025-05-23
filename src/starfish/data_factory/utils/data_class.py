from dataclasses import dataclass, field
from typing import Callable, List

import cloudpickle

from starfish.data_factory.config import TASK_RUNNER_TIMEOUT
from starfish.data_factory.constants import RUN_MODE_NORMAL, STORAGE_TYPE_LOCAL


@dataclass
class FactoryMasterConfig:
    """Configuration class for the master job in the data factory.

    This class represents the configuration settings for the master job that controls
    the overall data processing workflow. It includes settings for storage, job
    identification, batch processing, concurrency, and callbacks.

    Attributes:
        storage (str): Storage type to use (default: local)
        master_job_id (str): Unique identifier for the master job
        project_id (str): Identifier for the associated project
        batch_size (int): Number of records to process in each batch
        target_count (int): Total number of records to process
        max_concurrency (int): Maximum number of concurrent tasks
        show_progress (bool): Whether to display progress information
        task_runner_timeout (int): Timeout for task execution in seconds
        on_record_complete (List[Callable]): List of callbacks for record completion
        on_record_error (List[Callable]): List of callbacks for record errors
        run_mode (str): Execution mode for the job
        job_run_stop_threshold (int): Number of times to retry a failed job
        prev_job (dict): Dictionary containing previous job information
    """

    storage: str = STORAGE_TYPE_LOCAL
    master_job_id: str = None
    project_id: str = None
    batch_size: int = 1
    target_count: int = 0
    dead_queue_threshold: int = 3
    max_concurrency: int = 50
    show_progress: bool = True
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT
    on_record_complete: List[Callable] = field(default_factory=list)
    on_record_error: List[Callable] = field(default_factory=list)
    run_mode: str = RUN_MODE_NORMAL
    job_run_stop_threshold: int = 3
    prev_job: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        """Create a FactoryMasterConfig instance from a dictionary.

        This class method constructs a FactoryMasterConfig object from a dictionary
        representation. It handles the deserialization of callable functions using
        cloudpickle.

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
                - run_mode: Execution mode string
                - job_run_stop_threshold: Job retry threshold

        Returns:
            FactoryMasterConfig: A new instance of FactoryMasterConfig

        Raises:
            ValueError: If required fields are missing or invalid
            cloudpickle.PickleError: If callable deserialization fails
        """
        data = data.copy()

        # Deserialize callables using cloudpickle
        data["on_record_complete"] = [cloudpickle.loads(bytes.fromhex(c)) if c else None for c in data.get("on_record_complete", [])]
        data["on_record_error"] = [cloudpickle.loads(bytes.fromhex(c)) if c else None for c in data.get("on_record_error", [])]

        return cls(**data)

    def to_dict(self):
        """Convert the FactoryMasterConfig instance to a dictionary.

        This method serializes the configuration object into a dictionary format,
        including the serialization of callable functions using cloudpickle.

        Returns:
            dict: Dictionary representation of the configuration

        Raises:
            cloudpickle.PickleError: If callable serialization fails
        """
        import dataclasses

        result = dataclasses.asdict(self)

        # Serialize callables using cloudpickle and encode to base64
        result["on_record_complete"] = [cloudpickle.dumps(c).hex() for c in self.on_record_complete]
        result["on_record_error"] = [cloudpickle.dumps(c).hex() for c in self.on_record_error]

        return result

    def to_json(self):
        """Convert the FactoryMasterConfig instance to a JSON string.

        This method provides a JSON serialization of the configuration object,
        suitable for storage or transmission.

        Returns:
            str: JSON string representation of the configuration

        Raises:
            json.JSONDecodeError: If JSON serialization fails
        """
        import json

        return json.dumps(self.to_dict(), indent=2)

    def update(self, data: dict):
        """Update the configuration from a dictionary.

        This method updates the configuration fields from a dictionary. It handles
        the deserialization of callable functions using cloudpickle.

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
                - run_mode: Execution mode string
                - job_run_stop_threshold: Job retry threshold

        Raises:
            ValueError: If invalid fields are provided
            cloudpickle.PickleError: If callable deserialization fails
        """
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")

        # Handle callable deserialization
        if "on_record_complete" in data:
            self.on_record_complete = [cloudpickle.loads(bytes.fromhex(c)) if c else None for c in data["on_record_complete"]]
        if "on_record_error" in data:
            self.on_record_error = [cloudpickle.loads(bytes.fromhex(c)) if c else None for c in data["on_record_error"]]

        # Update other fields
        for key, value in data.items():
            if key not in ["on_record_complete", "on_record_error"] and hasattr(self, key):
                setattr(self, key, value)


@dataclass
class FactoryJobConfig:
    """Configuration class for individual jobs in the data factory.

    This class represents the configuration settings for individual jobs that
    are part of the larger data processing workflow. It includes settings for
    job identification, batch processing, user-defined functions, and callbacks.

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
    dead_queue_threshold: int = 3
    show_progress: bool = True
    task_runner_timeout: int = TASK_RUNNER_TIMEOUT
    user_func: Callable = None
    run_mode: str = RUN_MODE_NORMAL
    max_concurrency: int = 50
    on_record_complete: List[Callable] = field(default_factory=list)
    on_record_error: List[Callable] = field(default_factory=list)
    job_run_stop_threshold: int = 3


@dataclass
class TelemetryData:
    """Class representing telemetry data for data processing jobs.

    This class captures various metrics and statistics about the execution of data processing jobs,
    including job configuration, execution time, and outcome summaries.

    Attributes:
        job_id (str): Identifier for the job
        target_reached (bool): Whether the target count was achieved
        run_mode (str): Execution mode of the job
        num_inputs (int): Number of input records processed
        library_version (str): Version of the processing library
        config (dict): Configuration parameters used for the job
        execution_time (float): Total execution time in seconds
        count_summary (dict): Summary of record processing outcomes
        error_summary (dict): Summary of errors encountered during processing
    """

    job_id: str = ""
    target_reached: bool = False
    run_mode: str = ""
    run_time_platform: str = ""
    num_inputs: int = 0
    library_version: str = "starfish-core"
    config: dict = field(
        default_factory=lambda: {
            "batch_size": 0,
            "target_count": 0,
            "dead_queue_threshold": 0,
            "max_concurrency": 0,
            "task_runner_timeout": 0,
            "job_run_stop_threshold": 0,
        }
    )
    execution_time: float = 0.0
    count_summary: dict = field(default_factory=lambda: {"completed": 0, "failed": 0, "filtered": 0, "duplicate": 0})
    error_summary: dict = field(default_factory=lambda: {"total_errors": 0, "error_types": {}})

    def to_dict(self) -> dict:
        """Convert the TelemetryData instance to a dictionary.

        This method converts all the telemetry data fields into a dictionary format,
        making it suitable for serialization or further processing.

        Returns:
            dict: Dictionary representation of the telemetry data containing:
                - job_id: Identifier for the job
                - target_reached: Whether the target count was achieved
                - run_mode: Execution mode of the job
                - num_inputs: Number of input records processed
                - library_version: Version of the processing library
                - config: Configuration parameters used for the job
                - execution_time: Total execution time in seconds
                - count_summary: Summary of record processing outcomes
                - error_summary: Summary of errors encountered during processing
        """
        import dataclasses

        return dataclasses.asdict(self)
