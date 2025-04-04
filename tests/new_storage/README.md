# Storage Layer Tests

This directory contains tests for the StarFish storage layer implementation.

## Overview

The storage layer is responsible for persisting metadata and data artifacts for synthetic data generation jobs. It provides:

- A pluggable interface for different storage backends
- A hybrid local implementation using SQLite for metadata and JSON files for data
- Comprehensive APIs for storing projects, jobs, and records

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r ../requirements-test.txt
```

### Running the Main Test Script

For a quick verification of functionality, run the main test script:

```bash
python -m tests.new_storage.test_storage_main
```

This script provides a user-friendly overview of the storage layer's functionality by:
1. Creating a test storage in `/tmp/starfish_test_db` (or a custom path via `STARFISH_TEST_DB_DIR` env var)
2. Exercising all major API functions in sequence
3. Verifying data integrity
4. Leaving the files for inspection (unless `STARFISH_TEST_MODE=cleanup` is set)

You can run in full test mode which includes a small performance test:

```bash
STARFISH_TEST_MODE=full python -m tests.new_storage.test_storage_main
```

### Performance Testing

For dedicated performance testing of the storage layer with a larger dataset (1000 records):

```bash
python -m tests.new_storage.local.test_performance
```

This will create 500 execution jobs with 2 records each (1000 total records) and measure the performance of various storage operations.

### Running the Full Test Suite

To run the comprehensive test suite with pytest:

```bash
pytest -xvs tests/new_storage/
```

For just the local storage implementation:

```bash
pytest -xvs tests/new_storage/local/
```

## Test Structure

- `test_storage_main.py`: User-friendly standalone test script
- `local/test_performance.py`: Performance test with 1000 records
- `local/test_local_storage.py`: Comprehensive pytest-based test suite
- `local/test_basic_storage.py`: Simple standalone test script

## Test Database

Tests use separate test databases (by default in `/tmp/starfish_test_*` directories) to avoid interfering with production data.

## Test Coverage

The tests verify:

- Project creation and retrieval 
- Master job lifecycle (creation, status updates, completion)
- Execution job lifecycle (creation, status updates, completion)
- Record storage and retrieval (metadata and data)
- Filtering and pagination of records
- End-to-end workflows
- Performance with varied dataset sizes

## Implementation Details

The local storage implementation uses:
- SQLite for metadata (tables for projects, jobs, and records)
- JSON files for data artifacts (configs and record data)
- WAL mode for SQLite for better concurrency
- Nested directory structure for JSON files based on record IDs 