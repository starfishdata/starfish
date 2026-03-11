"""Complete in-memory storage implementation for v2.

The v1 InMemoryStorage is missing abstract methods. This provides a
working no-op implementation.
"""
import datetime
from typing import Any, Dict, List, Optional, Set

from starfish.data_factory.storage.base import Storage
from starfish.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
    StatusRecord,
)


class InMemoryStorageV2(Storage):
    """No-op in-memory storage that satisfies the full Storage ABC."""

    capabilities: Set[str] = set()  # No capabilities — skip all persistence

    def __init__(self):
        self._is_setup = False

    async def setup(self) -> None:
        self._is_setup = True

    async def close(self) -> None:
        self._is_setup = False

    # Config
    async def save_request_config(self, config_ref: str, config_data: Dict[str, Any]):
        pass

    def generate_request_config_path(self, master_job_id: str) -> str:
        return ""

    async def get_request_config(self, config_ref: str) -> Dict[str, Any]:
        return {}

    # Data
    async def save_record_data(self, record_uid: str, master_job_id: str, job_id: str, data: Dict[str, Any]) -> str:
        return ""

    async def get_record_data(self, output_ref: str) -> Dict[str, Any]:
        return {}

    # Project
    async def save_project(self, project_data: Project) -> None:
        pass

    async def get_project(self, project_id: str) -> Optional[Project]:
        return None

    async def list_projects(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Project]:
        return []

    # Master Job
    async def log_master_job_start(self, job_data: GenerationMasterJob) -> None:
        pass

    async def log_master_job_end(self, master_job_id: str, final_status: str, summary: Optional[Dict[str, Any]], end_time: datetime.datetime, update_time: datetime.datetime) -> None:
        pass

    async def update_master_job_status(self, master_job_id: str, status: str, update_time: datetime.datetime) -> None:
        pass

    async def get_master_job(self, master_job_id: str) -> Optional[GenerationMasterJob]:
        return None

    async def list_master_jobs(self, project_id: Optional[str] = None, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[GenerationMasterJob]:
        return []

    # Execution Job
    async def log_execution_job_start(self, job_data: GenerationJob) -> None:
        pass

    async def log_execution_job_end(self, job_id: str, final_status: str, counts: Dict[str, int], end_time: datetime.datetime, update_time: datetime.datetime, error_message: Optional[str] = None) -> None:
        pass

    async def get_execution_job(self, job_id: str) -> Optional[GenerationJob]:
        return None

    async def list_execution_jobs(self, master_job_id: str, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[GenerationJob]:
        return []

    # Record
    async def log_record_metadata(self, record_data: Record) -> None:
        pass

    async def get_record_metadata(self, record_uid: str) -> Optional[Record]:
        return None

    async def get_records_for_master_job(self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Record]:
        return []

    async def count_records_for_master_job(self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None) -> Dict[str, int]:
        return {}

    async def list_record_metadata(self, master_job_uuid: str, job_uuid: str) -> List[Record]:
        return []

    async def list_execution_jobs_by_master_id_and_config_hash(self, master_job_id: str, config_hash: str, job_status: str) -> List[GenerationJob]:
        return []
