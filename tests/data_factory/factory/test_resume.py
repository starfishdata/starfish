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
# async def test_case_keyboard_interrupt():
#     """Test handling of keyboard interrupt (Ctrl+C)"""
#     @data_factory(max_concurrency=2)
#     async def test_interrupt(city_name, num_records_per_city):
#         try:
#             #await asyncio.sleep(1)  # Simulate long-running task
#             return await mock_llm_call(city_name, num_records_per_city)
#         except asyncio.CancelledError:
#             raise KeyboardInterrupt()

#     async def interrupt_after_delay():
#         await asyncio.sleep(1)
#         # Get the current task and cancel it
#         for task in asyncio.all_tasks():
#             if task.get_name() == 'test_interrupt_task':
#                 task.cancel()
#                 break

#     # Create and name the main task
#     main_task = asyncio.create_task(
#         test_interrupt.run(
#             city_name=["SF", "Shanghai", "yoyo"] * 20,
#             num_records_per_city=1
#         ),
#         name='test_interrupt_task'
#     )

#     # Start the interrupt task
#     asyncio.create_task(interrupt_after_delay())

#     # Verify the task was interrupted
#     with pytest.raises(KeyboardInterrupt):
#         await main_task


# @pytest.mark.asyncio
# async def test_case_keyboard_interrupt(monkeypatch):
#     """Test handling of keyboard interrupt (Ctrl+C)"""
#     @data_factory(max_concurrency=2)
#     async def test_interrupt(city_name, num_records_per_city):
#         await asyncio.sleep(1)  # Simulate long-running task
#         return await mock_llm_call(city_name, num_records_per_city)

#     # Create a flag to track if we've interrupted
#     interrupted = False

#     async def mock_sleep(duration):
#         nonlocal interrupted
#         if not interrupted:
#             await original_sleep(1)  # Allow some initial processing
#             interrupted = True
#             raise KeyboardInterrupt()
#         # After interrupt, use the real sleep
#         return await original_sleep(duration)

#     # Store the original sleep function
#     original_sleep = asyncio.sleep
#     # Replace asyncio.sleep with our mock
#     monkeypatch.setattr(asyncio, 'sleep', mock_sleep)

#     with pytest.raises(KeyboardInterrupt):
#         await test_interrupt.run(
#             city_name=["SF", "Shanghai", "yoyo"] * 20,
#             num_records_per_city=1
#         )
