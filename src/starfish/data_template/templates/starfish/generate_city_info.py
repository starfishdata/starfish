from pydantic import BaseModel
from starfish import data_factory
from starfish.data_template.template_gen import data_gen_template
from starfish.data_factory.utils.mock import mock_llm_call
import random
from typing import Any, List, Dict, Callable

from starfish.common.logger import get_logger
from starfish.data_factory.constants import (
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STORAGE_TYPE_LOCAL,
)
from starfish.data_factory.factory import data_factory, resume_from_checkpoint
from starfish.data_factory.utils.mock import mock_llm_call
from starfish.data_factory.utils.state import MutableSharedState

logger = get_logger(__name__)


# Define input schema
class CitiInfoGeneratorInput(BaseModel):
    region_code: list[str]
    city_name: list[str]


@data_gen_template.register(
    name="starfish/generate_city_info",
    input_schema=CitiInfoGeneratorInput,
    output_schema=None,
    description="Generates relevant topics for community discussions using AI models",
    author="Your Name",
    starfish_version="0.1.0",
    dependencies=[],
)
def generate_city_info(input_data: dict = {}):
    # city_name = input_data["city_name"]
    # region_code = input_data["region_code"]
    city_name = ["San Francisco", "New York", "Los Angeles"] * 5
    region_code = ["DE", "IT", "US"] * 5

    @data_factory(
        storage=STORAGE_TYPE_LOCAL,
        max_concurrency=50,
        initial_state_values={},
        on_record_complete=[],
        on_record_error=[],
        show_progress=True,
        task_runner_timeout=60,
    )
    async def get_city_info_wf(city_name: List[str], region_code: List[str]) -> List[Dict[str, Any]]:
        """Retrieve information about cities using a workflow.

        Args:
            city_name: Name(s) of the city/cities to get information for
            region_code: Region code(s) associated with the city/cities

        Returns:
            List[Dict[str, Any]]: Processed city information from the mock LLM call
        """
        return await mock_llm_call(city_name, num_records_per_city=1, fail_rate=0.1, sleep_time=2)

    return get_city_info_wf.run(city_name=city_name, region_code=region_code)
