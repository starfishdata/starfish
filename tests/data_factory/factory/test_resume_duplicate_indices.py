import pytest
import asyncio
import random
from typing import List, Dict, Any

import nest_asyncio

from starfish.data_factory.factory import data_factory
from starfish.data_factory.constants import IDX, STATUS_COMPLETED
from starfish.common.logger import get_logger
from starfish.data_factory.utils.mock import mock_llm_call
from starfish.common.env_loader import load_env_file

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()
load_env_file()

logger = get_logger(__name__)


class ErrorCollector:
    """Collects errors during test execution and reports them at the end.

    This helps to run through the entire test even when errors are found,
    providing a complete picture of all issues.
    """

    def __init__(self):
        self.errors = []

    def add_error(self, error_msg):
        """Add an error message to the collection"""
        logger.error(f"ERROR DETECTED: {error_msg}")
        self.errors.append(error_msg)

    def add_errors(self, error_list):
        """Add a list of error messages to the collection"""
        for error in error_list:
            self.add_error(error)

    def assert_no_errors(self):
        """Assert that no errors were collected

        If errors were collected, raises an AssertionError with all error messages.
        """
        if self.errors:
            error_report = "\n".join([f"  {i+1}. {err}" for i, err in enumerate(self.errors)])
            raise AssertionError(f"Found {len(self.errors)} errors during test execution:\n{error_report}")


def check_data_index_match(data_factory_runnable):
    """Check if indices in a data factory match the output data.

    Verifies:
    1. Index and data length match
    2. Index values match data index values
    3. No duplicate indices in data

    Args:
        data_factory_runnable: A data factory instance to check

    Returns:
        List[str]: List of error messages, empty if no errors
    """
    errors = []
    index = data_factory_runnable.get_index_completed()
    output = data_factory_runnable.get_output_completed()
    output_index = [int(i["answer"].split(" - ")[0]) for i in output]

    if len(index) != len(output):
        errors.append(f"Index and Data length mismatch! (index: {len(index)}, output: {len(output)})")

    if index != output_index:
        mismatches = [(i, o) for i, o in zip(sorted(index), sorted(output_index)) if i != o]
        if mismatches:
            errors.append(f"Index and Data Index Value mismatch! First few mismatches: {mismatches[:5]}")

    if len(set(output_index)) != len(output_index):
        duplicates = [i for i in output_index if output_index.count(i) > 1]
        errors.append(f"Data has duplicate indices: {list(set(duplicates))}")

    return errors


def check_two_output_match(first_output, second_output):
    """Check if two outputs match.

    Assumptions:
    1. first_output already finished, second_output will have to contain the first_output
    2. each output should be unique and not be running more than once

    Args:
        first_output: First output data to compare
        second_output: Second output data to compare

    Returns:
        List[str]: List of error messages, empty if no errors
    """
    errors = []

    first_output_index = [int(i["answer"].split(" - ")[0]) for i in first_output]
    second_output_index = [int(i["answer"].split(" - ")[0]) for i in second_output]

    # Check 1: Make sure second output contains all indices from first output
    missing_indices = []
    for i in first_output_index:
        if i not in second_output_index:
            missing_indices.append(i)

    if missing_indices:
        errors.append(f"First output indices {missing_indices} MISSING in second output")

    # Check 2: Look for duplicates in both outputs
    if len(set(first_output_index)) != len(first_output_index):
        duplicates = [i for i in first_output_index if first_output_index.count(i) > 1]
        errors.append(f"First output has duplicate indices: {list(set(duplicates))}")

    if len(set(second_output_index)) != len(second_output_index):
        duplicates = [i for i in second_output_index if second_output_index.count(i) > 1]
        errors.append(f"Second output has duplicate indices: {list(set(duplicates))}")

    return errors


def log_check_result(check_function, *args, error_collector=None):
    """Run a check function and log the results

    Args:
        check_function: Function to run
        *args: Arguments to pass to the check function
        error_collector: Optional ErrorCollector to add errors to

    Returns:
        bool: True if check passed, False otherwise
    """
    errors = check_function(*args)
    if errors:
        for error in errors:
            logger.error(f"CHECK FAILED: {error}")
        if error_collector:
            error_collector.add_errors(errors)
        return False
    logger.info("CHECK PASSED")
    return True


def output_stats(output_data, error_collector=None):
    """Display statistics about the output data

    Args:
        output_data: Output data to analyze
        error_collector: Optional ErrorCollector to add errors to
    """
    indices = [int(item["answer"].split(" - ")[0]) for item in output_data]
    unique_indices = set(indices)

    logger.info(f"Output count: {len(indices)}")
    logger.info(f"Unique indices: {len(unique_indices)}")

    if len(indices) != len(unique_indices):
        # Find duplicate indices
        duplicates = {}
        for idx in indices:
            if indices.count(idx) > 1 and idx not in duplicates:
                duplicates[idx] = indices.count(idx)

        error_msg = f"Found {len(duplicates)} indices with duplicates: {duplicates}"
        logger.error(error_msg)
        if error_collector:
            error_collector.add_error(error_msg)

        # Check for missing indices (should be 0-99 for 100 items)
        expected_indices = set(range(100))
        missing = expected_indices - unique_indices
        if missing:
            error_msg = f"Missing indices: {missing}"
            logger.error(error_msg)
            if error_collector:
                error_collector.add_error(error_msg)

    return len(indices) == len(unique_indices)


