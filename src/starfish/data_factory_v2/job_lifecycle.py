"""Job lifecycle management — project/job creation, status updates, completion.

Extracted from the Factory God Object to provide clean separation.
Uses storage capabilities to decide whether to persist.
"""
import datetime
from typing import Any, Dict, Optional

import cloudpickle

from starfish.common.logger import get_logger
from starfish.data_factory_v2.config import FactoryConfig
from starfish.data_factory_v2.constants import (
    LOCAL_STORAGE_URI,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.storage.models import GenerationMasterJob, Project

logger = get_logger(__name__)


class JobLifecycle:
    """Manages project and master job metadata in storage."""

    def __init__(self, storage: Storage, config: FactoryConfig):
        self.storage = storage
        self.config = config
        self.config_ref: Optional[str] = None

    def _has_capability(self, cap: str) -> bool:
        return hasattr(self.storage, 'capabilities') and cap in self.storage.capabilities

    async def save_project(self) -> None:
        if not self._has_capability("QUERY_METADATA"):
            return

        project = Project(
            project_id=self.config.project_id,
            name=self.config.project_name or f"Project {self.config.project_id[:8]}",
            description=f"Data factory project",
        )
        await self.storage.save_project(project)

    async def start_master_job(self) -> None:
        if not self._has_capability("QUERY_METADATA"):
            return

        self.config_ref = self.storage.generate_request_config_path(self.config.master_job_id)

        master_job = GenerationMasterJob(
            master_job_id=self.config.master_job_id,
            project_id=self.config.project_id,
            name=f"Job {self.config.master_job_id[:8]}",
            status="running",
            request_config_ref=self.config_ref,
            output_schema={"type": "object"},
            storage_uri=LOCAL_STORAGE_URI if self.config.storage == STORAGE_TYPE_LOCAL else "memory://",
            target_record_count=self.config.target_count,
        )
        await self.storage.log_master_job_start(master_job)

    async def complete_master_job(self, counts: Dict[str, int], has_error: bool) -> None:
        if not self._has_capability("QUERY_METADATA"):
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        status = STATUS_FAILED if has_error else STATUS_COMPLETED
        summary = {
            STATUS_COMPLETED: counts.get("completed", 0),
            STATUS_FILTERED: counts.get("filtered", 0),
            STATUS_DUPLICATE: counts.get("duplicate", 0),
            STATUS_FAILED: counts.get("failed", 0),
        }
        await self.storage.log_master_job_end(
            self.config.master_job_id, status, summary, now, now
        )

    async def save_request_config(
        self, func, state, original_input_data
    ) -> None:
        """Save function + config for resume support."""
        if not self._has_capability("STORE_LARGE_CONFIG"):
            return
        if self.config_ref is None:
            self.config_ref = self.storage.generate_request_config_path(self.config.master_job_id)

        config_data = {
            "generator": "data_factory_v2",
            "state": state.to_dict() if state else {},
            "input_data": original_input_data,
        }

        # Serialize function
        try:
            config_data["func"] = cloudpickle.dumps(func).hex()
        except Exception as e:
            logger.warning(f"Cannot serialize function for resume: {e}")
            config_data["func"] = None

        # Serialize config
        try:
            config_data["config"] = self.config.to_dict()
        except Exception as e:
            logger.warning(f"Cannot serialize config for resume: {e}")
            config_data["config"] = None

        await self.storage.save_request_config(self.config_ref, config_data)
