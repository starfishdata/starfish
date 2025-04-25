#!/usr/bin/env python
"""
Main test script for the StarFish storage layer.
This script tests the core functionality of the storage layer in a sequence of operations.
"""

import asyncio
import datetime
import hashlib
import json
import os
import shutil
import time
import uuid

import pytest

# Import storage components
from starfish.data_factory.storage.local.local_storage import LocalStorage
from starfish.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)

# Test database location - can be overridden with env var
TEST_DB_DIR = os.environ.get("STARFISH_TEST_DB_DIR", "/tmp/starfish_test_db")
TEST_DB_URI = f"file://{TEST_DB_DIR}"

# Test mode - 'basic' (quick test) or 'full' (comprehensive)
TEST_MODE = os.environ.get("STARFISH_TEST_MODE", "basic")


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


@pytest.mark.asyncio
async def test_basic_workflow():
    """Test the basic workflow of the storage layer."""
    print_header("TESTING BASIC STORAGE WORKFLOW")

    # Clean up any existing test database
    if os.path.exists(TEST_DB_DIR):
        print(f"Cleaning up existing test directory: {TEST_DB_DIR}")
        shutil.rmtree(TEST_DB_DIR)

    # Create test directory
    os.makedirs(TEST_DB_DIR, exist_ok=True)

    print(f"Initializing storage with URI: {TEST_DB_URI}")
    storage = LocalStorage(TEST_DB_URI)
    await storage.setup()

    try:
        # 1. Create a project
        print("\n1. Creating project...")
        project_id = str(uuid.uuid4())
        project = Project(project_id=project_id, name="Test Project", description="A test project for storage layer testing")
        await storage.save_project(project)
        print(f"  - Created project: {project.name} ({project.project_id})")

        # 2. Create a master job
        print("\n2. Creating master job...")
        master_job_id = str(uuid.uuid4())

        # First save the request config
        config_data = {"generator": "test_generator", "parameters": {"num_records": 10, "complexity": "medium"}}
        config_ref = storage.generate_request_config_path(master_job_id)
        await storage.save_request_config(config_ref, config_data)
        print(f"  - Saved request config to: {config_ref}")

        # Now create the master job
        master_job = GenerationMasterJob(
            master_job_id=master_job_id,
            project_id=project_id,
            name="Test Master Job",
            status="pending",
            request_config_ref=config_ref,
            output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            storage_uri=TEST_DB_URI,
            target_record_count=10,
        )
        await storage.log_master_job_start(master_job)
        print(f"  - Created master job: {master_job.name} ({master_job.master_job_id})")

        # Update master job status to running
        now = datetime.datetime.now(datetime.timezone.utc)
        await storage.update_master_job_status(master_job_id, "running", now)
        print("  - Updated master job status to: running")

        # 3. Create an execution job
        print("\n3. Creating execution job...")
        job_id = str(uuid.uuid4())
        run_config = {"test_param": "test_value"}
        run_config_str = json.dumps(run_config)
        job = GenerationJob(
            job_id=job_id,
            master_job_id=master_job_id,
            status="pending",
            worker_id="test-worker-1",
            run_config=run_config_str,
            run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
        )
        await storage.log_execution_job_start(job)
        print(f"  - Created execution job: {job.job_id}")

        # Update execution job status to running
        now = datetime.datetime.now(datetime.timezone.utc)
        job.status = "running"
        job.start_time = now
        await storage.log_execution_job_start(job)
        print("  - Updated execution job status to: running")

        # 4. Create records
        print("\n4. Creating records...")
        records = []
        for i in range(5):
            record_uid = str(uuid.uuid4())
            record = Record(record_uid=record_uid, job_id=job_id, master_job_id=master_job_id, status="pending")
            await storage.log_record_metadata(record)
            records.append(record)
            print(f"  - Created record: {record.record_uid}")

        # 5. Save record data
        print("\n5. Saving record data...")
        for i, record in enumerate(records):
            # Generate some test data
            data = {"name": f"Test Record {i}", "value": i * 10, "is_valid": True, "timestamp": datetime.datetime.now().isoformat()}

            # Save the data
            output_ref = await storage.save_record_data(record.record_uid, master_job_id, job_id, data)

            # Update the record with the output reference
            record.output_ref = output_ref
            record.status = "completed"
            record.end_time = datetime.datetime.now(datetime.timezone.utc)
            await storage.log_record_metadata(record)
            print(f"  - Saved data for record {i}: {output_ref}")

        # 6. Complete the execution job
        print("\n6. Completing execution job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        counts = {"completed": 5, "filtered": 0, "duplicate": 0, "failed": 0}
        await storage.log_execution_job_end(job_id, "completed", counts, now, now)
        print("  - Marked execution job as completed")

        # 7. Complete the master job
        print("\n7. Completing master job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        summary = {"completed": 5, "filtered": 0, "duplicate": 0, "failed": 0}
        await storage.log_master_job_end(master_job_id, "completed", summary, now, now)
        print("  - Marked master job as completed")

        # 8. Retrieve and verify data
        print("\n8. Retrieving and verifying data...")

        # Get the project
        retrieved_project = await storage.get_project(project_id)
        print(f"  - Retrieved project: {retrieved_project.name}")
        assert retrieved_project.project_id == project_id

        # Get the master job
        retrieved_master = await storage.get_master_job(master_job_id)
        print(f"  - Retrieved master job: {retrieved_master.name}")
        assert retrieved_master.status == "completed"

        # Get the execution job
        retrieved_job = await storage.get_execution_job(job_id)
        print(f"  - Retrieved execution job: {retrieved_job.job_id}")
        assert retrieved_job.status == "completed"

        # Get the records
        retrieved_records = await storage.get_records_for_master_job(master_job_id)
        print(f"  - Retrieved {len(retrieved_records)} records")
        assert len(retrieved_records) == 5

        # Get the record data
        record = retrieved_records[0]
        record_data = await storage.get_record_data(record.output_ref)
        print(f"  - Retrieved data for record: {record.record_uid}")
        assert "name" in record_data
        assert "value" in record_data

        # Get counts
        counts = await storage.count_records_for_master_job(master_job_id)
        print(f"  - Record counts: {counts}")
        assert counts["completed"] == 5

        print("\nAll basic tests completed successfully!")

    finally:
        # Close the storage connection
        await storage.close()
        if TEST_MODE == "cleanup":
            print(f"\nCleaning up test directory: {TEST_DB_DIR}")
            shutil.rmtree(TEST_DB_DIR)
        else:
            print(f"\nLeaving test database in place for inspection: {TEST_DB_DIR}")


@pytest.mark.asyncio
async def small_performance_test():
    """Run a small performance test."""
    print_header("RUNNING SMALL PERFORMANCE TEST")

    # Clean up any existing test database
    if os.path.exists(TEST_DB_DIR):
        print(f"Cleaning up existing test directory: {TEST_DB_DIR}")
        shutil.rmtree(TEST_DB_DIR)

    # Create test directory
    os.makedirs(TEST_DB_DIR, exist_ok=True)

    print(f"Initializing storage with URI: {TEST_DB_URI}")
    storage = LocalStorage(TEST_DB_URI)
    await storage.setup()

    try:
        NUM_JOBS = 20
        RECORDS_PER_JOB = 5
        TOTAL_RECORDS = NUM_JOBS * RECORDS_PER_JOB

        start_time = time.time()

        # Create project
        project_id = str(uuid.uuid4())
        project = Project(project_id=project_id, name="Performance Test Project", description="A project for performance testing")
        await storage.save_project(project)

        # Create master job
        master_job_id = str(uuid.uuid4())
        config_data = {"generator": "perf_test_generator", "parameters": {"num_records": TOTAL_RECORDS}}
        config_ref = storage.generate_request_config_path(master_job_id)
        await storage.save_request_config(config_ref, config_data)

        master_job = GenerationMasterJob(
            master_job_id=master_job_id,
            project_id=project_id,
            name="Performance Test Master Job",
            status="running",
            request_config_ref=config_ref,
            output_schema={"type": "object", "properties": {}},
            storage_uri=TEST_DB_URI,
            target_record_count=TOTAL_RECORDS,
        )
        await storage.log_master_job_start(master_job)

        # Create execution jobs and records
        for job_idx in range(NUM_JOBS):
            # Create job
            job_id = str(uuid.uuid4())
            run_config = {"job_idx": job_idx, "records_per_job": RECORDS_PER_JOB}
            run_config_str = json.dumps(run_config)
            job = GenerationJob(
                job_id=job_id,
                master_job_id=master_job_id,
                status="running",
                worker_id=f"worker-{job_idx}",
                run_config=run_config_str,
                run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
            )
            await storage.log_execution_job_start(job)

            # Create records
            for rec_idx in range(RECORDS_PER_JOB):
                global_idx = job_idx * RECORDS_PER_JOB + rec_idx
                record_uid = str(uuid.uuid4())
                record = Record(record_uid=record_uid, job_id=job_id, master_job_id=master_job_id, status="pending")
                await storage.log_record_metadata(record)

                # Generate and save data
                data = {
                    "id": f"record-{global_idx}",
                    "name": f"Test Record {global_idx}",
                    "value": global_idx * 10,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "tags": [f"tag-{global_idx % 5}"],
                }

                output_ref = await storage.save_record_data(record_uid, master_job_id, job_id, data)

                # Update record status
                record.status = "completed"
                record.output_ref = output_ref
                record.end_time = datetime.datetime.now(datetime.timezone.utc)
                await storage.log_record_metadata(record)

            # Complete the job
            now = datetime.datetime.now(datetime.timezone.utc)
            counts = {"completed": RECORDS_PER_JOB, "filtered": 0, "duplicate": 0, "failed": 0}
            await storage.log_execution_job_end(job_id, "completed", counts, now, now)

        # Complete the master job
        now = datetime.datetime.now(datetime.timezone.utc)
        summary = {"completed": TOTAL_RECORDS, "filtered": 0, "duplicate": 0, "failed": 0}
        await storage.log_master_job_end(master_job_id, "completed", summary, now, now)

        # Verification
        retrieved_master = await storage.get_master_job(master_job_id)
        assert retrieved_master.status == "completed"
        assert retrieved_master.completed_record_count == TOTAL_RECORDS

        retrieved_jobs = await storage.list_execution_jobs(master_job_id)
        assert len(retrieved_jobs) == NUM_JOBS

        retrieved_records = await storage.get_records_for_master_job(master_job_id)
        assert len(retrieved_records) == TOTAL_RECORDS

        counts = await storage.count_records_for_master_job(master_job_id)
        assert counts["completed"] == TOTAL_RECORDS

        total_time = time.time() - start_time

        print("\nPerformance Test Results:")
        print(f"Total time: {total_time:.4f}s")
        print(f"Records: {TOTAL_RECORDS}")
        print(f"Jobs: {NUM_JOBS}")
        print(f"Throughput: {TOTAL_RECORDS/total_time:.2f} records/second")
        print(f"Average time per record: {total_time/TOTAL_RECORDS*1000:.2f}ms")

    finally:
        await storage.close()
        if TEST_MODE == "cleanup":
            shutil.rmtree(TEST_DB_DIR)


@pytest.mark.asyncio
async def main():
    """Main test function."""
    print(f"Storage test mode: {TEST_MODE}")
    print(f"Test database: {TEST_DB_DIR}")

    await test_basic_workflow()

    # If full test mode, also run the performance test
    if TEST_MODE == "full":
        await small_performance_test()

    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
