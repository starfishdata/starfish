import nest_asyncio
import pytest

from starfish.data_factory.factory import data_factory
from starfish.common.env_loader import load_env_file
from starfish.data_factory.utils.mock import mock_llm_call


nest_asyncio.apply()
load_env_file()


@pytest.mark.asyncio
async def test_input_output_idx():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """

    @data_factory(max_concurrency=2)
    async def test1(city_name, num_records_per_city, fail_rate=0.1, sleep_time=1):
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
    input_data = test1.get_input_data()
    assert len(input_data) == 5
    idx = test1.get_index(filter="completed")
    assert len(result) == len(idx)
    idx_com = test1.get_index_completed()
    assert len(result) == len(idx_com)
    idx_dup = test1.get_index_duplicate()
    assert len(idx_dup) == 0
    idx_fail = test1.get_index_failed()
    # the failed task can be requeue and become completed
    assert len(idx_fail) + len(idx_com) >= 25
    idx_fil = test1.get_index_filtered()
    assert len(idx_fil) == 0
    completed_data = test1.get_output_data(filter="completed")
    assert len(completed_data) == len(result)
    duplicate_data = test1.get_output_duplicate()
    assert len(duplicate_data) == 0
    completed_data = test1.get_output_completed()
    assert len(completed_data) == len(result)
    filtered_data = test1.get_output_filtered()
    assert len(filtered_data) == 0
    failed_data = test1.get_output_failed()
    assert len(failed_data) + len(completed_data) >= 25
