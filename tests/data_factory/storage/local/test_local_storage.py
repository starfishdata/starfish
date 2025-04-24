import datetime
import hashlib
import json
import os
import shutil
import uuid

import pytest
import pytest_asyncio

from starfish.data_factory.storage.local.local_storage import LocalStorage
from starfish.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)

# Test database directory - use a folder specifically for tests
TEST_DB_DIR = "/tmp/starfish_test_storage"
TEST_DB_URI = f"file://{TEST_DB_DIR}"


@pytest_asyncio.fixture(scope="function")
async def storage():
    """Fixture to create and clean up a test storage for each test function."""
    # Ensure clean directory
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)
    os.makedirs(TEST_DB_DIR, exist_ok=True)

    # Create storage instance
    storage = LocalStorage(TEST_DB_URI)
    await storage.setup()

    yield storage

    # Cleanup
    await storage.close()
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)


@pytest_asyncio.fixture
async def test_project(storage):
    """Create a test project for use in tests."""
    project = Project(project_id=str(uuid.uuid4()), name="Test Project", description="Test project for unit tests")
    await storage.save_project(project)
    return project


@pytest_asyncio.fixture
async def test_master_job(storage, test_project):
    """Create a test master job for use in tests."""
    # First save a config
    config_data = {"test": "config", "generator": "test_generator"}

    master_job = GenerationMasterJob(
        master_job_id=str(uuid.uuid4()),
        project_id=test_project.project_id,
        name="Test Master Job",
        status="pending",
        request_config_ref="",  # Will be filled after saving config
        output_schema={"type": "object", "properties": {}},
        storage_uri=TEST_DB_URI,
        target_record_count=10,
    )

    # Save config and update reference
    config_ref = storage.generate_request_config_path(master_job.master_job_id)
    await storage.save_request_config(config_ref, config_data)
    master_job.request_config_ref = config_ref

    # Save the master job
    await storage.log_master_job_start(master_job)
    return master_job


# --- Test Basic Setup and Configuration ---


@pytest.mark.asyncio
async def test_storage_setup():
    """Test that storage setup creates necessary directories and database."""
    # Ensure clean directory
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)

    storage = LocalStorage(TEST_DB_URI)
    await storage.setup()

    # Check that dirs exist
    assert os.path.exists(os.path.join(TEST_DB_DIR, "configs"))
    assert os.path.exists(os.path.join(TEST_DB_DIR, "data"))
    assert os.path.exists(os.path.join(TEST_DB_DIR, "metadata.db"))

    await storage.close()
    shutil.rmtree(TEST_DB_DIR)


# --- Project Tests ---


@pytest.mark.asyncio
async def test_save_and_get_project(storage):
    """Test saving and retrieving a project."""
    project_id = str(uuid.uuid4())
    project = Project(project_id=project_id, name="Test Project", description="Test Description")

    # Save project
    await storage.save_project(project)

    # Retrieve project
    retrieved = await storage.get_project(project_id)

    assert retrieved is not None
    assert retrieved.project_id == project_id
    assert retrieved.name == "Test Project"
    assert retrieved.description == "Test Description"


@pytest.mark.asyncio
async def test_list_projects(storage):
    """Test listing projects."""
    # Create multiple projects
    projects = []
    for i in range(5):
        project = Project(project_id=str(uuid.uuid4()), name=f"Test Project {i}", description=f"Description {i}")
        await storage.save_project(project)
        projects.append(project)

    # List all projects
    retrieved = await storage.list_projects()

    assert len(retrieved) == 5

    # Test limit
    limited = await storage.list_projects(limit=2)
    assert len(limited) == 2

    # Test offset
    offset = await storage.list_projects(offset=2)
    assert len(offset) == 3


# --- Master Job Tests ---


