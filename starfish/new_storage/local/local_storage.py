# synthetic_data_gen/storage/local/storage.py
import datetime
import logging
import os
from typing import Dict, Any, Optional, List, Set

from starfish.new_storage.base import Storage
from starfish.new_storage.models import ( # Import Pydantic models
    Project,
    GenerationMasterJob,
    GenerationJob,
    Record,
    StatusRecord
)
from starfish.new_storage.local.metadata_handler import SQLiteMetadataHandler
from starfish.new_storage.local.data_handler import FileSystemDataHandler
from starfish.new_storage.local.utils import parse_uri_to_path


logger = logging.getLogger(__name__)

class LocalStorage(Storage):
    """
    Hybrid Local Storage Backend using SQLite for metadata and local JSON files
    for data artifacts and large configurations. Facade over internal handlers.
    """
    capabilities: Set[str] = {"QUERY_METADATA", "FILTER_STATUS", "STORE_LARGE_CONFIG"}

    def __init__(self, storage_uri: str, data_storage_uri_override: Optional[str] = None):
        logger.info(f"Initializing LocalStorage with URI: {storage_uri}")
        self.base_path = parse_uri_to_path(storage_uri)
        self.metadata_db_path = os.path.join(self.base_path, "metadata.db") # Consistent name

        if data_storage_uri_override:
            if not data_storage_uri_override.startswith("file://"):
                logger.error("LocalStorage data override must use file:// URI")
                raise ValueError("LocalStorage data override must use file:// URI")
            self.data_base_path = parse_uri_to_path(data_storage_uri_override)
            logger.info(f"Using data override path: {self.data_base_path}")
        else:
            self.data_base_path = self.base_path
            logger.info(f"Using default data path within base: {self.data_base_path}")

        # Instantiate internal handlers
        self._metadata_handler = SQLiteMetadataHandler(self.metadata_db_path)
        self._data_handler = FileSystemDataHandler(self.data_base_path)
        self._is_setup = False

    async def setup(self) -> None:
        """Initializes both metadata DB schema and base file directories."""
        if self._is_setup: return
        logger.info("Setting up LocalStorage...")
        await self._metadata_handler.initialize_schema()
        await self._data_handler.ensure_base_dirs()
        self._is_setup = True
        logger.info("LocalStorage setup complete.")

    async def close(self) -> None:
        """Closes underlying connections/resources."""
        logger.info("Closing LocalStorage...")
        await self._metadata_handler.close()
        # FileSystemDataHandler might not need explicit close unless holding locks/handles
        self._is_setup = False

    # --- Delegate methods to internal handlers ---

    # Config Persistence
    async def save_request_config(self, master_job_id: str, config_data: Dict[str, Any]) -> str:
        return await self._data_handler.save_request_config_impl(master_job_id, config_data)

    async def get_request_config(self, config_ref: str) -> Dict[str, Any]:
        return await self._data_handler.get_request_config_impl(config_ref)

    # Data Artifact Persistence
    async def save_record_data(self, record_uid: str, master_job_id: str, job_id: str, data: Dict[str, Any]) -> str:
        # Pass necessary IDs if data handler needs them for pathing (though current uses record_uid)
        return await self._data_handler.save_record_data_impl(record_uid, data)

    async def get_record_data(self, output_ref: str) -> Dict[str, Any]:
        return await self._data_handler.get_record_data_impl(output_ref)

    # --- Metadata Methods ---
    async def save_project(self, project_data: Project) -> None:
        await self._metadata_handler.save_project_impl(project_data)

    async def get_project(self, project_id: str) -> Optional[Project]:
        return await self._metadata_handler.get_project_impl(project_id)

    async def list_projects(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Project]:
        return await self._metadata_handler.list_projects_impl(limit, offset)

    async def log_master_job_start(self, job_data: GenerationMasterJob) -> None:
        await self._metadata_handler.log_master_job_start_impl(job_data)

    async def log_master_job_end(self, master_job_id: str, final_status: str, summary: Optional[Dict[str, Any]], end_time: datetime.datetime, update_time: datetime.datetime) -> None:
        await self._metadata_handler.log_master_job_end_impl(master_job_id, final_status, summary, end_time, update_time)

    async def update_master_job_status(self, master_job_id: str, status: str, update_time: datetime.datetime) -> None:
         await self._metadata_handler.update_master_job_status_impl(master_job_id, status, update_time)

    async def get_master_job(self, master_job_id: str) -> Optional[GenerationMasterJob]:
        return await self._metadata_handler.get_master_job_impl(master_job_id)

    async def list_master_jobs(self, project_id: Optional[str] = None, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[GenerationMasterJob]:
         return await self._metadata_handler.list_master_jobs_impl(project_id, status_filter, limit, offset)

    async def log_execution_job_start(self, job_data: GenerationJob) -> None:
        await self._metadata_handler.log_execution_job_start_impl(job_data)

    async def log_execution_job_end(self, job_id: str, final_status: str, counts: Dict[str, int], end_time: datetime.datetime, update_time: datetime.datetime, error_message: Optional[str] = None) -> None:
        await self._metadata_handler.log_execution_job_end_impl(job_id, final_status, counts, end_time, update_time, error_message)

    async def get_execution_job(self, job_id: str) -> Optional[GenerationJob]:
        return await self._metadata_handler.get_execution_job_impl(job_id)

    async def list_execution_jobs(self, master_job_id: str, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[GenerationJob]:
        return await self._metadata_handler.list_execution_jobs_impl(master_job_id, status_filter, limit, offset)

    async def log_record_metadata(self, record_data: Record) -> None:
        await self._metadata_handler.log_record_metadata_impl(record_data)

    async def get_record_metadata(self, record_uid: str) -> Optional[Record]:
        return await self._metadata_handler.get_record_metadata_impl(record_uid)

    async def get_records_for_master_job( self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Record]:
        return await self._metadata_handler.get_records_for_master_job_impl(master_job_id, status_filter, limit, offset)

    async def count_records_for_master_job(self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None) -> Dict[str, int]:
         return await self._metadata_handler.count_records_for_master_job_impl(master_job_id, status_filter)