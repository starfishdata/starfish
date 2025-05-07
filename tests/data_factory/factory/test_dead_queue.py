import nest_asyncio
import pytest

from starfish.data_factory.factory import data_factory
from starfish.common.env_loader import load_env_file
from starfish.data_factory.utils.mock import mock_llm_call


nest_asyncio.apply()
load_env_file()


@pytest.mark.asyncio
async def test_dead_queue():
    @data_factory(max_concurrency=2)
    async def test1(city_name: str, num_records_per_city: int, fail_rate=0.3, sleep_time=1):
        return await mock_llm_call(city_name, num_records_per_city, fail_rate=fail_rate, sleep_time=sleep_time)

    nums_per_record = 5
    result = test1.run(
        data=[
            {"city_name": "1. New York"},
            {"city_name": "2. Los Angeles"},
            {"city_name": "3. Chicago"},
            {"city_name": "4. Houston"},
            {"city_name": "5. Miami"},
        ],
        num_records_per_city=nums_per_record,
    )

    dead_input_data, dead_input_data_indices = test1.get_input_data_in_dead_queue(), test1.get_index_dead_queue()
    assert len(dead_input_data) == len(dead_input_data_indices)