@pytest.mark.asyncio
async def test_master_job_lifecycle(storage, test_project):
    """Test the lifecycle of a master job."""
    # Create a master job
    config_data = {"generator": "test_generator"}
    master_job_id = str(uuid.uuid4())

    # Save request config
    config_ref = storage.generate_request_config_path(master_job_id)
    await storage.save_request_config(config_ref, config_data)

    master_job = GenerationMasterJob(
        master_job_id=master_job_id,
        project_id=test_project.project_id,
        name="Test Job",
        status="pending",
        request_config_ref=config_ref,
        output_schema={"type": "object"},
        storage_uri=TEST_DB_URI,
        target_record_count=100,
    )

    # Log job start
    await storage.log_master_job_start(master_job)

    # Update status
    now = datetime.datetime.now(datetime.timezone.utc)
    await storage.update_master_job_status(master_job_id, "running", now)

    # Get job and verify status
    job = await storage.get_master_job(master_job_id)
    assert job.status == "running"

    # Complete job
    end_time = datetime.datetime.now(datetime.timezone.utc)
    summary = {"completed": 80, "failed": 20}
    await storage.log_master_job_end(master_job_id, "completed", summary, end_time, end_time)

    # Get job and verify status and counts
    job = await storage.get_master_job(master_job_id)
    assert job.status == "completed"
    assert job.completed_record_count == 80
    assert job.failed_record_count == 20


@pytest.mark.asyncio
async def test_list_master_jobs(storage, test_project):
    """Test listing master jobs with filters."""
    # Create jobs with different statuses
    status_counts = {"pending": 2, "running": 3, "completed": 4}

    for status, count in status_counts.items():
        for i in range(count):
            job_id = str(uuid.uuid4())
            config_ref = storage.generate_request_config_path(job_id)
            await storage.save_request_config(config_ref, {"test": i})
            job = GenerationMasterJob(
                master_job_id=job_id,
                project_id=test_project.project_id,
                name=f"Test Job {status} {i}",
                status=status,
                request_config_ref=config_ref,
                output_schema={"type": "object"},
                storage_uri=TEST_DB_URI,
                target_record_count=10,
            )
            await storage.log_master_job_start(job)

    # List all jobs
    all_jobs = await storage.list_master_jobs()
    assert len(all_jobs) == sum(status_counts.values())

    # Filter by project
    project_jobs = await storage.list_master_jobs(project_id=test_project.project_id)
    assert len(project_jobs) == sum(status_counts.values())

    # Filter by status
    completed_jobs = await storage.list_master_jobs(status_filter=["completed"])
    assert len(completed_jobs) == 4

    running_jobs = await storage.list_master_jobs(status_filter=["running"])
    assert len(running_jobs) == 3

    # Multiple status filter
    multi_status = await storage.list_master_jobs(status_filter=["pending", "running"])
    assert len(multi_status) == 5

    # Test limit and offset
    limited = await storage.list_master_jobs(limit=3)
    assert len(limited) == 3

    offset = await storage.list_master_jobs(offset=5)
    assert len(offset) == 4


# --- Execution Job Tests ---


@pytest.mark.asyncio
async def test_execution_job_lifecycle(storage, test_master_job):
    """Test the lifecycle of an execution job."""
    # Create execution job
    job_id = str(uuid.uuid4())
    run_config = {"batch_size": 10}
    run_config_str = json.dumps(run_config)
    job = GenerationJob(
        job_id=job_id,
        master_job_id=test_master_job.master_job_id,
        status="pending",
        run_config=run_config_str,
        run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
    )

    # Log job start
    await storage.log_execution_job_start(job)

    # Get job and verify
    retrieved = await storage.get_execution_job(job_id)
    assert retrieved is not None
    assert retrieved.job_id == job_id
    assert retrieved.status == "pending"

    # Complete job
    now = datetime.datetime.now(datetime.timezone.utc)
    counts = {"completed": 8, "filtered": 1, "duplicate": 0, "failed": 1}

    await storage.log_execution_job_end(job_id, "completed", counts, now, now)

    # Get job and verify
    completed = await storage.get_execution_job(job_id)
    assert completed.status == "completed"
    assert completed.completed_record_count == 8
    assert completed.filtered_record_count == 1
    assert completed.failed_record_count == 1


