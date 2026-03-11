"""Thin orchestrator — wires together components without being a God Object.

Responsibilities:
- Lifecycle coordination (init → setup → execute → finalize)
- Delegates to: InputConverter, JobLifecycle, JobManager, OutputCollector

Does NOT handle:
- Input parsing (InputConverter)
- Output filtering (OutputCollector)
- Storage persistence (JobLifecycle)
- Task execution (JobManager/TaskRunner)
"""
import uuid
from asyncio import Queue
from typing import Any, Callable, Dict, List, Optional

import cloudpickle

from starfish.common.logger import get_logger
from starfish.data_factory_v2.config import FactoryConfig
from starfish.data_factory_v2.constants import (
    DEFAULT_PROGRESS_INTERVAL,
    LOCAL_STORAGE_URI,
    RUN_MODE_DRY_RUN,
    RUN_MODE_NORMAL,
    RUN_MODE_RESUME,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory_v2.errors import InputError, NoResumeSupportError, OutputError
from starfish.data_factory_v2.input_converter import convert_input, validate_params
from starfish.data_factory_v2.job_lifecycle import JobLifecycle
from starfish.data_factory_v2.job_manager import JobManager
from starfish.data_factory_v2.job_manager_dry_run import JobManagerDryRun
from starfish.data_factory_v2.job_manager_rerun import JobManagerRerun
from starfish.data_factory_v2.output_collector import OutputCollector
from starfish.data_factory_v2.state import MutableSharedState
from starfish.data_factory_v2.storage_in_memory import InMemoryStorageV2 as InMemoryStorage
from starfish.data_factory.storage.local.local_storage import LocalStorage

logger = get_logger(__name__)

# Map run modes to job manager classes
_JOB_MANAGERS = {
    RUN_MODE_NORMAL: JobManager,
    RUN_MODE_DRY_RUN: JobManagerDryRun,
    RUN_MODE_RESUME: JobManagerRerun,
}


class Factory:
    """Thin orchestrator for data factory pipelines.

    Coordinates the lifecycle phases without owning business logic.
    """

    def __init__(self, config: FactoryConfig, func: Callable = None):
        self.config = config
        self.func = func
        self.state: Optional[MutableSharedState] = None
        self.original_input_data: List[Dict[str, Any]] = []

        # Components (created per-run)
        self._storage = None
        self._lifecycle: Optional[JobLifecycle] = None
        self._job_manager: Optional[JobManager] = None
        self._output = OutputCollector()
        self._err: Optional[Exception] = None

    @property
    def job_manager(self) -> Optional[JobManager]:
        return self._job_manager

    @property
    def output_collector(self) -> OutputCollector:
        return self._output

    async def __call__(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Execute the full pipeline."""
        try:
            await self._initialize(*args, **kwargs)
            await self._setup()
            self._execute()
        except (InputError, OutputError, KeyboardInterrupt, Exception) as e:
            self._err = e
        finally:
            return await self._finalize()

    # ==================
    # Phase 1: Initialize
    # ==================

    async def _initialize(self, *args, **kwargs):
        """Set up input data, storage, and job manager."""
        self._reset_for_new_run()

        if self.config.run_mode != RUN_MODE_RESUME:
            # Parse input
            queue, records = convert_input(*args, **kwargs)
            self.original_input_data = records
            self._input_queue = queue

            # Validate function signature
            validate_params(self.func, records[0])

            # Set up storage
            await self._setup_storage()

            # Generate IDs and adjust target
            if self.config.run_mode == RUN_MODE_NORMAL:
                self.config.project_id = str(uuid.uuid4())
                self.config.master_job_id = str(uuid.uuid4())
                if self.config.target_count == 0:
                    self.config.target_count = self._input_queue.qsize()
        else:
            self._input_queue = Queue()
            await self._setup_storage()

        # Create lifecycle manager
        self._lifecycle = JobLifecycle(self._storage, self.config)

        # Create job manager
        manager_cls = _JOB_MANAGERS.get(self.config.run_mode, JobManager)
        self._output = OutputCollector()
        self._job_manager = manager_cls(
            config=self.config,
            state=self.state,
            storage=self._storage,
            user_func=self.func,
            input_queue=self._input_queue,
            output_collector=self._output,
        )

    # ==================
    # Phase 2: Setup
    # ==================

    async def _setup(self):
        """Create project/job records and prepare queues."""
        if self.config.run_mode == RUN_MODE_NORMAL:
            await self._lifecycle.save_project()
            await self._lifecycle.start_master_job()

        await self._job_manager.setup_input_output_queue()

    # ==================
    # Phase 3: Execute
    # ==================

    def _execute(self):
        """Run the job orchestration."""
        if self.config.run_mode != RUN_MODE_RESUME:
            logger.info(
                f"[JOB START] Master Job ID: {self.config.master_job_id} | "
                f"Target: {self.config.target_count}"
            )
        self._job_manager.run_orchestration()

    # ==================
    # Phase 4: Finalize
    # ==================

    async def _finalize(self) -> List[Dict[str, Any]]:
        """Complete job, report results, clean up."""
        result = []

        if self._job_manager:
            result = self._output.get_output()

            if len(result) == 0 and self._err is None:
                self._err = OutputError("No records generated")

            # Update master job in DB
            if self._lifecycle:
                await self._lifecycle.complete_master_job(
                    self._job_manager.get_stats(),
                    has_error=self._err is not None,
                )

            # Report final status
            self._job_manager._reporter.report_final(
                self._job_manager.get_stats(), self.config.target_count
            )
            if self._job_manager.dead_queue_count > 0:
                self._job_manager._reporter.report_dead_queue(
                    self._job_manager.dead_queue_count,
                    self.config.retry_policy.dead_queue_threshold,
                )

        # Handle errors
        if self._err:
            if isinstance(self._err, (InputError, OutputError)):
                await self._close_storage()
                raise self._err
            else:
                err_msg = "KeyboardInterrupt" if isinstance(self._err, KeyboardInterrupt) else str(self._err)
                logger.error(f"Error occurred: {err_msg}")
                logger.info("[RESUME INFO] Job stopped unexpectedly. Resume with .resume()")

        # Save config for resume
        if self.config.run_mode != RUN_MODE_DRY_RUN and self._lifecycle:
            await self._lifecycle.save_request_config(
                self.func, self.state, self.original_input_data
            )

        await self._close_storage()
        return result

    # ==================
    # Storage
    # ==================

    async def _setup_storage(self):
        if self._storage is None:
            if self.config.storage == STORAGE_TYPE_LOCAL:
                self._storage = LocalStorage(LOCAL_STORAGE_URI)
            else:
                self._storage = InMemoryStorage()
            await self._storage.setup()

    async def _close_storage(self):
        if self._storage:
            await self._storage.close()
            self._storage = None

    def _reset_for_new_run(self):
        """Reset state for a new run (handles same-session reuse)."""
        self._err = None
        self._storage = None
        self._lifecycle = None
        self._job_manager = None
        self._output = OutputCollector()

    # ==================
    # Resume (class method)
    # ==================

    @staticmethod
    async def resume_from_storage(master_job_id: str, **overrides) -> "Factory":
        """Create a Factory configured for resume from a stored job.

        Loads function, config, state, and input data from storage.
        """
        factory = Factory(FactoryConfig(storage=STORAGE_TYPE_LOCAL))
        factory.config.master_job_id = master_job_id

        await factory._setup_storage()

        # Load master job
        master_job = await factory._storage.get_master_job(master_job_id)
        if not master_job:
            await factory._close_storage()
            raise InputError(f"Master job not found: {master_job_id}")

        # Load config data
        config_data = await factory._storage.get_request_config(
            master_job.request_config_ref
        )

        # Reconstruct state
        factory.state = MutableSharedState(initial_data=config_data.get("state"))

        # Reconstruct config
        saved_config = config_data.get("config")
        if saved_config:
            factory.config = FactoryConfig.from_dict(saved_config)

        # Reconstruct function
        func_hex = config_data.get("func")
        if func_hex:
            factory.func = cloudpickle.loads(bytes.fromhex(func_hex))

        if not factory.func:
            await factory._close_storage()
            raise NoResumeSupportError()

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(factory.config, key) and value is not None:
                setattr(factory.config, key, value)

        # Set up prev_job for JobManagerRerun
        prev_master = {
            "completed_count": master_job.completed_record_count,
            "failed_count": master_job.failed_record_count,
            "filtered_count": master_job.filtered_record_count,
            "duplicate_count": master_job.duplicate_record_count,
            "total_count": (
                master_job.completed_record_count
                + master_job.failed_record_count
                + master_job.filtered_record_count
                + master_job.duplicate_record_count
            ),
        }
        factory.config.prev_job = {
            "master_job": prev_master,
            "input_data": config_data.get("input_data", []),
        }
        factory.original_input_data = [
            dict(item) for item in config_data.get("input_data", [])
        ]

        factory.config.run_mode = RUN_MODE_RESUME
        await factory._close_storage()

        return factory
