from starfish.core.structured_llm import StructuredLLM
from starfish.common.env_loader import load_env_file
from starfish.common.utils import merge_structured_outputs
from starfish.utils.data_factory import data_factory
from datetime import datetime

load_env_file()


### Mock LLM call
import random
import asyncio

async def mock_llm_call(city_name, num_records_per_city, fail_rate=0.05, sleep_time=0.01):
    # Simulate a slight delay (optional, feels more async-realistic)
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Starting {city_name}, sleep for {sleep_time}s")

    await asyncio.sleep(sleep_time)

    print(f"{city_name}: Successfully processed!") ## For debugging

    # 5% chance of failure
    if random.random() < fail_rate:
        print(f"  {city_name}: Failed!") ## For debugging
        raise ValueError(f"Mock LLM failed to process city: {city_name}")
    
    result = [f"{city_name}_{random.randint(1, 5)}" for _ in range(num_records_per_city)]
    return result


@data_factory(max_concurrency=5)
async def test1(city_name, num_records_per_city, fail_rate = 0.05, sleep_time = 1):
    return await mock_llm_call(city_name, num_records_per_city, fail_rate = fail_rate, sleep_time = sleep_time)

print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Starting test with max_concurrency=5")
data = test1.run(data = [
    {'city_name': '1. New York'},
    {'city_name': '2. Los Angeles'},
    {'city_name': '3. Chicago'},
    {'city_name': '4. Houston'},
    {'city_name': '5. Miami'}
], num_records_per_city=5)

print(data)

print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Finished test")
