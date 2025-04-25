"""
Basic test script for the LocalStorage implementation.
This script can be run directly to test the basic functionality.
"""

import asyncio
import datetime
import hashlib
import json
import os
import shutil
import traceback
import uuid

from starfish.data_factory.storage.local.local_storage import LocalStorage
from starfish.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)

# Test database directory
TEST_DB_DIR = "/tmp/starfish_test_basic"
TEST_DB_URI = f"file://{TEST_DB_DIR}"


async def run_basic_test():
    """Run a basic test of the LocalStorage implementation."""
    print("Starting basic LocalStorage test")

    # Setup test environment
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)
    os.makedirs(TEST_DB_DIR, exist_ok=True)

    storage = None

    try:
        # Create storage
        print("Step 1: Creating storage instance")
        storage = LocalStorage(TEST_DB_URI)

        print("Step 2: Setting up storage")
        await storage.setup()
        print("✓ Storage setup complete")

        # Create a project
        print("Step 3: Creating project")
        project_id = str(uuid.uuid4())
        project = Project(project_id=project_id, name="Test Basic Project", description="A simple test project")
        await storage.save_project(project)
        print(f"✓ Project created: {project.name}")

        # Create a master job
        print("Step 4: Creating master job")
        master_job_id = str(uuid.uuid4())
        config_data = {"test": True, "generator": "test_generator"}
        config_ref = storage.generate_request_config_path(master_job_id)
        await storage.save_request_config(config_ref, config_data)

        master_job = GenerationMasterJob(
            master_job_id=master_job_id,
            project_id=project_id,
            name="Test Master Job",
            status="pending",
            request_config_ref=config_ref,
            output_schema={"type": "object"},
            storage_uri=TEST_DB_URI,
            target_record_count=10,
        )
        await storage.log_master_job_start(master_job)
        print(f"✓ Master job created: {master_job.name}")

        # Update master job status
        print("Step 5: Updating master job status")
        now = datetime.datetime.now(datetime.timezone.utc)
        await storage.update_master_job_status(master_job_id, "running", now)

        # Create an execution job
        print("Step 6: Creating execution job")
        job_id = str(uuid.uuid4())
        run_config = {"batch_size": 5}
        run_config_str = json.dumps(run_config)
        job = GenerationJob(
            job_id=job_id,
            master_job_id=master_job_id,
            status="pending",
            run_config=run_config_str,
            run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
        )
        await storage.log_execution_job_start(job)
        print(f"✓ Execution job created: {job.job_id}")

        # Start the execution job (update its status)
        print("Step 7: Starting execution job")
        now = datetime.datetime.now(datetime.timezone.utc)

        # Update job fields
        job.status = "pending"
        job.start_time = now

        try:
            # Log the updated job
            await storage.log_execution_job_start(job)
            print("✓ Execution job started")
        except Exception as e:
            print(f"✗ Error starting execution job: {str(e)}")
            traceback.print_exc()
            raise

        # Generate some test records
        print("Step 8: Generating test records")
        record_uids = []
        for i in range(5):
            print(f"  Creating record {i+1}/5...")
            record_uid = str(uuid.uuid4())
            record_data = {"index": i, "data": f"Test data {i}"}

            # Save record data
            output_ref = await storage.save_record_data(record_uid, master_job_id, job_id, record_data)

            # Create and save record metadata
            record = Record(
                record_uid=record_uid,
                job_id=job_id,
                master_job_id=master_job_id,
                status="completed",
                output_ref=output_ref,
                start_time=now,
                end_time=now,
                last_update_time=now,
            )
            await storage.log_record_metadata(record)
            record_uids.append(record_uid)
            print(f"✓ Record {i+1} created: {record_uid[:8]}...")

        # Complete the execution job
        print("Step 9: Completing execution job")
        job_end_time = datetime.datetime.now(datetime.timezone.utc)
        counts = {"completed": 5, "failed": 0}
        try:
            await storage.log_execution_job_end(job_id, "completed", counts, job_end_time, job_end_time)
            print("✓ Execution job completed")
        except Exception as e:
            print(f"✗ Error completing execution job: {str(e)}")
            traceback.print_exc()
            raise

        # Complete the master job
        print("Step 10: Completing master job")
        master_end_time = datetime.datetime.now(datetime.timezone.utc)
        summary = {"completed": 5, "failed": 0}
        await storage.log_master_job_end(master_job_id, "completed", summary, master_end_time, master_end_time)
        print("✓ Master job completed")

        # Retrieve and verify data
        print("Step 11: Verifying data")
        # Get the master job
        retrieved_master = await storage.get_master_job(master_job_id)
        assert retrieved_master.status == "completed"
        assert retrieved_master.completed_record_count == 5
        print("✓ Master job verified")

        # Get the execution job
        retrieved_job = await storage.get_execution_job(job_id)
        assert retrieved_job.status == "completed"
        assert retrieved_job.completed_record_count == 5
        print("✓ Execution job verified")

        # Get records
        records = await storage.get_records_for_master_job(master_job_id)
        assert len(records) == 5
        print(f"✓ Retrieved {len(records)} records")

        # Get record data for first record
        first_record = records[0]
        record_data = await storage.get_record_data(first_record.output_ref)
        print(f"✓ Record data retrieved: {json.dumps(record_data)}")

        # Count records
        count_by_status = await storage.count_records_for_master_job(master_job_id)
        assert count_by_status.get("completed", 0) == 5
        print(f"✓ Record counts verified: {json.dumps(count_by_status)}")

        # Check configuration storage
        retrieved_config = await storage.get_request_config(config_ref)
        assert retrieved_config["generator"] == "test_generator"
        print(f"✓ Config data verified: {json.dumps(retrieved_config)}")

        # Close the storage
        await storage.close()
        print("✓ Storage closed successfully")

        print("\n✓ All tests passed! The LocalStorage implementation is working correctly.")

        # Show details of what was created
        print("\nFiles created:")
        print(f"- SQLite DB: {os.path.join(TEST_DB_DIR, 'metadata.db')}")
        print(f"- Config: {os.path.join(TEST_DB_DIR, 'configs', f'{master_job_id}.request.json')}")
        print(f"- Data files: {len(record_uids)} record JSON files in nested directories")

    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        traceback.print_exc()
        raise e
    finally:
        # Clean up resources
        if storage:
            try:
                await storage.close()
            except Exception:
                pass
        # Don't clean up so user can inspect files
        print(f"\nTest files are in {TEST_DB_DIR} - you can inspect them and delete when done.")


if __name__ == "__main__":
    asyncio.run(run_basic_test())
