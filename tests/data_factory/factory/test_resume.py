import asyncio
import os
import nest_asyncio
import pytest

from starfish.data_factory.factory import data_factory, resume_from_checkpoint
from starfish.common.env_loader import load_env_file
from starfish.data_factory.constants import STATUS_COMPLETED
from starfish.data_factory.utils.errors import InputError, NoResumeSupportError, OutputError
from starfish.data_factory.utils.mock import mock_llm_call
from starfish.llm.structured_llm import StructuredLLM

nest_asyncio.apply()
load_env_file()


@pytest.mark.asyncio
async def test_case_re_run_master_id_not_found():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    with pytest.raises(InputError):
        resume_from_checkpoint("123")


@pytest.mark.asyncio
async def test_case_job_re_run():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    @data_factory(max_concurrency=2, job_run_stop_threshold=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        # global master_job_id
        result = await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)
        # master_job_id = test1.factory.config.master_job_id
        return result

    result = test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
        ],
        num_records_per_city=1,
    )
    assert len(result) == 2
    master_job_id = test1.factory.config.master_job_id
    result = data_factory.resume_from_checkpoint(master_job_id)
    assert len(result) == 2
    result = test1.resume()
    assert len(result) == 2
    result = resume_from_checkpoint(master_job_id)
    assert len(result) == 2
    # data_factory.re


@pytest.mark.asyncio
async def test_case_job_re_run_catch_typeErr():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    @data_factory(max_concurrency=2, job_run_stop_threshold=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        global master_job_id
        result = await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)
        master_job_id = test1.factory.config.master_job_id
        return result

    result = test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
        ],
        num_records_per_city=1,
    )
    master_job_id = test1.factory.config.master_job_id
    result = test1.resume()
    assert len(result) == 2
    # TypeError
    with pytest.raises(NoResumeSupportError):
        data_factory.resume_from_checkpoint(master_job_id)

    with pytest.raises(NoResumeSupportError):
        resume_from_checkpoint(master_job_id)


@pytest.mark.asyncio
async def test_case_reuse_run_same_factory():
    @data_factory(max_concurrency=10)
    async def input_format_mock_llm(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.01)

    result = input_format_mock_llm.run(city_name=["SF", "Shanghai"], num_records_per_city=2)
    assert len(result) == 4

    result = input_format_mock_llm.run(city_name=["SF", "Shanghai", "yoyo"], num_records_per_city=2)
    assert len(result) == 6

    result = input_format_mock_llm.run(city_name=["SF", "Shanghai", "yoyo"] * 20, num_records_per_city=2)
    assert len(result) == 120
    # -- input_format_mock_llm.resume_from_checkpoint()
    data_factory.resume_from_checkpoint(input_format_mock_llm.factory.config.master_job_id)


# @pytest.mark.asyncio
# @pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping in CI environment")
# async def test_case_keyboard_interrupt(monkeypatch):
#     """Test handling of keyboard interrupt (Ctrl+C)"""
#     processed_tasks = 0

#     @data_factory(max_concurrency=2)
#     async def test_interrupt(city_name, num_records_per_city):
#         nonlocal processed_tasks
#         await asyncio.sleep(0.1)  # Simulate processing time
#         processed_tasks += 1
#         return await mock_llm_call(city_name, num_records_per_city)

#     async def mock_sleep(duration):
#         # Allow some tasks to complete before interrupting
#         if processed_tasks < 10:  # Let exactly 2 tasks complete
#             return await original_sleep(duration)
#         raise KeyboardInterrupt()

#     # Store the original sleep function
#     original_sleep = asyncio.sleep
#     # Replace asyncio.sleep with our mock
#     monkeypatch.setattr(asyncio, "sleep", mock_sleep)

#     try:
#         # Run with a limited number of tasks to prevent hanging
#         test_interrupt.run(city_name=["SF", "Shanghai", "yoyo"] * 20, num_records_per_city=1)
#     except KeyboardInterrupt:
#         # Verify some tasks were processed before interrupt
#         assert processed_tasks == 10
#     finally:
#         # Cleanup: restore original sleep function
#         monkeypatch.undo()


@pytest.mark.asyncio
# @pytest.mark.skip("to run later")
async def test_resume_with_paramters():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    @data_factory(max_concurrency=2, job_run_stop_threshold=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        # global master_job_id
        result = await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)
        # master_job_id = test1.factory.config.master_job_id
        return result

    result = test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
        ],
        num_records_per_city=1,
    )
    assert len(result) == 2
    master_job_id = test1.factory.config.master_job_id
    result = data_factory.resume_from_checkpoint(master_job_id, max_concurrency=30)
    assert len(result) == 2
    result = test1.resume(max_concurrency=30)
    assert len(result) == 2
    result = resume_from_checkpoint(master_job_id, max_concurrency=30)
    assert len(result) == 2