@pytest.mark.asyncio
async def test_list_execution_jobs(storage, test_master_job):
    """Test listing execution jobs with filters."""
    # Create multiple jobs
    status_counts = {"pending": 2, "duplicate": 3, "completed": 4}

    for status, count in status_counts.items():
        for i in range(count):
            run_config = {"batch": i}
            run_config_str = json.dumps(run_config)
            job = GenerationJob(
                job_id=str(uuid.uuid4()),
                master_job_id=test_master_job.master_job_id,
                status=status,
                run_config=run_config_str,
                run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
            )
            await storage.log_execution_job_start(job)

    # List all jobs for master
    all_jobs = await storage.list_execution_jobs(test_master_job.master_job_id)
    assert len(all_jobs) == sum(status_counts.values())

    # Filter by status
    completed = await storage.list_execution_jobs(test_master_job.master_job_id, status_filter=["completed"])
    assert len(completed) == 4

    # Multiple status
    multi_status = await storage.list_execution_jobs(test_master_job.master_job_id, status_filter=["pending", "duplicate"])
    assert len(multi_status) == 5

    # Test limit and offset
    limited = await storage.list_execution_jobs(test_master_job.master_job_id, limit=3)
    assert len(limited) == 3

    offset = await storage.list_execution_jobs(test_master_job.master_job_id, offset=5)
    assert len(offset) == 4


# --- Record Tests ---


@pytest.mark.asyncio
async def test_record_storage(storage, test_master_job):
    """Test saving and retrieving record data and metadata."""
    # Create execution job first
    run_config = {"test": "record_storage"}
    run_config_str = json.dumps(run_config)
    job = GenerationJob(
        job_id=str(uuid.uuid4()),
        master_job_id=test_master_job.master_job_id,
        status="pending",
        run_config=run_config_str,
        run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
    )
    await storage.log_execution_job_start(job)

    # Create record
    record_uid = str(uuid.uuid4())
    record_data = {"field1": "value1", "field2": 123}

    # Save record data
    output_ref = await storage.save_record_data(record_uid, test_master_job.master_job_id, job.job_id, record_data)

    # Create and save record metadata
    now = datetime.datetime.now(datetime.timezone.utc)
    record = Record(
        record_uid=record_uid,
        job_id=job.job_id,
        master_job_id=test_master_job.master_job_id,
        status="completed",
        output_ref=output_ref,
        start_time=now,
        end_time=now,
        last_update_time=now,
    )

    await storage.log_record_metadata(record)

    # Retrieve record metadata
    retrieved_meta = await storage.get_record_metadata(record_uid)
    assert retrieved_meta is not None
    assert retrieved_meta.record_uid == record_uid
    assert retrieved_meta.status == "completed"

    # Retrieve record data
    retrieved_data = await storage.get_record_data(output_ref)
    assert retrieved_data == record_data


@pytest.mark.asyncio
async def test_get_records_for_master_job(storage, test_master_job):
    """Test retrieving records for a master job with filters."""
    # Create execution job
    run_config = {"test": "get_records"}
    run_config_str = json.dumps(run_config)
    job = GenerationJob(
        job_id=str(uuid.uuid4()),
        master_job_id=test_master_job.master_job_id,
        status="pending",
        run_config=run_config_str,
        run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
    )
    await storage.log_execution_job_start(job)

    # Create records with different statuses
    status_counts = {"completed": 5, "failed": 3, "filtered": 2}
    records = []

    for status, count in status_counts.items():
        for i in range(count):
            record_uid = str(uuid.uuid4())

            # Save fake data reference (we don't need actual data for this test)
            if status == "completed":
                data = {"value": i}
                output_ref = await storage.save_record_data(record_uid, test_master_job.master_job_id, job.job_id, data)
            else:
                output_ref = None

            # Create record metadata
            now = datetime.datetime.now(datetime.timezone.utc)
            record = Record(
                record_uid=record_uid,
                job_id=job.job_id,
                master_job_id=test_master_job.master_job_id,
                status=status,
                output_ref=output_ref,
                start_time=now,
                end_time=now,
                last_update_time=now,
                error_message="Error" if status == "failed" else None,
            )

            await storage.log_record_metadata(record)
            records.append(record)

    # Get all records
    all_records = await storage.get_records_for_master_job(test_master_job.master_job_id)
    assert len(all_records) == sum(status_counts.values())

    # Filter by status
    completed = await storage.get_records_for_master_job(test_master_job.master_job_id, status_filter=["completed"])
    assert len(completed) == 5

    # Multiple status
    multi_status = await storage.get_records_for_master_job(test_master_job.master_job_id, status_filter=["failed", "filtered"])
    assert len(multi_status) == 5

    # Test limit and offset
    limited = await storage.get_records_for_master_job(test_master_job.master_job_id, limit=3)
    assert len(limited) == 3

    # Test count
    counts = await storage.count_records_for_master_job(test_master_job.master_job_id)
    assert counts.get("completed", 0) == 5
    assert counts.get("failed", 0) == 3
    assert counts.get("filtered", 0) == 2

    # Test count with filter
    filtered_counts = await storage.count_records_for_master_job(test_master_job.master_job_id, status_filter=["completed", "failed"])
    assert filtered_counts.get("completed", 0) == 5
    assert filtered_counts.get("failed", 0) == 3
    assert "filtered" not in filtered_counts