@pytest.mark.asyncio
async def test_resume_duplicate_indices():
    """Test for the duplicate indices bug during multiple resume operations.

    This test specifically targets the issue where resuming a completed job
    multiple times can result in duplicate indices or mismatched index counts.
    """
    error_collector = ErrorCollector()

    @data_factory(max_concurrency=10)
    async def re_run_mock_llm(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.5)

    # Generate test data: 100 numbered cities
    cities = ["New York", "London", "Tokyo", "Paris", "Sydney"]
    numbered_cities = [f"{i} - {cities[i % len(cities)]}" for i in range(100)]

    # Initial run
    logger.info("STARTING INITIAL RUN")
    re_run_mock_llm_data_1 = re_run_mock_llm.run(city_name=numbered_cities, num_records_per_city=1)

    # Check data integrity after initial run
    log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)

    # First resume
    logger.info("STARTING FIRST RESUME")
    re_run_mock_llm_data_2 = re_run_mock_llm.resume()

    # Check data integrity after first resume
    log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)
    log_check_result(check_two_output_match, re_run_mock_llm_data_1, re_run_mock_llm_data_2, error_collector=error_collector)

    # Second resume
    logger.info("STARTING SECOND RESUME")
    re_run_mock_llm_data_3 = re_run_mock_llm.resume()

    # Check data integrity after second resume
    log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)
    log_check_result(check_two_output_match, re_run_mock_llm_data_2, re_run_mock_llm_data_3, error_collector=error_collector)

    # Third resume
    logger.info("STARTING THIRD RESUME")
    re_run_mock_llm_data_4 = re_run_mock_llm.resume()

    # Check data integrity after third resume
    log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)
    log_check_result(check_two_output_match, re_run_mock_llm_data_3, re_run_mock_llm_data_4, error_collector=error_collector)

    # Assert that no errors were collected
    error_collector.assert_no_errors()


@pytest.mark.asyncio
async def test_resume_already_completed_job():
    """Test for the bug when resuming an already completed job multiple times."""
    error_collector = ErrorCollector()

    @data_factory(max_concurrency=10)
    async def re_run_mock_llm(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.0)

    # Generate test data: 100 numbered cities with no failures
    cities = ["New York", "London", "Tokyo", "Paris", "Sydney"]
    numbered_cities = [f"{i} - {cities[i % len(cities)]}" for i in range(100)]

    # Initial run - should complete all tasks with fail_rate=0
    logger.info("STARTING INITIAL RUN WITH NO FAILURES")
    re_run_mock_llm_data_1 = re_run_mock_llm.run(city_name=numbered_cities, num_records_per_city=1)

    # Verify all 100 tasks completed successfully
    completed_indices = re_run_mock_llm.get_index_completed()
    if len(completed_indices) != 100:
        error_collector.add_error(f"Expected 100 completed tasks, got {len(completed_indices)}")

    log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)

    # Multiple resume cycles on a completely finished job - should not duplicate or miss indices
    for i in range(5):
        logger.info(f"STARTING RESUME #{i+1} OF COMPLETED JOB")
        resume_data = re_run_mock_llm.resume()

        # Check for consistent indices
        log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)

        # Verify output count remains 100
        completed_indices = re_run_mock_llm.get_index_completed()
        if len(completed_indices) != 100:
            error_collector.add_error(f"Expected 100 completed tasks after resume #{i+1}, got {len(completed_indices)}")

        # Verify output consistency
        log_check_result(check_two_output_match, re_run_mock_llm_data_1, resume_data, error_collector=error_collector)

    # Assert that no errors were collected
    error_collector.assert_no_errors()


