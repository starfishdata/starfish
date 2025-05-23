import asyncio
import sys
from typing import Any, Callable, List

import cloudpickle
from starfish.data_factory.utils.errors import InputError, NoResumeSupportError
from starfish.common.logger import get_logger
from starfish.data_factory.constants import IDX, STORAGE_TYPE_LOCAL, STATUS_COMPLETED, STATUS_DUPLICATE, STATUS_FAILED, STATUS_FILTERED, RUN_MODE_RE_RUN
from starfish.data_factory.factory_ import Factory
from starfish.data_factory.utils.data_class import FactoryMasterConfig
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)

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
            for task_data in factory.job_manager.dead_queue._queue:
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
        async def resume(*args, **kwargs) -> List[Any]:
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
        return FactoryExecutorManager.execute(FactoryExecutorManager.Resume.resume, *args, **filtered_args)

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
