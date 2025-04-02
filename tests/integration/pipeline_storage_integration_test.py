import unittest
import pytest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock
from starfish.core.workflow.pipeline.manager import Pipeline
from starfish.core.workflow.step import StepRegistry, transactional_storage
from starfish.core.storage.base import create_storage
from pydantic import BaseModel, Field


# Define test models and steps for our test pipeline
class TestContextModel(BaseModel):
    """Test context model."""
    input_text: str = Field(..., description="Input text to process")
    output_path: str = Field(..., description="Path to output results")
    num_results: int = Field(3, description="Number of results to generate")


@StepRegistry.register("test_step1", input_model=None)
@transactional_storage(artifact_keys=["results"], record_type="step1_data")
async def test_step1(config, state):
    """Generate test data."""
    # Get parameters from context
    input_text = state["context"]["input_text"]
    num_results = state["context"]["num_results"]
    
    # Generate results
    results = []
    for i in range(num_results):
        results.append({
            "id": f"result_{i}",
            "text": f"{input_text} - {i}" 
        })
    
    # Store results in artifacts
    if "artifacts" not in state:
        state["artifacts"] = {}
    if "test_step1" not in state["artifacts"]:
        state["artifacts"]["test_step1"] = {}
    state["artifacts"]["test_step1"]["results"] = results
    
    # Set step status
    if "state" not in state:
        state["state"] = {}
    if "test_step1" not in state["state"]:
        state["state"]["test_step1"] = {}
    state["state"]["test_step1"]["status"] = "success"
    state["state"]["test_step1"]["count"] = len(results)
    
    return state


@StepRegistry.register("test_step2", input_model=None)
@transactional_storage(artifact_keys=["processed_results"], record_type="step2_data")
async def test_step2(config, state):
    """Process test data."""
    # Check for results from step1
    if "artifacts" not in state or "test_step1" not in state["artifacts"] or "results" not in state["artifacts"]["test_step1"]:
        raise ValueError("No results from step1")
    
    # Get results
    results = state["artifacts"]["test_step1"]["results"]
    
    # Process results
    processed_results = []
    for result in results:
        processed_results.append({
            "id": result["id"],
            "text": result["text"].upper(),
            "length": len(result["text"])
        })
    
    # Store processed results in artifacts
    if "artifacts" not in state:
        state["artifacts"] = {}
    if "test_step2" not in state["artifacts"]:
        state["artifacts"]["test_step2"] = {}
    state["artifacts"]["test_step2"]["processed_results"] = processed_results
    
    # Set step status
    if "state" not in state:
        state["state"] = {}
    if "test_step2" not in state["state"]:
        state["state"]["test_step2"] = {}
    state["state"]["test_step2"]["status"] = "success"
    state["state"]["test_step2"]["count"] = len(processed_results)
    
    return state


