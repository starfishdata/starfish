import pytest
import asyncio
import os
import shutil
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from starfish.core.workflow.pipeline import Pipeline
from starfish.core.workflow.step import StepRegistry, step_handler
from starfish.core.workflow.pipeline import transactional_storage, PipelineStorageContext
from starfish.core.storage.filesystem import FileSystemStorage
from starfish.core.storage.models import Record, FileSystemStorageConfig

# ==================================================================================
# Test Pipeline Steps
# ==================================================================================

@StepRegistry.register("test_generate", input_model=None)
@transactional_storage(artifact_keys=["data"], record_type="test_data")
@step_handler()
async def test_generate_step(config: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate test data."""
    # Create some test data
    data = [
        {"id": 1, "name": "Test 1", "value": 100},
        {"id": 2, "name": "Test 2", "value": 200},
        {"id": 3, "name": "Test 3", "value": 300},
    ]
    
    # Store in artifacts
    if "artifacts" not in state:
        state["artifacts"] = {}
    if "test_generate" not in state["artifacts"]:
        state["artifacts"]["test_generate"] = {}
    state["artifacts"]["test_generate"]["data"] = data
    
    # Set status
    if "state" not in state:
        state["state"] = {}
    if "test_generate" not in state["state"]:
        state["state"]["test_generate"] = {}
    state["state"]["test_generate"]["status"] = "success"
    
    return state

@StepRegistry.register("test_process", input_model=None)
@transactional_storage(artifact_keys=["processed_data"], record_type="processed_data")
@step_handler(required_artifacts={"test_generate": ["data"]})
async def test_process_step(config: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Process test data."""
    # Get test data
    data = state["artifacts"]["test_generate"]["data"]
    
    # Process data (multiply values by 2)
    processed_data = [
        {**item, "value": item["value"] * 2}
        for item in data
    ]
    
    # Store in artifacts
    if "artifacts" not in state:
        state["artifacts"] = {}
    if "test_process" not in state["artifacts"]:
        state["artifacts"]["test_process"] = {}
    state["artifacts"]["test_process"]["processed_data"] = processed_data
    
    # Set status
    if "state" not in state:
        state["state"] = {}
    if "test_process" not in state["state"]:
        state["state"]["test_process"] = {}
    state["state"]["test_process"]["status"] = "success"
    
    return state

# ==================================================================================
# Test Context Model
# ==================================================================================

class TestPipelineContext(BaseModel):
    """Test pipeline context."""
    project_name: str = Field("Test Project")
    multiply_factor: int = Field(2)

# ==================================================================================
# Tests
# ==================================================================================

class TestPipelineStorage:
    """Tests for pipeline storage functionality."""
    
    TEST_DIR = "test_storage_results"
    
    @classmethod
    def setup_class(cls):
        """Set up test class by ensuring test directory exists."""
        # Remove test directory if it exists
        if os.path.exists(cls.TEST_DIR):
            shutil.rmtree(cls.TEST_DIR)
        
        # Create test directory
        os.makedirs(cls.TEST_DIR, exist_ok=True)
    
    @classmethod
    def teardown_class(cls):
        """Clean up test directory."""
        if os.path.exists(cls.TEST_DIR):
            shutil.rmtree(cls.TEST_DIR)
    
    @pytest.mark.asyncio
    async def test_pipeline_storage(self):
        """Test pipeline storage with transactional steps."""
        # Create pipeline with storage config
        pipeline = Pipeline(
            name="test_pipeline",
            description="Test pipeline with storage",
            context_model=TestPipelineContext,
            steps=[
                {"name": "test_generate", "config": {"type": "test"}},
                {"name": "test_process", "config": {"type": "test"}}
            ],
            storage_config={
                "type": "filesystem",
                "base_path": self.TEST_DIR,
                "data_format": "jsonl"
            }
        )
        
        # Run pipeline
        result = await pipeline.run_async({
            "project_name": "Storage Test Project"
        })
        
        # Check that pipeline executed successfully
        assert result["status"] == "success"
        
        # Check that storage files were created
        storage = FileSystemStorage(FileSystemStorageConfig(
            type="filesystem",
            base_path=self.TEST_DIR,
            data_format="jsonl"
        ))
        
        # Get project and job information from storage
        projects = storage.list_projects()
        assert len(projects) == 1
        
        project = projects[0]
        assert project.name == "Storage Test Project"
        
        # Check for master job
        jobs = storage.list_jobs(project_id=project.project_id)
        assert len(jobs) >= 1
        
        # Find master job
        master_job = None
        for job in jobs:
            if job.job_type == "pipeline_execution":
                master_job = job
                break
        
        assert master_job is not None
        
        # Check for step jobs
        step_jobs = [j for j in jobs if j.job_type.startswith("step_")]
        assert len(step_jobs) == 2
        
        # Check for test_generate step
        generate_job = next((j for j in step_jobs if j.job_type == "step_test_generate"), None)
        assert generate_job is not None
        
        # Check for test_process step
        process_job = next((j for j in step_jobs if j.job_type == "step_test_process"), None)
        assert process_job is not None
        
        # Check records were saved
        generate_records = storage.load_records(generate_job.job_id)
        assert len(generate_records) == 3
        
        process_records = storage.load_records(process_job.job_id)
        assert len(process_records) == 3
        
        # Verify processed data values
        for record in process_records:
            assert record.data["value"] == record.data["id"] * 100 * 2

    @pytest.mark.asyncio
    async def test_pipeline_storage_disabled(self):
        """Test pipeline with storage disabled."""
        # Create pipeline with storage disabled
        pipeline = Pipeline(
            name="test_pipeline_disabled",
            description="Test pipeline with storage disabled",
            context_model=TestPipelineContext,
            steps=[
                {"name": "test_generate", "config": {"type": "test"}},
                {"name": "test_process", "config": {"type": "test"}}
            ],
            storage_config={
                "type": "filesystem",
                "base_path": self.TEST_DIR,
                "data_format": "jsonl",
                "enabled": False
            }
        )
        
        # Run pipeline
        result = await pipeline.run_async({
            "project_name": "Disabled Storage Test"
        })
        
        # Check that pipeline executed successfully
        assert result["status"] == "success"
        
        # Check storage context
        storage = FileSystemStorage(FileSystemStorageConfig(
            type="filesystem",
            base_path=self.TEST_DIR,
            data_format="jsonl"
        ))
        
        # Get projects
        projects = [p for p in storage.list_projects() if p.name == "Disabled Storage Test"]
        assert len(projects) == 0

    @pytest.mark.asyncio
    async def test_pipeline_storage_override(self):
        """Test pipeline with storage configuration override."""
        # Create pipeline with storage config
        pipeline = Pipeline(
            name="test_pipeline_override",
            description="Test pipeline with storage override",
            context_model=TestPipelineContext,
            steps=[
                {"name": "test_generate", "config": {"type": "test"}},
                {"name": "test_process", "config": {"type": "test"}}
            ],
            storage_config={
                "type": "filesystem",
                "base_path": "wrong_directory",
                "data_format": "jsonl"
            }
        )
        
        # Run pipeline with overridden storage config
        result = await pipeline.run_async({
            "project_name": "Override Storage Test",
            "storage.base_path": self.TEST_DIR
        })
        
        # Check that pipeline executed successfully
        assert result["status"] == "success"
        
        # Check that storage files were created in the overridden directory
        storage = FileSystemStorage(FileSystemStorageConfig(
            type="filesystem",
            base_path=self.TEST_DIR,
            data_format="jsonl"
        ))
        
        # Get project and job information from storage
        projects = [p for p in storage.list_projects() if p.name == "Override Storage Test"]
        assert len(projects) == 1 