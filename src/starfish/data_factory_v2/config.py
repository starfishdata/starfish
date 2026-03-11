from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import cloudpickle

from starfish.data_factory_v2.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DEAD_QUEUE_THRESHOLD,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_TASK_RETRIES,
    DEFAULT_RATE_LIMIT,
    DEFAULT_STOP_THRESHOLD,
    DEFAULT_TASK_TIMEOUT,
    RUN_MODE_NORMAL,
    STORAGE_TYPE_LOCAL,
)


@dataclass
class RetryPolicy:
    """Unified retry configuration.

    Controls both within-task retries (TaskRunner) and cross-task retries (dead queue).
    """

    max_task_retries: int = DEFAULT_MAX_TASK_RETRIES
    dead_queue_threshold: int = DEFAULT_DEAD_QUEUE_THRESHOLD
    backoff_base: float = 2.0
    backoff_max: float = 30.0

    def get_delay(self, attempt: int) -> float:
        """Exponential backoff with cap."""
        return min(self.backoff_base ** attempt, self.backoff_max)


@dataclass
class FactoryConfig:
    """Master configuration for a data factory pipeline.

    This is the single source of truth for all pipeline settings.
    """

    # Storage
    storage: str = STORAGE_TYPE_LOCAL

    # Job identity (set at runtime)
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    master_job_id: Optional[str] = None

    # Processing
    batch_size: int = DEFAULT_BATCH_SIZE
    target_count: int = 0  # 0 = process all input
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    task_timeout: int = DEFAULT_TASK_TIMEOUT
    rate_limit: float = DEFAULT_RATE_LIMIT  # requests per second, 0 = unlimited

    # Retry
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)

    # Hooks
    on_record_complete: List[Callable] = field(default_factory=list)
    on_record_error: List[Callable] = field(default_factory=list)

    # Display
    show_progress: bool = True

    # Run control
    run_mode: str = RUN_MODE_NORMAL
    stop_threshold: int = DEFAULT_STOP_THRESHOLD

    # Resume data (populated internally)
    prev_job: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "FactoryConfig":
        """Deserialize from dict, handling cloudpickle-encoded callables."""
        data = data.copy()

        # Deserialize hooks
        data["on_record_complete"] = [
            cloudpickle.loads(bytes.fromhex(c)) if c else None
            for c in data.get("on_record_complete", [])
        ]
        data["on_record_error"] = [
            cloudpickle.loads(bytes.fromhex(c)) if c else None
            for c in data.get("on_record_error", [])
        ]

        # Deserialize retry_policy if present
        if "retry_policy" in data and isinstance(data["retry_policy"], dict):
            data["retry_policy"] = RetryPolicy(**data["retry_policy"])

        return cls(**data)

    def to_dict(self) -> dict:
        """Serialize to dict, encoding callables with cloudpickle."""
        import dataclasses
        result = dataclasses.asdict(self)

        # Serialize hooks
        result["on_record_complete"] = [cloudpickle.dumps(c).hex() for c in self.on_record_complete]
        result["on_record_error"] = [cloudpickle.dumps(c).hex() for c in self.on_record_error]

        return result
