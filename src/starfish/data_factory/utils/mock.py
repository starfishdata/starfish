import asyncio
import random

from starfish.common.logger import get_logger

logger = get_logger(__name__)


async def mock_llm_call(city_name, num_records_per_city, fail_rate=0.01, sleep_time=0.5):
    await asyncio.sleep(sleep_time)

    if random.random() < fail_rate:
        logger.debug(f"  {city_name}: Failed!")
        raise ValueError(f"Mock LLM failed to process city: {city_name}")

    logger.debug(f"{city_name}: Successfully processed!")

    result = [{"answer": f"{city_name}_{random.randint(1, 5)}"} for _ in range(num_records_per_city)]
    return result
