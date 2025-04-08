from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from starfish.common.logger import get_logger
from starfish.storage.models import (
    AssociationSchema,
    JobMetadata,
    Project,
    Record,
    RecordAssociation,
    RecordSchema,
    StorageCapabilities,
)

logger = get_logger(__name__)


class Storage(ABC):
    """Abstract base class for all storage implementations.

    This class defines the standard interface that all storage implementations must follow.
    It includes methods for working with projects, jobs, records, and associations.
    """

    capabilities: StorageCapabilities = StorageCapabilities()

    # ==================================================================================
    # Project Operations
    # ==================================================================================

    @abstractmethod
    def save_project(self, project: Project) -> Dict[str, Any]:
        """Save a project.

        Args:
            project: Project to save

        Returns:
            Dictionary with metadata about the saved project
        """
        pass

    @abstractmethod
    def load_project(self, project_id: str) -> Optional[Project]:
        """Load a project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project or None if not found
        """
        pass

    @abstractmethod
    def list_projects(self) -> List[Project]:
        """List all projects.

        Returns:
            List of all projects
        """
        pass

    @abstractmethod
    def update_project(self, project: Project) -> Dict[str, Any]:
        """Update an existing project.

        Args:
            project: Project with updated fields

        Returns:
            Dictionary with metadata about the updated project
        """
        pass

    # ==================================================================================
    # Job Operations
    # ==================================================================================

    @abstractmethod
    def save_job_metadata(self, metadata: JobMetadata) -> Dict[str, Any]:
        """Save job metadata.

        Args:
            metadata: Job metadata to save

        Returns:
            Dictionary with metadata about the saved job
        """
        pass

    @abstractmethod
    def load_job_metadata(self, job_id: str) -> Optional[JobMetadata]:
        """Load job metadata by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobMetadata or None if not found
        """
        pass

    @abstractmethod
    def list_jobs(self, project_id: Optional[str] = None, job_type: Optional[str] = None, parent_job_id: Optional[str] = None) -> List[JobMetadata]:
        """List jobs, optionally filtered by project, type, and parent.

        Args:
            project_id: Optional project ID to filter by
            job_type: Optional job type to filter by
            parent_job_id: Optional parent job ID to filter by

        Returns:
            List of matching jobs
        """
        pass

    @abstractmethod
    def update_job_metadata(self, metadata: JobMetadata) -> Dict[str, Any]:
        """Update job metadata.

        Args:
            metadata: JobMetadata with updated fields

        Returns:
            Dictionary with metadata about the updated job
        """
        pass

    # ==================================================================================
    # Record Operations
    # ==================================================================================

    @abstractmethod
    def save_records(self, records: List[Record], job_id: str) -> Dict[str, Any]:
        """Save records for a job.

        Args:
            records: List of records to save
            job_id: Job identifier

        Returns:
            Dictionary with metadata about the saved records
        """
        pass

    @abstractmethod
    def load_records(self, job_id: str) -> List[Record]:
        """Load all records for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of records
        """
        pass

    @abstractmethod
    def load_records_by_project(self, project_id: str, job_type: Optional[str] = None) -> List[Record]:
        """Load all records in a project, optionally filtered by job type.

        Args:
            project_id: Project identifier
            job_type: Optional job type to filter by

        Returns:
            List of records
        """
        pass

    @abstractmethod
    def load_record(self, record_id: str) -> Optional[Record]:
        """Load a single record by ID.

        Args:
            record_id: Record identifier

        Returns:
            Record or None if not found
        """
        pass

    # ==================================================================================
    # Association Operations
    # ==================================================================================

    @abstractmethod
    def save_associations(self, associations: List[RecordAssociation], job_id: str) -> Dict[str, Any]:
        """Save associations for a job.

        Args:
            associations: List of associations to save
            job_id: Job identifier

        Returns:
            Dictionary with metadata about the saved associations
        """
        pass

    @abstractmethod
    def load_associations(self, job_id: str) -> List[RecordAssociation]:
        """Load all associations for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of associations
        """
        pass

    @abstractmethod
    def find_associations(
        self, source_record_id: Optional[str] = None, target_record_id: Optional[str] = None, association_type: Optional[str] = None
    ) -> List[RecordAssociation]:
        """Find associations by source, target, or type.

        Args:
            source_record_id: Optional source record ID to filter by
            target_record_id: Optional target record ID to filter by
            association_type: Optional association type to filter by

        Returns:
            List of matching associations
        """
        pass


class RecordTypeRegistry:
    """Registry for record types and schemas."""

    _types: Dict[str, RecordSchema] = {}

    @classmethod
    def register(cls, name: str, schema: Dict, version: int = 1, description: Optional[str] = None) -> None:
        """Register a record type schema."""
        cls._types[name] = RecordSchema(name=name, version=version, schema=schema, description=description or f"Record type: {name}")

    @classmethod
    def get_schema(cls, name: str) -> Optional[RecordSchema]:
        """Get the schema for a record type."""
        return cls._types.get(name)

    @classmethod
    def validate(cls, record: Record) -> Tuple[bool, List[str]]:
        """Validate a record against its schema."""
        record_type = record.record_type
        if record_type not in cls._types:
            return False, [f"Unknown record type: {record_type}"]

        schema = cls._types[record_type].schema
        try:
            import jsonschema

            jsonschema.validate(record.data, schema)
            return True, []
        except Exception as e:
            return False, [str(e)]

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all registered record types."""
        return list(cls._types.keys())


class AssociationTypeRegistry:
    """Registry for association types and schemas."""

    _types: Dict[str, AssociationSchema] = {}

    @classmethod
    def register(cls, name: str, schema: Dict, version: int = 1, description: Optional[str] = None) -> None:
        """Register an association type."""
        cls._types[name] = AssociationSchema(name=name, version=version, schema=schema, description=description or f"Association type: {name}")

    @classmethod
    def get_schema(cls, name: str) -> Optional[AssociationSchema]:
        """Get the schema for an association type."""
        return cls._types.get(name)

    @classmethod
    def validate(cls, association: RecordAssociation) -> Tuple[bool, List[str]]:
        """Validate an association against its schema."""
        assoc_type = association.association_type
        if assoc_type not in cls._types:
            return False, [f"Unknown association type: {assoc_type}"]

        schema = cls._types[assoc_type].schema
        try:
            import jsonschema

            jsonschema.validate(association.scores, schema)
            return True, []
        except Exception as e:
            return False, [str(e)]

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all registered association types."""
        return list(cls._types.keys())


from starfish.core.component_registry import Registry

# Create a storage-specific registry
storage_registry = Registry[Storage](Storage)

# Export for convenient access
register_storage = storage_registry.register
create_storage = storage_registry.create
get_available_storage_types = storage_registry.get_available_types
get_all_storage_input_models = storage_registry.get_all_input_models

# For backward compatibility
BaseStorage = Storage
