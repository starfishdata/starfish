from pydantic import BaseModel, Field, validator
from typing import Literal, Dict, Any, List, Optional, Union, Set
from datetime import datetime
import uuid
import hashlib
import json
from enum import Enum
from pydantic import ConfigDict

# ==================================================================================
# Core Data Models
# ==================================================================================

class Project(BaseModel):
    """Top-level container for related jobs."""
    project_id: str = Field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = Field(None)
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = Field(None)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class JobMetadata(BaseModel):
    """Metadata for tracking job information."""
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    project_id: str
    job_type: str = Field(..., description="Type of job: generation, evaluation, improvement, etc.")
    status: str = Field(default="pending", description="Job status: pending, running, completed, failed, etc.")
    parent_job_id: Optional[str] = Field(None, description="ID of parent job if this is a child job")
    pipeline_name: Optional[str] = Field(None, description="Name of the pipeline used")
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    step_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "job_123",
                "project_id": "proj_123",
                "job_type": "generation",
                "status": "completed",
                "pipeline_name": "data_generation",
                "parameters": {},
                "step_states": {
                    "step1": {"status": "completed", "start_time": "2023-01-01T00:00:00"},
                    "step2": {"status": "completed", "start_time": "2023-01-01T00:01:00"}
                },
                "created_at": "2023-01-01T00:00:00",
                "completed_at": "2023-01-01T00:10:00"
            }
        }
    )

class Record(BaseModel):
    """Data record with metadata."""
    record_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    job_id: str
    record_type: str
    content_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def compute_hash(self) -> str:
        """Compute hash of record data for deduplication."""
        # Create a copy with only data fields, not metadata
        data_only = {k: v for k, v in self.data.items()}
        serialized = json.dumps(data_only, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.content_hash is None:
            self.content_hash = self.compute_hash()

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class AssociationType(str, Enum):
    """Types of record associations."""
    EVALUATION = "evaluation"
    DUPLICATE = "duplicate"
    PARENT_CHILD = "parent_child"
    ITERATION = "iteration"
    SIMILAR = "similar"
    CUSTOM = "custom"

class RecordAssociation(BaseModel):
    """Association between records."""
    association_id: str = Field(default_factory=lambda: f"assoc_{uuid.uuid4().hex[:8]}")
    source_record_id: str
    target_record_id: str
    association_type: str
    job_id: str
    scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# ==================================================================================
# Registry Models (For Type and Association schemas)
# ==================================================================================

class RecordSchema(BaseModel):
    """Schema definition for a record type."""
    name: str
    version: int = 1
    schema_definition: Dict[str, Any]
    description: Optional[str] = None

class AssociationSchema(BaseModel):
    """Schema definition for an association type."""
    name: str
    version: int = 1
    schema_definition: Dict[str, Any]
    description: Optional[str] = None

# ==================================================================================
# Storage Capability Model
# ==================================================================================

class StorageCapabilities(BaseModel):
    """Define what a storage backend can do."""
    supports_queries: bool = False
    supports_projects: bool = True
    supports_associations: bool = False
    supports_paging: bool = False
    max_batch_size: Optional[int] = None
    query_operators: List[str] = Field(default_factory=list)

# ==================================================================================
# Storage Configuration Models
# ==================================================================================

class BaseStorageConfig(BaseModel):
    """
    Base configuration for all storage types.
    All storage implementations should include these fields.
    """
    type: str = Field(..., description="Storage type identifier")
    
    class Config:
        extra = 'forbid'

class FileSystemStorageConfig(BaseStorageConfig):
    """Configuration model for FileSystemStorage."""
    type: Literal["filesystem"]
    base_path: str = Field(
        default="data_results",
        description="Directory where files will be stored"
    )
    data_format: Literal["jsonl"] = Field(
        default="jsonl", 
        description="Format to store the generated data in (only jsonl supported currently)"
    )
    # Additional fields for project-based storage
    project_id: Optional[str] = Field(
        None,
        description="Project ID for organizing related jobs. If not provided, a new project ID will be generated."
    )
    project_name: Optional[str] = Field(
        None,
        description="Name of the project for new projects. Required when creating a new project."
    )
    pipeline_name: Optional[str] = Field(
        None,
        description="Name of the pipeline being used"
    )

class PrefixedFileStorageConfig(FileSystemStorageConfig):
    """Configuration model for PrefixedFileStorage."""
    type: Literal["prefixed_filesystem"]
    prefix: str = Field(default="PREFIX_", description="String to prepend to all filenames")
    suffix: str = Field(default="_SUFFIX", description="String to append to all filenames before extension")

class DatabaseStorageConfig(BaseStorageConfig):
    """Configuration model for database storage (placeholder for future implementation)."""
    type: Literal["database"]
    connection_string: str = Field(..., description="Database connection string")
    table_prefix: Optional[str] = Field(None, description="Prefix for all tables")

class S3StorageConfig(BaseStorageConfig):
    """Configuration model for S3 storage (placeholder for future implementation)."""
    type: Literal["s3"]
    bucket: str = Field(..., description="S3 bucket name")
    prefix: str = Field(default="data/", description="Key prefix for all objects")
    region: Optional[str] = Field(None, description="AWS region")
    create_project_prefix: bool = Field(
        default=True,
        description="Whether to create a prefix for each project"
    )
    create_job_prefix: bool = Field(
        default=True,
        description="Whether to create a prefix for each job"
    )