# --- Integration Tests: Complete Workflow ---


@pytest.mark.asyncio
async def test_complete_workflow(storage):
    """Test a complete workflow from project creation to record retrieval."""
    # 1. Create project
    project = Project(project_id=str(uuid.uuid4()), name="Workflow Test Project")
    await storage.save_project(project)

    # 2. Create master job
    master_job_id = str(uuid.uuid4())
    config_data = {"generator": "workflow_test"}
    config_ref = storage.generate_request_config_path(master_job_id)
    await storage.save_request_config(config_ref, config_data)

    master_job = GenerationMasterJob(
        master_job_id=master_job_id,
        project_id=project.project_id,
        name="Workflow Test Job",
        status="pending",
        request_config_ref=config_ref,
        output_schema={"type": "object"},
        storage_uri=TEST_DB_URI,
        target_record_count=100,
    )
    await storage.log_master_job_start(master_job)

    # 3. Start master job
    now = datetime.datetime.now(datetime.timezone.utc)
    await storage.update_master_job_status(master_job_id, "running", now)

    # 4. Create execution job
    job_id = str(uuid.uuid4())
    run_config = {"batch_size": 10}
    run_config_str = json.dumps(run_config)
    job = GenerationJob(
        job_id=job_id,
        master_job_id=master_job_id,
        status="pending",
        run_config=run_config_str,
        run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
    )
    await storage.log_execution_job_start(job)

    # 5. Start execution job
    job.status = "pending"
    job.start_time = now
    await storage.log_execution_job_start(job)

    # 6. Generate some records
    records = []
    record_datas = []

    for i in range(10):
        record_uid = str(uuid.uuid4())
        record_data = {"index": i, "value": f"test-{i}"}

        # Save data for successful records
        if i < 8:  # 8 successful, 2 failed
            output_ref = await storage.save_record_data(record_uid, master_job_id, job_id, record_data)
            status = "completed"
            error = None
        else:
            output_ref = None
            status = "failed"
            error = "Test error"

        record = Record(
            record_uid=record_uid,
            job_id=job_id,
            master_job_id=master_job_id,
            status=status,
            output_ref=output_ref,
            start_time=now,
            end_time=now,
            last_update_time=now,
            error_message=error,
        )

        await storage.log_record_metadata(record)
        records.append(record)
        if output_ref:
            record_datas.append((record_uid, record_data))

    # 7. Complete execution job
    job_end = datetime.datetime.now(datetime.timezone.utc)
    job_counts = {"completed": 8, "failed": 2}
    await storage.log_execution_job_end(job_id, "completed", job_counts, job_end, job_end)

    # 8. Complete master job
    master_end = datetime.datetime.now(datetime.timezone.utc)
    master_summary = {"completed": 8, "failed": 2}
    await storage.log_master_job_end(master_job_id, "completed", master_summary, master_end, master_end)

    # --- Verification ---

    # Verify master job
    master = await storage.get_master_job(master_job_id)
    assert master.status == "completed"
    assert master.completed_record_count == 8
    assert master.failed_record_count == 2

    # Verify execution job
    exec_job = await storage.get_execution_job(job_id)
    assert exec_job.status == "completed"
    assert exec_job.completed_record_count == 8
    assert exec_job.failed_record_count == 2

    # Verify records
    job_records = await storage.get_records_for_master_job(master_job_id)
    assert len(job_records) == 10

    completed_records = await storage.get_records_for_master_job(master_job_id, status_filter=["completed"])
    assert len(completed_records) == 8

    # Verify record data
    for record_uid, original_data in record_datas:
        record = await storage.get_record_metadata(record_uid)
        data = await storage.get_record_data(record.output_ref)
        assert data == original_data

    # Verify counts
    counts = await storage.count_records_for_master_job(master_job_id)
    assert counts["completed"] == 8
    assert counts["failed"] == 2
