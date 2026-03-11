"""Public API: @data_factory decorator and FactoryWrapper.

No FactoryExecutorManager — direct FactoryWrapper → Factory flow.
"""
from typing import Any, Callable, Dict, List, Optional, cast

from starfish.common.logger import get_logger
from starfish.data_factory_v2.config import FactoryConfig, RetryPolicy
from starfish.data_factory_v2.constants import (
    DEFAULT_DEAD_QUEUE_THRESHOLD,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_TASK_RETRIES,
    DEFAULT_RATE_LIMIT,
    DEFAULT_STOP_THRESHOLD,
    DEFAULT_TASK_TIMEOUT,
    RUN_MODE_DRY_RUN,
    RUN_MODE_NORMAL,
    RUN_MODE_RESUME,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory_v2.errors import InputError
from starfish.data_factory_v2.event_loop import run_in_event_loop
from starfish.data_factory_v2.factory import Factory
from starfish.data_factory_v2.state import MutableSharedState

logger = get_logger(__name__)


class FactoryWrapper:
    """User-facing API returned by @data_factory.

    Provides .run(), .dry_run(), .resume(), and output accessors.
    Calls Factory directly — no intermediate manager layer.
    """

    def __init__(self, factory: Factory, func: Callable):
        self.factory = factory
        self.state = factory.state
        self.__func__ = func

    # ==================
    # Execution Methods
    # ==================

    def run(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Execute the pipeline normally."""
        self.factory.config.run_mode = RUN_MODE_NORMAL
        return run_in_event_loop(self.factory(*args, **kwargs))

    def dry_run(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Test run with 1 record, no persistence."""
        self.factory.config.run_mode = RUN_MODE_DRY_RUN
        return run_in_event_loop(self.factory(*args, **kwargs))

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
        task_timeout: int = None,
        stop_threshold: int = None,
    ) -> List[Dict[str, Any]]:
        """Resume from the last checkpoint."""
        # Build overrides from explicitly-passed args
        overrides = {
            k: v for k, v in {
                "storage": storage,
                "batch_size": batch_size,
                "target_count": target_count,
                "max_concurrency": max_concurrency,
                "on_record_complete": on_record_complete,
                "on_record_error": on_record_error,
                "show_progress": show_progress,
                "task_timeout": task_timeout,
                "stop_threshold": stop_threshold,
            }.items() if v is not None
        }

        if initial_state_values is not None:
            self.factory.state = MutableSharedState(initial_data=initial_state_values)

        # Same-session resume: use existing factory state
        factory = self.factory
        if factory.job_manager:
            # Build prev_job from current session
            jm = factory.job_manager
            factory.config.prev_job = {
                "master_job": {
                    "completed_count": jm.completed_count,
                    "failed_count": jm.failed_count,
                    "filtered_count": jm.filtered_count,
                    "duplicate_count": jm.duplicate_count,
                    "total_count": jm.total_count,
                },
                "input_data": factory.original_input_data,
            }

        for key, value in overrides.items():
            if hasattr(factory.config, key):
                setattr(factory.config, key, value)

        factory.config.run_mode = RUN_MODE_RESUME
        return run_in_event_loop(factory())

    # ==================
    # Output Accessors
    # ==================

    def get_output_data(self, filter: str) -> List[Dict[str, Any]]:
        status = _normalize_filter(filter)
        return self.factory.output_collector.get_output(status)

    def get_output_completed(self) -> List[Dict[str, Any]]:
        return self.factory.output_collector.get_output(STATUS_COMPLETED)

    def get_output_duplicate(self) -> List[Dict[str, Any]]:
        return self.factory.output_collector.get_output(STATUS_DUPLICATE)

    def get_output_filtered(self) -> List[Dict[str, Any]]:
        return self.factory.output_collector.get_output(STATUS_FILTERED)

    def get_output_failed(self) -> List[Dict[str, Any]]:
        return self.factory.output_collector.get_output(STATUS_FAILED)

    def get_input_data_in_dead_queue(self) -> List[Dict[str, Any]]:
        if self.factory.job_manager:
            return self.factory.job_manager.get_dead_queue_data()
        return []

    def get_input_data(self) -> List[Dict[str, Any]]:
        return self.factory.original_input_data

    # Index accessors
    def get_index(self, filter: str) -> List[int]:
        status = _normalize_filter(filter)
        return self.factory.output_collector.get_indices(status)

    def get_index_completed(self) -> List[int]:
        return self.factory.output_collector.get_indices(STATUS_COMPLETED)

    def get_index_duplicate(self) -> List[int]:
        return self.factory.output_collector.get_indices(STATUS_DUPLICATE)

    def get_index_filtered(self) -> List[int]:
        return self.factory.output_collector.get_indices(STATUS_FILTERED)

    def get_index_failed(self) -> List[int]:
        return self.factory.output_collector.get_indices(STATUS_FAILED)

    def get_index_dead_queue(self) -> List[int]:
        if self.factory.job_manager:
            items = self.factory.job_manager.get_dead_queue_data()
            from starfish.data_factory_v2.constants import IDX
            return [item.get(IDX) for item in items]
        return []


def _normalize_filter(f: str) -> str:
    """Convert user-facing filter names to internal status constants."""
    mapping = {
        "duplicated": STATUS_DUPLICATE,
        "completed": STATUS_COMPLETED,
        "failed": STATUS_FAILED,
        "filtered": STATUS_FILTERED,
    }
    return mapping.get(f, f)


# ==================
# Decorator
# ==================

def data_factory(
    storage: str = STORAGE_TYPE_LOCAL,
    batch_size: int = 1,
    target_count: int = 0,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    dead_queue_threshold: int = DEFAULT_DEAD_QUEUE_THRESHOLD,
    max_task_retries: int = DEFAULT_MAX_TASK_RETRIES,
    initial_state_values: Optional[Dict[str, Any]] = None,
    on_record_complete: Optional[List[Callable]] = None,
    on_record_error: Optional[List[Callable]] = None,
    show_progress: bool = True,
    task_timeout: int = DEFAULT_TASK_TIMEOUT,
    stop_threshold: int = DEFAULT_STOP_THRESHOLD,
    rate_limit: float = DEFAULT_RATE_LIMIT,
    project_name: Optional[str] = None,
) -> Callable:
    """Decorator that transforms an async function into a data factory pipeline.

    Args:
        storage: 'local' (SQLite + filesystem) or 'in_memory'
        batch_size: Records per batch
        target_count: Target output count (0 = process all)
        max_concurrency: Max parallel tasks
        dead_queue_threshold: Failures before dead-queuing a record
        max_task_retries: Within-task retry attempts
        initial_state_values: Initial shared state dict
        on_record_complete: Hooks called after success (can return 'duplicate'/'filtered')
        on_record_error: Hooks called after failure
        show_progress: Enable progress logging
        task_timeout: Seconds before task timeout
        stop_threshold: Consecutive failures before job stops
        rate_limit: Max requests/second (0 = unlimited)
        project_name: Optional project name for metadata
    """
    on_record_complete = on_record_complete or []
    on_record_error = on_record_error or []
    initial_state_values = initial_state_values or {}

    config = FactoryConfig(
        storage=storage,
        batch_size=batch_size,
        target_count=target_count,
        max_concurrency=max_concurrency,
        retry_policy=RetryPolicy(
            max_task_retries=max_task_retries,
            dead_queue_threshold=dead_queue_threshold,
        ),
        on_record_complete=on_record_complete,
        on_record_error=on_record_error,
        show_progress=show_progress,
        task_timeout=task_timeout,
        stop_threshold=stop_threshold,
        rate_limit=rate_limit,
        project_name=project_name,
    )

    def decorator(func: Callable) -> FactoryWrapper:
        factory = Factory(config, func)
        factory.state = MutableSharedState(initial_data=initial_state_values)
        return FactoryWrapper(factory, func)

    return decorator


async def resume_from_checkpoint(master_job_id: str, **kwargs) -> List[Dict[str, Any]]:
    """Resume a job from checkpoint using a master_job_id.

    Loads the function, config, and state from storage.
    """
    factory = await Factory.resume_from_storage(master_job_id, **kwargs)
    return await factory()