@pytest.mark.asyncio
@pytest.mark.skip("Skip because case not correct")
async def test_resume_finish_and_repeat():
    """Test that matches the user's specific scenario.

    This test:
    1. Creates a job with 100 records with a 50% failure rate
    2. Runs it and resuming a few times to get close to completion
    3. Forces it to complete (by setting fail_rate=0)
    4. Then performs multiple resume operations on the completed job
    """
    error_collector = ErrorCollector()

    @data_factory(max_concurrency=10)
    async def re_run_mock_llm(city_name: str, num_records_per_city: int, fail_rate: float = 0.5):
        """Modified version of the function to allow controlling the fail rate."""
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=fail_rate)

    # Generate test data: 100 numbered cities
    cities = ["New York", "London", "Tokyo", "Paris", "Sydney"]
    numbered_cities = [f"{i} - {cities[i % len(cities)]}" for i in range(100)]

    # Initial run with 50% failure rate
    logger.info("STARTING INITIAL RUN WITH 50% FAILURE RATE")
    initial_data = re_run_mock_llm.run(city_name=numbered_cities, num_records_per_city=1, fail_rate=0.5)
    initial_completed = len(re_run_mock_llm.get_index_completed())
    logger.info(f"Initial run completed {initial_completed}/100 tasks")

    # A few more resumes to get more completions
    logger.info("RESUMING WITH 50% FAILURE RATE (FIRST)")
    resume1_data = re_run_mock_llm.resume()
    resume1_completed = len(re_run_mock_llm.get_index_completed())
    logger.info(f"After first resume: {resume1_completed}/100 tasks completed")

    logger.info("RESUMING WITH 50% FAILURE RATE (SECOND)")
    resume2_data = re_run_mock_llm.resume()
    resume2_completed = len(re_run_mock_llm.get_index_completed())
    logger.info(f"After second resume: {resume2_completed}/100 tasks completed")

    # Force completion by using a zero failure rate
    logger.info("FORCING COMPLETION WITH 0% FAILURE RATE")
    # can not change fail_rate
    force_complete_data = re_run_mock_llm.resume(fail_rate=0.0)
    force_complete_count = len(re_run_mock_llm.get_index_completed())
    logger.info(f"After forced completion: {force_complete_count}/100 tasks completed")

    # This should be 100 tasks now
    if force_complete_count != 100:
        error_collector.add_error(f"Expected all 100 tasks to complete, got {force_complete_count}")

    log_check_result(check_data_index_match, re_run_mock_llm, error_collector=error_collector)

    # Capture the initial output state
    initial_complete_output = re_run_mock_llm.get_output_completed()
    initial_indices = re_run_mock_llm.get_index_completed()
    output_stats(initial_complete_output, error_collector=error_collector)

    # Now repeatedly resume the finished job multiple times in a row
    previous_output = force_complete_data
    for i in range(10):
        logger.info(f"RESUMING COMPLETED JOB (ITERATION {i+1})")
        resume_data = re_run_mock_llm.resume()

        # Print statistics
        logger.info(f"After resume #{i+1}:")
        output_stats(resume_data, error_collector=error_collector)

        # Check data integrity
        current_indices = re_run_mock_llm.get_index_completed()
        if len(current_indices) != 100:
            error_collector.add_error(f"Index count changed: {len(current_indices)}")

        # Compare with initial indices
        if set(current_indices) != set(initial_indices):
            missing = set(initial_indices) - set(current_indices)
            added = set(current_indices) - set(initial_indices)
            if missing:
                error_collector.add_error(f"Missing indices: {missing}")
            if added:
                error_collector.add_error(f"Added indices: {added}")

        # Verify against previous output
        match_errors = check_two_output_match(previous_output, resume_data)
        if match_errors:
            for error in match_errors:
                error_collector.add_error(f"CONSISTENCY ERROR: {error}")

        previous_output = resume_data

    # Assert that no errors were collected
    error_collector.assert_no_errors()


@pytest.mark.asyncio
@pytest.mark.skip("Skip to update")
async def test_run_consecutive_not_completed():
    """Test that matches the user's specific scenario.

    This test:
    1. Creates a job with 100 records with a 50% failure rate
    2. Runs it and resuming a few times to get close to completion
    3. Forces it to complete (by setting fail_rate=0)
    4. Then performs multiple resume operations on the completed job
    """
    error_collector = ErrorCollector()

    @data_factory(max_concurrency=10)
    async def re_run_mock_llm(city_name: str, num_records_per_city: int, fail_rate: float = 0.5):
        """Modified version of the function to allow controlling the fail rate."""
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=fail_rate)

    # Generate test data: 100 numbered cities
    cities = ["New York", "London", "Tokyo", "Paris", "Sydney"]
    numbered_cities = [f"{i} - {cities[i % len(cities)]}" for i in range(100)]

    # Initial run with 50% failure rate
    logger.info("STARTING INITIAL RUN WITH 100% FAILURE RATE")
    initial_data = re_run_mock_llm.run(city_name=numbered_cities, num_records_per_city=1, fail_rate=0.3)
    initial_completed = len(re_run_mock_llm.get_index_completed())
    logger.info(f"Initial run completed {initial_completed}/100 tasks")

    # A few more resumes to get more completions
    logger.info("RESUMING WITH 100% FAILURE RATE (FIRST)")
    second_data = re_run_mock_llm.run(city_name=numbered_cities, num_records_per_city=1, fail_rate=1.0)
    second_completed = len(re_run_mock_llm.get_index_completed())
    logger.info(f"Initial run completed {second_completed}/100 tasks")
