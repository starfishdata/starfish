# synthetic_data_gen/core/interfaces/storage.py
import datetime
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

# Import Pydantic models from where they are defined
# Assuming they are in synthetic_data_gen/models.py
from starfish.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
    StatusRecord,
)


class Storage(ABC):
    """Abstract Base Class for persistent storage backend implementations.
    Defines the contract for saving and retrieving job/record metadata and data artifacts.
    """

    @abstractmethod
    async def setup(self) -> None:
        """Initialize the backend (connect, create tables/dirs, run migrations)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (close connections)."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> Set[str]:
        """Return supported capability flags."""
        pass

    # --- Configuration Persistence ---
    @abstractmethod
    async def save_request_config(self, config_ref: str, config_data: Dict[str, Any]):
        """Save request config"""
        pass

    @abstractmethod
    def generate_request_config_path(self, master_job_id: str) -> str:
        """geenrate request config path, return reference."""
        pass

    @abstractmethod
    async def get_request_config(self, config_ref: str) -> Dict[str, Any]:
        """Retrieve request config from reference."""
        pass

    # --- Data Artifact Persistence ---
    @abstractmethod
    async def save_record_data(self, record_uid: str, master_job_id: str, job_id: str, data: Dict[str, Any]) -> str:
        """Save record data payload, return reference (output_ref)."""
        pass

    @abstractmethod
    async def get_record_data(self, output_ref: str) -> Dict[str, Any]:
        """Retrieve record data payload from reference."""
        pass

    # --- Metadata Logging & Retrieval ---
    # Project methods (Optional but good practice)
    @abstractmethod
    async def save_project(self, project_data: Project) -> None:
        """Save or update project details."""
        pass

    @abstractmethod
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve project details."""
        pass

    @abstractmethod
    async def list_projects(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Project]:
        """List available projects."""
        pass

    @abstractmethod
    async def delete_project(self, project_id: str) -> None:
        """Delete a project."""
        pass

    # Master Job methods
    @abstractmethod
    async def log_master_job_start(self, job_data: GenerationMasterJob) -> None:
        """Log the initial state of a master job."""
        pass

    @abstractmethod
    async def log_master_job_end(
        self, master_job_id: str, final_status: str, summary: Optional[Dict[str, Any]], end_time: datetime.datetime, update_time: datetime.datetime
    ) -> None:
        """Log the final status and summary of a master job."""
        pass

    @abstractmethod
    async def update_master_job_status(self, master_job_id: str, status: str, update_time: datetime.datetime) -> None:
        """Update the status of a master job (for intermediate states)."""
        pass

    @abstractmethod
    async def get_master_job(self, master_job_id: str) -> Optional[GenerationMasterJob]:
        """Retrieve master job details."""
        pass

    @abstractmethod
    async def list_master_jobs(
        self, project_id: Optional[str] = None, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[GenerationMasterJob]:
        """List master jobs, optionally filtering by project and status."""
        pass

    # Execution Job methods
    @abstractmethod
    async def log_execution_job_start(self, job_data: GenerationJob) -> None:
        """Log the initial state of an execution job."""
        pass

    @abstractmethod
    async def log_execution_job_end(
        self,
        job_id: str,
        final_status: str,
        counts: Dict[str, int],
        end_time: datetime.datetime,
        update_time: datetime.datetime,
        error_message: Optional[str] = None,
    ) -> None:
        """Log the final status and outcome counts of an execution job."""
        pass

    @abstractmethod
    async def get_execution_job(self, job_id: str) -> Optional[GenerationJob]:
        """Retrieve execution job details."""
        pass

    @abstractmethod
    async def list_execution_jobs(
        self, master_job_id: str, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[GenerationJob]:
        """List execution jobs for a given master job."""
        pass

    # Record Metadata methods
    @abstractmethod
    async def log_record_metadata(self, record_data: Record) -> None:
        """Log the metadata for a single generated record artifact."""
        pass

    @abstractmethod
    async def get_record_metadata(self, record_uid: str) -> Optional[Record]:
        """Retrieve a specific record's metadata."""
        pass

    @abstractmethod
    async def get_records_for_master_job(
        self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Record]:
        """Retrieve metadata for records belonging to a master job."""
        pass

    @abstractmethod
    async def count_records_for_master_job(self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None) -> Dict[str, int]:
        """Efficiently get counts of records grouped by status for a master job."""
        pass

    @abstractmethod
    async def list_record_metadata(self, master_job_uuid: str, job_uuid: str) -> List[Record]:
        """Retrieve metadata for records belonging to a master job."""
        pass

    @abstractmethod
    async def list_execution_jobs_by_master_id_and_config_hash(self, master_job_id: str, config_hash: str, job_status: str) -> Optional[GenerationJob]:
        """Retrieve execution job details by master job id and config hash."""
        pass

    @abstractmethod
    async def save_dataset(self, project_id: str, dataset_name: str, dataset_data: Dict[str, Any]) -> str:
        """Save a dataset."""
        pass

    @abstractmethod
    async def get_dataset(self, project_id: str, dataset_name: str) -> Dict[str, Any]:
        """Get a dataset."""
        pass

    @abstractmethod
    async def list_datasets(self, project_id: str) -> List[Dict[str, Any]]:
        """List datasets for a project."""
        pass


from .registry import Registry

# Create a storage-specific registry
storage_registry = Registry[Storage](Storage)

# Export for convenient access
register_storage = storage_registry.register
create_storage = storage_registry.create
get_available_storage_types = storage_registry.get_available_types
get_all_storage_input_models = storage_registry.get_all_input_models

# For backward compatibility
BaseStorage = Storage
