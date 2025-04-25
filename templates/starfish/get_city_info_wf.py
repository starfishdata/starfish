# Auto-generated module from template: starfish/get_city_info_wf
from pydantic import BaseModel
from starfish import data_factory
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


def handle_error(data: Any, state: MutableSharedState):
    """Handle error cases during data processing.

    Args:
        data: The data that caused the error
        state: Shared state object for tracking progress

    Returns:
        str: STATUS_FAILED constant
    """
    logger.error(f"Error occurred: {data}")
    return STATUS_FAILED


def handle_record_complete(data: Any, state: MutableSharedState):
    """Handle successful completion of a record.

    Args:
        data: The successfully processed data
        state: Shared state object for tracking progress

    Returns:
        str: STATUS_COMPLETED constant
    """
    # print(f"Record complete: {data}")

    state.set("completed_count", 1)
    state.update({"completed_count": 2})
    return STATUS_COMPLETED


def handle_duplicate_record(data: Any, state: MutableSharedState):
    """Handle duplicate record detection.

    Args:
        data: The duplicate data record
        state: Shared state object for tracking progress

    Returns:
        str: Either STATUS_COMPLETED or STATUS_DUPLICATE based on random chance
    """
    logger.debug(f"Record : {data}")
    state.set("completed_count", 1)
    state.update({"completed_count": 2})
    # return STATUS_DUPLICATE
    if random.random() < 0.9:
        # print("going to return completed")
        return STATUS_COMPLETED
    # print("going to return duplicate")
    return STATUS_DUPLICATE


# Define input schema
class TopicGeneratorInput(BaseModel):
    community_name: str
    seed_topics: list[str]
    num_topics: int
    language: str = "en"


# Define output schema
class TopicGeneratorOutput(BaseModel):
    generated_topics: list[str]
    success: bool
    message: str


@data_factory(
    storage=STORAGE_TYPE_LOCAL,
    max_concurrency=50,
    initial_state_values={},
    on_record_complete=[handle_record_complete, handle_duplicate_record],
    on_record_error=[handle_error],
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
    # structured_llm = StructuredLLM(
    #     model_name="openai/gpt-4o-mini",
    #     prompt="Facts about city {{city_name}} in region {{region_code}}.",
    #     output_schema=[{"name": "question", "type": "str"}, {"name": "answer", "type": "str"}],
    #     model_kwargs={"temperature": 0.7},
    # )
    # output = await structured_llm.run(city_name=city_name, region_code=region_code)
    # validation_llm = StructuredLLM(
    #     model_name='anthropic/claude-3',
    #     prompt='''Analyze these city facts and provide:
    #     1. Accuracy score (0-10)
    #     2. Potential sources for verification
    #     3. Confidence level (0-1)
    #     Facts: {{data}}''',
    #     output_schema=[
    #         {'name': 'accuracy_score', 'type': 'float'},
    #         #{'name': 'sources', 'type': 'List[str]'},
    #         {'name': 'confidence', 'type': 'float'}
    #     ],
    #     #max_tokens=500
    # )
    # output = await validation_llm.run(data=output.data)

    # return output.data
    return await mock_llm_call(city_name, num_records_per_city=3, fail_rate=0.1, sleep_time=2)
