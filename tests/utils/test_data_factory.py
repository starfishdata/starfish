import pytest
import nest_asyncio
import asyncio
import random

nest_asyncio.apply()
from starfish.common.env_loader import load_env_file
from starfish.utils.data_factory import data_factory

load_env_file()
### Mock LLM call


async def mock_llm_call(city_name, num_records_per_city, fail_rate=0.05, sleep_time=0.01):
    # Simulate a slight delay (optional, feels more async-realistic)
    await asyncio.sleep(sleep_time)

    # 5% chance of failure
    if random.random() < fail_rate:
        print(f"  {city_name}: Failed!") ## For debugging
        raise ValueError(f"Mock LLM failed to process city: {city_name}")
    
    print(f"{city_name}: Successfully processed!") ## For debugging

    result = [f"{city_name}_{random.randint(1, 5)}" for _ in range(num_records_per_city)]
    return result


@pytest.mark.asyncio
async def test_case_1():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.5, sleep_time=1):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test1.run(data=[
        {'city_name': '1. New York'},
        {'city_name': '2. Los Angeles'},
        {'city_name': '3. Chicago'},
        {'city_name': '4. Houston'},
        {'city_name': '5. Miami'}
    ], num_records_per_city=5)
    assert len(result) == 5

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

    with pytest.raises(TypeError):
        test1.run(city=["1. New York", "2. Los Angeles", "3. Chicago", "4. Houston", "5. Miami"], 
                       num_records_per_city=5)

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

    with pytest.raises(Exception):
        test1.run(data=[
            {'city_name': '1. New York'},
            {'city_name': '2. Los Angeles'},
            {'city_name': '3. Chicago'},
            {'city_name': '4. Houston'},
            {'city_name': '5. Miami'}
        ], num_records_per_city=5)

@pytest.mark.asyncio
async def test_case_4():
    """Test if broadcast variables can override kwargs with a single value"""
    @data_factory(max_concurrency=2)
    async def test_func(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test_func.run(
        data=[
            {'city_name': '1. New York'},
            {'city_name': '2. Los Angeles'}
        ],
        city_name='override_city_name',
        num_records_per_city=1
    )
    
    # Verify all results contain the override value
    for res in result:
        assert all('override_city_name' in item for item in res)

@pytest.mark.asyncio
async def test_case_5():
    """Test if broadcast variables can override kwargs with a list of values"""
    @data_factory(max_concurrency=2)
    async def test_func(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test_func.run(
        data=[
            {'city_name': '1. New York'},
            {'city_name': '2. Los Angeles'}
        ],
        city_name=['1. override_city_name', '2. override_city_name'],
        num_records_per_city=1
    )
    
    # Verify each result contains the corresponding override value
    assert all('1. override_city_name' in item for item in result[0])
    assert all('2. override_city_name' in item for item in result[1])

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

    with pytest.raises(TypeError):
        test1.run(data=[
            {'city_name': '1. New York'},
            {'city_name': '2. Los Angeles'},
        ], city_name='override_city_name')

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

    with pytest.raises(TypeError):
        test1.run(data=[
            {'city_name': '1. New York'},
            {'city_name': '2. Los Angeles'},
        ], num_records_per_city=1, random_param='random_param')

@pytest.mark.asyncio
async def test_case_8():
    """Test hooks that change state of workflow
    - Input: List of dicts with city names
    - Hook: test_hook modifies state
    - Expected: State variable should be modified by hook
    """
    async def test_hook(data, state):
        state['variable'] = f'changed_state - {data}'
        return state

    @data_factory(max_concurrency=2, on_record_complete=[test_hook], state={'variable': 'initial_state'})
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=0.05):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    result = test1.run(data=[
        {'city_name': '1. New York'},
        {'city_name': '2. Los Angeles'},
    ], num_records_per_city=1)
    
    assert test1.state['variable'].startswith('changed_state')