class TestPipelineWithStorage(unittest.TestCase):
    """Integration test for pipeline with transactional storage."""
    
    def setUp(self):
        """Set up a test directory for storage."""
        self.test_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.test_dir, "storage")
        os.makedirs(self.storage_path, exist_ok=True)
    
    def tearDown(self):
        """Clean up the test directory."""
        shutil.rmtree(self.test_dir)
    
    @pytest.mark.asyncio
    async def test_pipeline_with_storage(self):
        """Test a pipeline with transactional storage."""
        # Create a test pipeline
        pipeline = Pipeline(
            name="test_pipeline",
            description="Pipeline for testing transactional storage",
            context_model=TestContextModel,
            steps=[
                {"name": "test_step1", "config": {"type": "test"}},
                {"name": "test_step2", "config": {"type": "test"}}
            ],
            storage_config={
                "type": "filesystem",
                "base_path": self.storage_path,
                "data_format": "jsonl",
                "project_name": "Test Project"
            }
        )
        
        # Run the pipeline
        result = await pipeline.run_async({
            "input_text": "Hello, world",
            "output_path": os.path.join(self.test_dir, "output.json"),
            "num_results": 5
        })
        
        # Check pipeline result
        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")
        
        # Check for step2 artifacts in result
        self.assertIn("data", result)
        self.assertIn("processed_results", result["data"])
        self.assertEqual(len(result["data"]["processed_results"]), 5)
        
        # Check storage files were created
        # 1. Check project directory exists
        projects_dir = os.listdir(self.storage_path)
        self.assertGreaterEqual(len(projects_dir), 1)
        
        # 2. Get the project directory
        project_dir = os.path.join(self.storage_path, projects_dir[0])
        
        # 3. Check for master job and two child jobs
        job_dirs = os.listdir(project_dir)
        self.assertGreaterEqual(len(job_dirs), 3)  # At least master + 2 steps
        
        # Find metadata files
        metadata_files = []
        record_files = []
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file == "metadata.json":
                    metadata_files.append(os.path.join(root, file))
                elif file.endswith(".jsonl"):
                    record_files.append(os.path.join(root, file))
        
        # Check for at least 3 metadata files (master + 2 steps)
        self.assertGreaterEqual(len(metadata_files), 3)
        
        # Check for at least 2 record files (1 per step)
        self.assertGreaterEqual(len(record_files), 2)
        
    @pytest.mark.asyncio
    async def test_pipeline_with_step_failure(self):
        """Test a pipeline with a failing step and transactional storage."""
        # Create a mock step that will fail
        @StepRegistry.register("failing_step", input_model=None)
        @transactional_storage(artifact_keys=["partial_results"], record_type="partial_data")
        async def failing_step(config, state):
            """A step that fails after producing partial results."""
            # Generate partial results
            partial_results = [{"id": "partial_1", "status": "started"}]
            
            # Store partial results in artifacts
            if "artifacts" not in state:
                state["artifacts"] = {}
            if "failing_step" not in state["artifacts"]:
                state["artifacts"]["failing_step"] = {}
            state["artifacts"]["failing_step"]["partial_results"] = partial_results
            
            # Set step status to in-progress
            if "state" not in state:
                state["state"] = {}
            if "failing_step" not in state["state"]:
                state["state"]["failing_step"] = {}
            state["state"]["failing_step"]["status"] = "in_progress"
            
            # Now fail
            raise ValueError("Simulated failure")
        
        # Create a test pipeline with the failing step
        pipeline = Pipeline(
            name="failure_pipeline",
            description="Pipeline for testing failure handling",
            context_model=TestContextModel,
            steps=[
                {"name": "test_step1", "config": {"type": "test"}},
                {"name": "failing_step", "config": {"type": "test"}},
                {"name": "test_step2", "config": {"type": "test"}}  # This won't run
            ],
            storage_config={
                "type": "filesystem",
                "base_path": self.storage_path,
                "data_format": "jsonl",
                "project_name": "Failure Test"
            }
        )
        
        # Run the pipeline and expect it to fail
        with self.assertRaises(ValueError):
            await pipeline.run_async({
                "input_text": "Hello, world",
                "output_path": os.path.join(self.test_dir, "output.json"),
                "num_results": 5
            })
        
        # Check storage files were created despite the failure
        # 1. Check project directory exists
        projects_dir = os.listdir(self.storage_path)
        self.assertGreaterEqual(len(projects_dir), 1)
        
        # 2. Get the last project directory (from the failure test)
        project_dirs = [os.path.join(self.storage_path, d) for d in projects_dir]
        project_dirs.sort(key=os.path.getmtime)
        project_dir = project_dirs[-1]
        
        # 3. Check for master job and successful steps
        job_dirs = os.listdir(project_dir)
        self.assertGreaterEqual(len(job_dirs), 2)  # At least master + test_step1
        
        # Find metadata files
        metadata_files = []
        record_files = []
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file == "metadata.json":
                    metadata_files.append(os.path.join(root, file))
                elif file.endswith(".jsonl"):
                    record_files.append(os.path.join(root, file))
        
        # Check that we have metadata files for the master job and steps
        self.assertGreaterEqual(len(metadata_files), 2)
        
        # Check that we have a record file for test_step1
        self.assertGreaterEqual(len(record_files), 1)
        
        # Check that the test_step2 wasn't executed (no records)
        step2_records = [f for f in record_files if "step2" in f]
        self.assertEqual(len(step2_records), 0)


if __name__ == "__main__":
    unittest.main() 