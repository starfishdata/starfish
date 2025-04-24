import argparse
import asyncio
import datetime
import hashlib
import json
import os
import random
import shutil
import time
import uuid
from typing import Any, Dict

import pytest
import pytest_asyncio

from starfish.data_factory.storage.local.local_storage import LocalStorage
from starfish.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)

# Default test database directory - can be overridden
TEST_DB_DIR = os.environ.get("STARFISH_TEST_DB_DIR", "/tmp/starfish_test_performance")
TEST_DB_URI = f"file://{TEST_DB_DIR}"

# Default performance test parameters - can be overridden via args
DEFAULT_TOTAL_RECORDS = 500  # Higher default for meaningful concurrency test
DEFAULT_BATCH_SIZE = 5  # Records per job
DEFAULT_CONCURRENCY = 50  # Number of concurrent operations - test with higher concurrency
DEFAULT_DATA_COMPLEXITY = "medium"  # Size/complexity of generated records


def parse_args():
    """Parse command line arguments for the performance test."""
    parser = argparse.ArgumentParser(description="Storage Layer Performance Test")
    parser.add_argument(
        "--total-records", type=int, default=DEFAULT_TOTAL_RECORDS, help=f"Total number of records to generate (default: {DEFAULT_TOTAL_RECORDS})"
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Number of records per job (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument(
        "--concurrency", type=int, default=DEFAULT_CONCURRENCY, help=f"Maximum number of concurrent operations (default: {DEFAULT_CONCURRENCY})"
    )
    parser.add_argument(
        "--complexity",
        choices=["small", "medium", "large"],
        default=DEFAULT_DATA_COMPLEXITY,
        help=f"Size/complexity of generated data (default: {DEFAULT_DATA_COMPLEXITY})",
    )
    parser.add_argument("--db-dir", type=str, default=TEST_DB_DIR, help=f"Directory for test database (default: {TEST_DB_DIR})")
    parser.add_argument("--use-batch", action="store_true", help="Use batch operations where possible for better performance")
    parser.add_argument("--read-performance", action="store_true", help="Run the read performance test instead of the workflow test")
    return parser.parse_args()


# Data generation helpers
def generate_qa_data(index: int, complexity: str) -> Dict[str, Any]:
    """Generate question-answer data with controllable complexity."""
    # Base data that's always included
    data = {
        "question": f"What is the result of {index} + {index*2}?",
        "answer": f"The result of {index} + {index*2} is {index + index*2}.",
        "created_at": datetime.datetime.now().isoformat(),
        "metadata": {
            "difficulty": random.choice(["easy", "medium", "hard"]),
            "category": random.choice(["math", "logic", "general"]),
            "tags": [f"tag-{i}" for i in range(1, random.randint(2, 5))],
        },
    }

    # Add complexity based on the requested level
    if complexity in ["medium", "large"]:
        data["alternatives"] = [
            f"The result is {index + index*2 + random.randint(-5, 5)}.",
            f"The result is {index + index*2 + random.randint(-5, 5)}.",
            f"The result is {index + index*2 + random.randint(-5, 5)}.",
        ]
        data["explanation"] = f"To calculate {index} + {index*2}, we add {index} and {index*2} together to get {index + index*2}."

    if complexity == "large":
        # Add much more data for "large" complexity
        data["detailed_explanation"] = "\n".join(
            [
                f"Step 1: Write down the numbers {index} and {index*2}.",
                f"Step 2: Add the numbers together: {index} + {index*2} = {index + index*2}.",
                f"Step 3: Verify the result by checking: {index + index*2} - {index} = {index*2}.",
                f"Step 4: Therefore, {index} + {index*2} = {index + index*2}.",
            ]
        )
        data["related_questions"] = [
            {"question": f"What is {index} * {index*2}?", "answer": f"{index * (index*2)}"},
            {"question": f"What is {index} - {index*2}?", "answer": f"{index - (index*2)}"},
            {"question": f"What is {index} / {index*2}?", "answer": f"{index / (index*2):.2f}"},
        ]
        # Add a large amount of irrelevant data to test large payload performance
        data["examples"] = [{f"example_{i}": f"This is example {i} for question {index}. " * 3} for i in range(10)]

    return data


async def batch_operation(tasks, concurrency=DEFAULT_CONCURRENCY):
    """Execute a batch of async tasks with limited concurrency using semaphore."""
    semaphore = asyncio.Semaphore(concurrency)

    async def task_with_semaphore(task):
        async with semaphore:
            return await task

    # Process tasks concurrently with limited concurrency
    return await asyncio.gather(*(task_with_semaphore(task) for task in tasks))


@pytest_asyncio.fixture(scope="function")
async def storage(request):
    """Fixture to create and clean up a test storage for the entire module."""
    # Get test directory from the request object (passed from test function)
    test_db_dir = getattr(request, "param", TEST_DB_DIR)
    test_db_uri = f"file://{test_db_dir}"

    # Ensure clean directory
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
    os.makedirs(test_db_dir, exist_ok=True)

    # Create storage instance
    storage = LocalStorage(test_db_uri)
    await storage.setup()

    yield storage

    # Cleanup
    await storage.close()
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)


@pytest.mark.asyncio
async def test_realistic_workflow(
    storage,
    total_records=DEFAULT_TOTAL_RECORDS,
    batch_size=DEFAULT_BATCH_SIZE,
    concurrency=DEFAULT_CONCURRENCY,
    complexity=DEFAULT_DATA_COMPLEXITY,
    use_batch=False,
):
    """
    Test with a realistic workflow that simulates actual usage patterns.

    This represents a more realistic scenario where:
    1. A user creates a project and requests a certain number of records
    2. The system creates a master job
    3. The system creates multiple execution jobs based on the batch size
    4. Each job processes its batch of records asynchronously
    5. As records are completed, job and master job status are updated
    """
    num_jobs = (total_records + batch_size - 1) // batch_size  # Ceiling division

    print("\nRunning realistic workflow test with:")
    print(f"  - Total records: {total_records}")
    print(f"  - Records per job: {batch_size}")
    print(f"  - Number of jobs: {num_jobs}")
    print(f"  - Concurrency level: {concurrency}")
    print(f"  - Data complexity: {complexity}")
    print(f"  - Use batch operations: {use_batch}")

    total_start_time = time.time()

    # --- 1. User creates a project ---
    start_time = time.time()
    project = Project(project_id=str(uuid.uuid4()), name="QA Dataset Project", description="A project for generating question-answer pairs")
    await storage.save_project(project)
    project_time = time.time() - start_time
    print(f"\n1. Project creation: {project_time:.4f}s")

    # --- 2. User requests data generation with schema ---
    start_time = time.time()
    master_job_id = str(uuid.uuid4())

    # Define the output schema for QA data
    output_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question text"},
            "answer": {"type": "string", "description": "The answer text"},
            "created_at": {"type": "string", "format": "date-time"},
            "metadata": {
                "type": "object",
                "properties": {
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "required": ["question", "answer"],
    }

    # Save configuration
    config_data = {
        "generator": "qa_pair_generator",
        "parameters": {"total_records": total_records, "batch_size": batch_size, "style": "factual", "complexity": complexity},
    }
    config_ref = storage.generate_request_config_path(master_job_id)
    await storage.save_request_config(config_ref, config_data)

    # Create the master job
    master_job = GenerationMasterJob(
        master_job_id=master_job_id,
        project_id=project.project_id,
        name="QA Pair Generation",
        status="pending",
        request_config_ref=config_ref,
        output_schema=output_schema,
        storage_uri=storage._metadata_handler.db_path.replace("/metadata.db", ""),
        target_record_count=total_records,
    )
    await storage.log_master_job_start(master_job)

    # Mark as running
    now = datetime.datetime.now(datetime.timezone.utc)
    await storage.update_master_job_status(master_job_id, "running", now)
    master_job_time = time.time() - start_time
    print(f"2. Master job creation and setup: {master_job_time:.4f}s")

    # --- 3. System creates execution jobs ---
    jobs_start_time = time.time()
    execution_jobs = []

    # Create jobs
    for job_idx in range(num_jobs):
        # Calculate actual batch size (may be smaller for the last job)
        actual_batch_size = min(batch_size, total_records - job_idx * batch_size)
        if actual_batch_size <= 0:
            break

        job_id = str(uuid.uuid4())
        job = GenerationJob(
            job_id=job_id,
            master_job_id=master_job_id,
            status="pending",
            worker_id=f"worker-{job_idx % (concurrency * 2)}",  # Simulate multiple workers
            run_config={"start_index": job_idx * batch_size, "count": actual_batch_size, "complexity": complexity},
            run_config_hash=hashlib.sha256(
                json.dumps({"start_index": job_idx * batch_size, "count": actual_batch_size, "complexity": complexity}).encode()
            ).hexdigest(),
        )
        execution_jobs.append(job)

    # Use batch operation if enabled, otherwise use concurrent operations
    if use_batch and hasattr(storage._metadata_handler, "batch_save_execution_jobs"):
        # Use the batch operation to save all jobs in one transaction
        await storage._metadata_handler.batch_save_execution_jobs(execution_jobs)
    else:
        # Process jobs concurrently using gather - let SQLite handle serialization
        job_tasks = [storage.log_execution_job_start(job) for job in execution_jobs]
        await batch_operation(job_tasks, concurrency)

    jobs_creation_time = time.time() - jobs_start_time
    print(f"3. Execution jobs creation ({num_jobs} jobs): {jobs_creation_time:.4f}s ({jobs_creation_time/num_jobs:.6f}s per job)")

    # --- 4. Workers process jobs and generate records ---
    processing_start_time = time.time()

    # Keep track of counts for the final summary
    completed_records = 0
    filtered_records = 0
    failed_records = 0

    # Process job concurrently with limited concurrency
    async def process_job(job_idx, job):
        job_start_time = time.time()

        # Mark job as pending
        job.status = "pending"
        job.start_time = datetime.datetime.now(datetime.timezone.utc)
        await storage.log_execution_job_start(job)

        # Calculate actual batch size and record range for this job
        start_index = job_idx * batch_size
        actual_batch_size = min(batch_size, total_records - start_index)

        # This job's records
        job_records = []
        record_creation_tasks = []

        # Create record metadata and save it
        for i in range(actual_batch_size):
            global_idx = start_index + i

            # Create record
            record_uid = str(uuid.uuid4())
            record = Record(record_uid=record_uid, job_id=job.job_id, master_job_id=master_job_id, status="pending")
            job_records.append(record)

            # Add to tasks list or save immediately
            if not use_batch:
                record_creation_tasks.append(storage.log_record_metadata(record))

        # Save records
        if use_batch and hasattr(storage._metadata_handler, "batch_save_records"):
            # Use batch operation to save all records in one transaction
            await storage._metadata_handler.batch_save_records(job_records)
        elif record_creation_tasks:
            # Process record creation tasks concurrently
            await asyncio.gather(*record_creation_tasks)

        # Track local job counts
        job_completed = 0
        job_filtered = 0
        job_failed = 0

        # Create a list to hold data save tasks
        data_save_tasks = []

        # Process records for this job
        for i, record in enumerate(job_records):
            global_idx = start_index + i

            # Generate QA data (simulates actual generation)
            try:
                # Simulate occasional failures
                if random.random() < 0.02:  # 2% failure rate
                    record.status = "failed"
                    record.error_message = "Simulated generation failure"
                    job_failed += 1
                # Simulate occasional filtered records
                elif random.random() < 0.05:  # 5% filter rate
                    record.status = "filtered"
                    record.error_message = "Filtered: low quality response"
                    job_filtered += 1
                # Normal successful generation
                else:
                    record_data = generate_qa_data(global_idx, complexity)

                    # Save data (this is file I/O and can be done concurrently)
                    data_save_task = storage.save_record_data(record.record_uid, master_job_id, job.job_id, record_data)
                    data_save_tasks.append((record, data_save_task))
                    job_completed += 1
            except Exception as e:
                # Unexpected error
                record.status = "failed"
                record.error_message = f"Error: {str(e)}"
                job_failed += 1

            # Set completion time for all records
            record.end_time = datetime.datetime.now(datetime.timezone.utc)

        # Wait for all data saves to complete concurrently
        if data_save_tasks:
            # Process data save tasks concurrently
            for record, task in data_save_tasks:
                record.status = "completed"
                record.output_ref = await task

        # Update all records with final status
        if use_batch and hasattr(storage._metadata_handler, "batch_save_records"):
            # Batch update all records
            await storage._metadata_handler.batch_save_records(job_records)
        else:
            update_tasks = [storage.log_record_metadata(record) for record in job_records]
            await asyncio.gather(*update_tasks)

        # Complete the job
        job_end_time = datetime.datetime.now(datetime.timezone.utc)
        job_counts = {"completed": job_completed, "filtered": job_filtered, "duplicate": 0, "failed": job_failed}

        await storage.log_execution_job_end(job.job_id, "completed", job_counts, job_end_time, job_end_time)

        job_time = time.time() - job_start_time
        print(f"  - Job {job_idx+1}/{num_jobs} completed: {job_time:.4f}s, " + f"{actual_batch_size} records ({job_time/actual_batch_size:.4f}s per record)")

        # Return the counts for aggregation
        return job_completed, job_filtered, job_failed

    # Process jobs concurrently with limited concurrency
    job_tasks = [process_job(job_idx, job) for job_idx, job in enumerate(execution_jobs)]
    job_results = await batch_operation(job_tasks, concurrency=min(concurrency, 10))

    # Aggregate counts from all jobs
    for job_completed, job_filtered, job_failed in job_results:
        completed_records += job_completed
        filtered_records += job_filtered
        failed_records += job_failed

    processing_time = time.time() - processing_start_time
    print(f"4. Record generation and processing: {processing_time:.4f}s " + f"({processing_time/total_records:.4f}s per record)")

    # --- 5. Complete the master job ---
    completion_start_time = time.time()

    # Prepare summary with actual counts
    summary = {
        "completed": completed_records,
        "filtered": filtered_records,
        "duplicate": 0,  # We didn't simulate duplicates
        "failed": failed_records,
        "total_requested": total_records,
        "total_processed": completed_records + filtered_records + failed_records,
    }

    # Mark master job as completed
    now = datetime.datetime.now(datetime.timezone.utc)
    await storage.log_master_job_end(master_job_id, "completed", summary, now, now)

    completion_time = time.time() - completion_start_time
    print(f"5. Master job completion: {completion_time:.4f}s")

    # --- 6. Read operations (simulate user querying results) ---
    read_start_time = time.time()

    # Verify master job
    retrieved_master = await storage.get_master_job(master_job_id)
    assert retrieved_master.status == "completed"

    # Get all jobs
    retrieved_jobs = await storage.list_execution_jobs(master_job_id)
    assert len(retrieved_jobs) == num_jobs

    # Get total record count
    counts = await storage.count_records_for_master_job(master_job_id)
    assert counts["completed"] + counts["filtered"] + counts["failed"] == total_records

    # Paginated record retrieval (simulate UI pagination)
    page_size = 50
    page_count = (total_records + page_size - 1) // page_size

    # Process page reads concurrently
    page_tasks = []
    for page in range(min(3, page_count)):  # Test up to 3 pages
        page_tasks.append(storage.get_records_for_master_job(master_job_id, limit=page_size, offset=page * page_size))

    if page_tasks:
        page_start = time.time()
        page_results = await asyncio.gather(*page_tasks)
        page_time = time.time() - page_start

        for i, paginated in enumerate(page_results):
            assert len(paginated) <= page_size
            print(f"  - Page {i+1} retrieval ({len(paginated)} records): {page_time/len(page_results):.4f}s")

    # Read individual records (simulate user viewing details)
    data_read_times = []
    sample_size = min(20, total_records)  # Test up to 20 random records

    # Get some completed records
    completed_recs = await storage.get_records_for_master_job(master_job_id, status_filter=["completed"], limit=100)

    record_read_tasks = []
    if completed_recs:
        # Select random samples from the completed records
        samples = random.sample(completed_recs, min(sample_size, len(completed_recs)))

        # Read records concurrently
        for i, record in enumerate(samples):
            if record.output_ref:  # Only try to read records with data
                record_read_tasks.append((i + 1, record, storage.get_record_data(record.output_ref)))

        # Wait for all read tasks to complete
        for i, _record, task in record_read_tasks:
            read_start = time.time()
            await task
            read_time = time.time() - read_start
            data_read_times.append(read_time)
            print(f"  - Record {i} data retrieval: {read_time:.4f}s")

    avg_read_time = sum(data_read_times) / len(data_read_times) if data_read_times else 0
    read_time = time.time() - read_start_time
    print(f"6. Record retrieval and reads: {read_time:.4f}s (avg data read: {avg_read_time:.4f}s)")

    # --- Overall Performance Summary ---
    total_time = time.time() - total_start_time

    print("\nPerformance Summary:")
    print(f"  Total runtime: {total_time:.4f}s")
    print(f"  Records requested: {total_records}")
    print(f"  Records completed: {completed_records}")
    print(f"  Records filtered: {filtered_records}")
    print(f"  Records failed: {failed_records}")
    print(f"  Throughput: {total_records/total_time:.2f} records/second (wall clock)")
    print(f"  Average processing time: {processing_time/total_records*1000:.2f}ms per record")
    print(f"  Average data read time: {avg_read_time*1000:.2f}ms per record")

    # Basic verification
    assert retrieved_master.completed_record_count == completed_records
    assert retrieved_master.filtered_record_count == filtered_records
    assert retrieved_master.failed_record_count == failed_records

    # Performance expectation
    assert total_time < 300, f"Performance test took too long: {total_time:.2f}s"


@pytest.mark.asyncio
async def test_high_concurrency():
    """Test the storage layer with high concurrency specifically."""
    # This test runs with significantly higher concurrency to stress-test
    # the SQLite handler's ability to handle concurrent write requests

    storage_instance = LocalStorage(f"file://{TEST_DB_DIR}_high_concurrency")
    await storage_instance.setup()
    try:
        # Use high concurrency (50+ concurrent operations)
        await test_realistic_workflow(
            storage_instance,
            total_records=500,
            batch_size=1,  # 1 record per job = 500 jobs for maximum concurrency
            concurrency=50,
            complexity="small",  # Small data for speed
            use_batch=False,  # Don't use batch to test concurrent operations
        )
    finally:
        await storage_instance.close()
        if os.path.exists(f"{TEST_DB_DIR}_high_concurrency"):
            shutil.rmtree(f"{TEST_DB_DIR}_high_concurrency")


@pytest.mark.asyncio
async def test_batch_performance():
    """Test the performance impact of batch operations."""
    storage_instance = LocalStorage(f"file://{TEST_DB_DIR}_batch_test")
    await storage_instance.setup()
    try:
        # Test with batch operations enabled
        await test_realistic_workflow(
            storage_instance,
            total_records=500,
            batch_size=10,  # Higher batch size for batch operations
            concurrency=10,
            complexity="small",
            use_batch=True,  # Use batch operations
        )
    finally:
        await storage_instance.close()
        if os.path.exists(f"{TEST_DB_DIR}_batch_test"):
            shutil.rmtree(f"{TEST_DB_DIR}_batch_test")


@pytest.mark.asyncio
async def test_read_performance():
    """Test the performance of reading all completed records from a project.

    This test:
    1. Creates a project with a significant number of records (default 500)
    2. Marks most of them as completed
    3. Performs 5 iterations of reading all completed records and their data
    4. Reports average read times and throughput
    """
    # Configuration
    total_records = 500  # Can be adjusted
    complexity = "small"  # Use small data for faster test setup

    print(f"\nRunning read performance test with {total_records} total records")

    # Setup test database
    test_dir = f"{TEST_DB_DIR}_read_perf"
    storage_instance = LocalStorage(f"file://{test_dir}")

    try:
        # Clean start
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        os.makedirs(test_dir, exist_ok=True)

        await storage_instance.setup()

        # Setup phase - create project and records
        print("Setting up test data...")
        setup_start = time.time()

        # Create project
        project = Project(project_id=str(uuid.uuid4()), name="Read Performance Test Project", description="Project for testing read performance")
        await storage_instance.save_project(project)

        # Create master job
        master_job_id = str(uuid.uuid4())
        config_data = {"generator": "qa_pair_generator", "parameters": {"total_records": total_records, "complexity": complexity}}
        config_ref = storage_instance.generate_request_config_path(master_job_id)
        await storage_instance.save_request_config(config_ref, config_data)

        # Define the output schema for QA data
        output_schema = {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question text"},
                "answer": {"type": "string", "description": "The answer text"},
                "created_at": {"type": "string", "format": "date-time"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                        "category": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "required": ["question", "answer"],
        }

        master_job = GenerationMasterJob(
            master_job_id=master_job_id,
            project_id=project.project_id,
            name="Read Performance Test",
            status="running",
            request_config_ref=config_ref,
            output_schema=output_schema,
            storage_uri=storage_instance._metadata_handler.db_path.replace("/metadata.db", ""),
            target_record_count=total_records,
        )
        await storage_instance.log_master_job_start(master_job)

        # Create a single job for all records (for simplicity)
        job_id = str(uuid.uuid4())
        run_config = {"test_type": "read_performance"}
        run_config_str = json.dumps(run_config)
        job = GenerationJob(
            job_id=job_id,
            master_job_id=master_job_id,
            status="pending",
            worker_id="read-perf-worker",
            run_config=run_config_str,
            run_config_hash=hashlib.sha256(run_config_str.encode()).hexdigest(),
        )
        await storage_instance.log_execution_job_start(job)

        # Create and save all records with random data
        records = []
        completed_count = 0
        filtered_count = 0
        failed_count = 0

        # Use batch save for better setup performance
        for i in range(total_records):
            record_uid = str(uuid.uuid4())
            record = Record(record_uid=record_uid, job_id=job_id, master_job_id=master_job_id, status="pending")

            # Make most records completed (85%), some filtered (10%), some failed (5%)
            rand_val = random.random()
            if rand_val < 0.85:  # 85% completed
                record_data = generate_qa_data(i, complexity)
                output_ref = await storage_instance.save_record_data(record.record_uid, master_job_id, job_id, record_data)
                record.status = "completed"
                record.output_ref = output_ref
                completed_count += 1
            elif rand_val < 0.95:  # 10% filtered
                record.status = "filtered"
                record.error_message = "Filtered for test"
                filtered_count += 1
            else:  # 5% failed
                record.status = "failed"
                record.error_message = "Failed for test"
                failed_count += 1

            record.end_time = datetime.datetime.now(datetime.timezone.utc)
            records.append(record)

        # Save all records in batch
        if hasattr(storage_instance._metadata_handler, "batch_save_records"):
            await storage_instance._metadata_handler.batch_save_records(records)
        else:
            for record in records:
                await storage_instance.log_record_metadata(record)

        # Complete the job
        job_counts = {"completed": completed_count, "filtered": filtered_count, "duplicate": 0, "failed": failed_count}
        now = datetime.datetime.now(datetime.timezone.utc)
        await storage_instance.log_execution_job_end(job_id, "completed", job_counts, now, now)

        # Complete the master job
        summary = {
            "completed": completed_count,
            "filtered": filtered_count,
            "duplicate": 0,
            "failed": failed_count,
            "total_requested": total_records,
            "total_processed": total_records,
        }
        await storage_instance.log_master_job_end(master_job_id, "completed", summary, now, now)

        setup_time = time.time() - setup_start
        print(f"Setup completed in {setup_time:.2f}s")
        print(f"Created {total_records} records ({completed_count} completed, {filtered_count} filtered, {failed_count} failed)")

        # Read performance test - run 5 iterations
        iterations = 5
        metadata_times = []
        data_times = []
        total_times = []

        print("\nStarting read performance test (5 iterations):")

        for iteration in range(1, iterations + 1):
            iter_start = time.time()

            # Step 1: Get all completed records metadata
            meta_start = time.time()
            completed_records = await storage_instance.get_records_for_master_job(master_job_id, status_filter=["completed"])
            meta_time = time.time() - meta_start

            # Verify we got the expected number of records
            assert len(completed_records) == completed_count

            # Step 2: Read all record data
            data_start = time.time()
            data_read_tasks = []

            for record in completed_records:
                if record.output_ref:
                    data_read_tasks.append(storage_instance.get_record_data(record.output_ref))

            # Read all data concurrently
            await asyncio.gather(*data_read_tasks)
            data_time = time.time() - data_start

            # Calculate timing for this iteration
            iter_time = time.time() - iter_start

            # Store times
            metadata_times.append(meta_time)
            data_times.append(data_time)
            total_times.append(iter_time)

            # Print iteration results
            print(f"  Iteration {iteration}:")
            print(f"    Metadata retrieval: {meta_time:.4f}s ({len(completed_records)} records, {meta_time/len(completed_records)*1000:.2f}ms per record)")
            print(f"    Data retrieval: {data_time:.4f}s ({len(data_read_tasks)} records, {data_time/len(data_read_tasks)*1000:.2f}ms per record)")
            print(f"    Total: {iter_time:.4f}s (throughput: {len(completed_records)/iter_time:.2f} records/second)")

        # Calculate and print averages
        avg_meta_time = sum(metadata_times) / len(metadata_times)
        avg_data_time = sum(data_times) / len(data_times)
        avg_total_time = sum(total_times) / len(total_times)

        print("\nRead Performance Summary (averages over 5 iterations):")
        print(f"  Records retrieved: {completed_count}")
        print(f"  Average metadata retrieval time: {avg_meta_time:.4f}s ({avg_meta_time/completed_count*1000:.2f}ms per record)")
        print(f"  Average data retrieval time: {avg_data_time:.4f}s ({avg_data_time/completed_count*1000:.2f}ms per record)")
        print(f"  Average total time: {avg_total_time:.4f}s")
        print(f"  Average throughput: {completed_count/avg_total_time:.2f} records/second")

    finally:
        # Clean up
        await storage_instance.close()
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    """Run directly for easier testing outside pytest."""
    # Parse command line arguments
    args = parse_args()

    # Use the arguments to configure the test
    TEST_DB_DIR = args.db_dir

    # Check if we should run the read performance test instead of the workflow test
    if args.read_performance:
        asyncio.run(test_read_performance())
    else:
        # Run the regular workflow test
        async def run_test():
            storage_instance = LocalStorage(f"file://{TEST_DB_DIR}")
            await storage_instance.setup()
            try:
                await test_realistic_workflow(
                    storage_instance,
                    total_records=args.total_records,
                    batch_size=args.batch_size,
                    concurrency=args.concurrency,
                    complexity=args.complexity,
                    use_batch=args.use_batch,
                )
            finally:
                await storage_instance.close()
                if os.path.exists(TEST_DB_DIR):
                    shutil.rmtree(TEST_DB_DIR)

        asyncio.run(run_test())
