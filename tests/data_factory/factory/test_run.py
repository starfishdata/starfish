import nest_asyncio
import pytest
import os

from starfish.data_factory.factory import data_factory
from starfish.common.env_loader import load_env_file
from starfish.data_factory.constants import STATUS_COMPLETED
from starfish.data_factory.utils.errors import InputError, OutputError
from starfish.data_factory.utils.mock import mock_llm_call
from starfish.llm.structured_llm import StructuredLLM

nest_asyncio.apply()
load_env_file()


@pytest.mark.asyncio
async def test_case_1():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=1):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
            {"city_name": "3. Chicago"},
            {"city_name": "4. Houston"},
            {"city_name": "5. Miami"},
        ],
        num_records_per_city=5,
    )
    for item in result:
        assert "job_id" not in item
        assert "master_job_id" not in item
    assert len(result) == 25


@pytest.mark.asyncio
async def test_case_2():
    """Test with kwargs list and broadcast variables
    - Input: city as list (incorrect format)
    - Broadcast: num_records_per_city
    - Expected: TypeError due to incorrect input format
    """

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.5, sleep_time=1):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    with pytest.raises(InputError):
        test1.run(city=["1. New York", "2. Los Angeles", "3. Chicago", "4. Houston", "5. Miami"], num_records_per_city=5)


@pytest.mark.asyncio
async def test_case_3():
    """Test failure handling with 100% failure rate
    - Input: List of dicts with city names
    - Parameters: fail_rate=1 (100% failure)
    - Expected: Exception due to all requests failing
    """

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    with pytest.raises(OutputError):
        test1.run(
            data=[
                {"city_name": "1. New York"},
                {"city_name": "2. Los Angeles"},
                {"city_name": "3. Chicago"},
                {"city_name": "4. Houston"},
                {"city_name": "5. Miami"},
            ],
            num_records_per_city=5,
        )


@pytest.mark.asyncio
async def test_case_4():
    """Test if broadcast variables can override kwargs with a single value"""

    @data_factory(max_concurrency=2)
    async def test_func(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test_func.run(data=[{"city_name": "1. New York"}, {"city_name": "2. Los Angeles"}], city_name="override_city_name", num_records_per_city=1)

    # Verify all results contain the override value
    for item in result:
        assert "override_city_name" in item["answer"]


@pytest.mark.asyncio
async def test_case_5():
    """Test if broadcast variables can override kwargs with a list of values"""

    @data_factory(max_concurrency=2)
    async def test_func(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test_func.run(
        data=[{"city_name": "1. New York"}, {"city_name": "2. Los Angeles"}],
        city_name=["1. override_city_name", "2. override_city_name"],
        num_records_per_city=1,
    )

    # Verify each result contains the corresponding override value
    assert any("1. override_city_name" in item["answer"] or "2. override_city_name" in item["answer"] for item in result)


@pytest.mark.asyncio
async def test_case_6():
    """Test missing required kwargs
    - Input: List of dicts with city names
    - Missing: Required num_records_per_city parameter
    - Expected: TypeError due to missing required parameter
    """

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    with pytest.raises(InputError):
        test1.run(
            data=[
                {"city_name": "1. New York"},
                {"city_name": "2. Los Angeles"},
            ],
            city_name="override_city_name",
        )


@pytest.mark.asyncio
async def test_case_7():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    with pytest.raises(InputError):
        test1.run(
            data=[
                {"city_name": "1. New York"},
                {"city_name": "2. Los Angeles"},
            ],
            num_records_per_city=1,
            random_param="random_param",
        )


@pytest.mark.asyncio
async def test_case_8():
    """Test hooks that change state of workflow
    - Input: List of dicts with city names
    - Hook: test_hook modifies state
    - Expected: State variable should be modified by hook
    """

    def test_hook(data, state):
        state.update({"variable": f"changed_state - {data}"})
        return STATUS_COMPLETED

    @data_factory(max_concurrency=2, on_record_complete=[test_hook], initial_state_values={"variable": "initial_state"})
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
        ],
        num_records_per_city=1,
    )
    state_value = test1.state.get("variable")
    assert state_value.startswith("changed_state")


@pytest.mark.asyncio
async def test_case_dry_run():
    """Test dry_run in workflow"""

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    test1.dry_run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
        ],
        num_records_per_city=1,
    )


@pytest.mark.asyncio
async def test_case_timeout():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    @data_factory(max_concurrency=2, task_runner_timeout=0.01)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    with pytest.raises(OutputError):
        test1.run(
            data=[
                {"city_name": "1. New York"},
                {"city_name": "2. Los Angeles"},
            ],
            num_records_per_city=1,
        )


@pytest.mark.asyncio
async def test_case_job_run_stop_threshold():
    """Test extra parameters not defined in workflow
    - Input: List of dicts with city names
    - Extra: random_param not defined in workflow
    - Expected: TypeError due to unexpected parameter
    """

    @data_factory(max_concurrency=2, job_run_stop_threshold=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
        ],
        num_records_per_city=1,
    )


@pytest.mark.asyncio
async def test_case_reuse_run_different_factory():
    @data_factory(max_concurrency=10)
    async def input_format_mock_llm(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.01)

    @data_factory(max_concurrency=10)
    async def input_format_mock_llm_1(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.01)

    @data_factory(max_concurrency=10)
    async def input_format_mock_llm_2(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.01)

    result = input_format_mock_llm.run(city_name=["SF", "Shanghai"], num_records_per_city=2)
    assert len(result) == 4

    result = input_format_mock_llm_1.run(city_name=["SF", "Shanghai", "yoyo"], num_records_per_city=2)
    assert len(result) == 6

    result = input_format_mock_llm_2.run(city_name=["SF", "Shanghai", "yoyo"] * 20, num_records_per_city=2)
    assert len(result) == 120


@pytest.mark.asyncio
async def test_case_reuse_run_same_factory():
    @data_factory(max_concurrency=10)
    async def input_format_mock_llm(city_name: str, num_records_per_city: int):
        return await mock_llm_call(city_name=city_name, num_records_per_city=num_records_per_city, fail_rate=0.01)

    result = input_format_mock_llm.run(city_name=["SF", "Shanghai"], num_records_per_city=2)
    assert len(result) == 4
    result = input_format_mock_llm.run(city_name=["SF", "Shanghai"], num_records_per_city=2)
    assert len(result) == 4
    result = input_format_mock_llm.run(city_name=["SF", "Shanghai"], num_records_per_city=2)
    assert len(result) == 4


# @pytest.mark.asyncio
# @pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping in CI environment")
# async def test_case_cloudpick():
#     ### Pydantic Issue?
#     from pydantic import BaseModel

#     class MockLLMInput(BaseModel):
#         city_name: str
#         num_records_per_city: int

#     @data_factory(max_concurrency=10)
#     async def test_pydantic_issue(city_name: str, num_records_per_city: int):
#         facts_generator = StructuredLLM(model_name="openai/gpt-4o-mini", output_schema=MockLLMInput, prompt="generate facts about {{city_name}}")

#         response = await facts_generator.run(city_name=city_name, num_records_per_city=num_records_per_city)

#         return response.data

#     result = test_pydantic_issue.run(city_name=["SF", "Shanghai"], num_records_per_city=2)
#     # num of records not used right now
#     assert len(result) == 2
