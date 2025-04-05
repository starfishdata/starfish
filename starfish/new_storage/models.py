import datetime
import json
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, computed_field, field_validator
import uuid

# --- Enums for Status Fields ---

StatusMasterJob = Literal[
    'pending', 'running',  'completed',
    'failed', 'completed_with_errors', 'cancelled'
]
StatusExecutionJob = Literal[
    'pending', 'running', 'completed', 'failed', 'cancelled'
]
StatusRecord = Literal[
    'pending', 'running', 'completed', 'duplicate', 'filtered', 'failed',  'cancelled'
]

# Helper functions for default timestamps
def utc_now() -> datetime.datetime:
    """Return current UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)

# --- Core Models ---

class Project(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique project identifier.")
    name: str = Field(..., description="User-friendly project name.")
    description: Optional[str] = Field(None, description="Optional description.")
    created_when: datetime.datetime = Field(default_factory=utc_now)
    updated_when: datetime.datetime = Field(default_factory=utc_now)

    class Config:
        from_attributes = True 

class GenerationMasterJob(BaseModel):
    master_job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job identifier.")
    project_id: str = Field(..., description="FK to Projects. Groups jobs.")
    name: Optional[str] = Field(None, description="Optional user-friendly name.")
    status: StatusMasterJob = Field(default='pending', description="Overall status of the job request.")
    request_config_ref: str = Field(..., description="Reference (e.g., file path, S3 URI) to the external request config JSON.")
    output_schema: Dict[str, Any] = Field(..., description="JSON definition of the expected primary data structure.") # Store as dict, serialize to JSON str for DB
    storage_uri: str = Field(..., description="Primary storage location config.")
    metadata_storage_uri_override: Optional[str] = Field(None, description="Advanced config override for metadata.")
    data_storage_uri_override: Optional[str] = Field(None, description="Advanced config override for data.")
    target_record_count: int = Field(..., description="Number of unique, valid records requested.")
    completed_record_count: int = Field(default=0, description="Aggregate count of 'completed' records.")
    filtered_record_count: int = Field(default=0, description="Aggregate count of 'filtered' records.")
    duplicate_record_count: int = Field(default=0, description="Aggregate count of 'duplicate' records.")
    failed_record_count: int = Field(default=0, description="Aggregate count of 'failed' records.")
    creation_time: datetime.datetime = Field(default_factory=utc_now, description="Job submission time.")
    start_time: Optional[datetime.datetime] = Field(None, description="Time the first execution work began.")
    end_time: Optional[datetime.datetime] = Field(None, description="Time the job reached a terminal state.")
    last_update_time: datetime.datetime = Field(default_factory=utc_now, description="Last modification time.")

    @field_validator('output_schema', mode="before")
    def _parse_json_string(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string provided")
        return value

    class Config:
        from_attributes = True 


class GenerationJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique execution identifier.")
    master_job_id: str = Field(..., description="FK to MasterJobs.")
    status: StatusExecutionJob = Field(default='pending', description="Status of this specific execution run.")
    run_config: Optional[Dict[str, Any]] = Field(None, description="JSON of specific inputs/context for this run.") # Store as dict
    attempted_generations: int = Field(default=0, description="Generation cycles/input items processed in this run.")
    produced_outputs_count: int = Field(default=0, description="Raw data items returned by generator(s) in this run.")
    completed_record_count: int = Field(default=0, description="'completed' records from this run.")
    filtered_record_count: int = Field(default=0, description="'filtered' records from this run.")
    duplicate_record_count: int = Field(default=0, description="'duplicate' records from this run.")
    failed_record_count: int = Field(default=0, description="'failed' records from this run.")
    creation_time: datetime.datetime = Field(default_factory=utc_now)
    start_time: Optional[datetime.datetime] = Field(None, description="When this execution actually started.")
    end_time: Optional[datetime.datetime] = Field(None, description="When this execution finished.")
    last_update_time: datetime.datetime = Field(default_factory=utc_now)
    worker_id: Optional[str] = Field(None, description="Identifier of the worker (if applicable).")
    error_message: Optional[str] = Field(None, description="Error if the whole execution run failed.")

    @field_validator('run_config', mode="before")
    def _parse_json_string(cls, value):
        # Same validator as above if stored as JSON string in DB
        if isinstance(value, str):
             try:
                 return json.loads(value)
             except json.JSONDecodeError:
                 raise ValueError("Invalid JSON string provided for run_config")
        return value

    # Helper method to calculate duration if needed
    def get_duration_seconds(self) -> Optional[float]:
        """Calculate the duration in seconds between start_time and end_time."""
        if self.start_time and self.end_time:
            start = self.start_time.replace(tzinfo=None) if self.start_time.tzinfo else self.start_time
            end = self.end_time.replace(tzinfo=None) if self.end_time.tzinfo else self.end_time
            return (end - start).total_seconds()
        return None

    class Config:
        from_attributes = True 


class Record(BaseModel):
    record_uid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique artifact ID.")
    job_id: str = Field(..., description="FK to GenerationJob.")
    master_job_id: str = Field(..., description="Denormalized FK to GenerationMasterJob.")
    status: StatusRecord = Field(default='pending', description="Final determined status of this artifact.")
    output_ref: Optional[str] = Field(None, description="Reference (e.g., file path, S3 URI) to the external data JSON.")
    start_time: datetime.datetime = Field(default_factory=utc_now, description="Time generator function produced the data.")
    end_time: datetime.datetime = Field(default_factory=utc_now, description="Time final status was assigned.")
    last_update_time: datetime.datetime = Field(default_factory=utc_now)
    error_message: Optional[str] = Field(None, description="Specific error related to this record.")

    class Config:
        from_attributes = True 


### Request configs: {storage_uri}/configs/{master_job_id}.request.json
### Record Data: {storage_uri}/data/{record_uid[:2]}/{record_uid[2:4]}/{record_uid}.json


