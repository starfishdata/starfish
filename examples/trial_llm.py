import random
import asyncio
from typing import Any, Dict
from starfish.core.llm.structured_llm import StructuredLLM
from starfish.core.data_factory.factory import data_factory
from starfish.core.data_factory.constants import STATUS_COMPLETED, STATUS_DUPLICATE, STATUS_FILTERED, STATUS_FAILED, STORAGE_TYPE_IN_MEMORY, STORAGE_TYPE_LOCAL
from starfish.core.data_factory.state import MutableSharedState
from starfish.core.common.logger import get_logger
logger = get_logger(__name__)
# Add callback for error handling
# todo state is a class with thread safe dict
async def handle_error(data: Any, state: MutableSharedState):
    logger.error(f"Error occurred: {data}")
    return STATUS_FAILED

async def handle_record_complete(data: Any, state: MutableSharedState):
    print(f"Record complete: {data}")

    await state.set("completed_count",  1)
    await state.data
    await state.update({"completed_count": 2})
    return STATUS_COMPLETED

async def handle_duplicate_record(data: Any, state: MutableSharedState):
    logger.debug(f"Record duplicated: {data}")
    await state.set("completed_count",  1)
    await state.data
    await state.update({"completed_count": 2})
    #return STATUS_DUPLICATE
    if random.random() < 0.9:
        return STATUS_COMPLETED
    return STATUS_DUPLICATE

async def mock_llm_call(city_name, num_records_per_city, fail_rate=0.5, sleep_time=0.1):
    await asyncio.sleep(sleep_time)

    if random.random() < fail_rate:
        logger.debug(f"  {city_name}: Failed!")
        raise ValueError(f"Mock LLM failed to process city: {city_name}")
    
    logger.debug(f"{city_name}: Successfully processed!")

    result = [{"answer": f"{city_name}_{random.randint(1, 5)}"} for _ in range(num_records_per_city)]
    return result

@data_factory(
    storage=STORAGE_TYPE_LOCAL, max_concurrency=50, initial_state_values={}, on_record_complete=[handle_record_complete, handle_duplicate_record], 
    on_record_error=[handle_error],show_progress=True
)
async def get_city_info_wf(city_name, region_code):
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

    #return output.data
    return await mock_llm_call(city_name, num_records_per_city=3, fail_rate=0.5, sleep_time=0.01)


# Execute with batch processing
# results = generate_city_info(
#     cities=["Paris", "Tokyo", "New York", "London"],
#     num_facts=3
# )

# run re_run  dry_run
user_case = "run"
if user_case == "run":
    results = get_city_info_wf.run(
        #data=[{"city_name": "Berlin"}, {"city_name": "Rome"}],
        #[{"city_name": "Berlin"}, {"city_name": "Rome"}],
    city_name=["San Francisco", "New York", "Los Angeles"]*10,
    region_code=["DE", "IT", "US"]*10,
        # city_name="Beijing",  ### Overwrite the data key
        # num_records_per_city = 3
    )
elif user_case == "dry_run":    
    results = get_city_info_wf.dry_run(
        #data=[{"city_name": "Berlin"}, {"city_name": "Rome"}],
        #[{"city_name": "Berlin"}, {"city_name": "Rome"}],
        city_name=["San Francisco", "New York", "Los Angeles"]*10,
        region_code=["DE", "IT", "US"]*10,
            # city_name="Beijing",  ### Overwrite the data key
            # num_records_per_city = 3
        )
elif user_case == "re_run":
    results = get_city_info_wf.re_run( master_job_id="e342bb94-3784-45c7-beab-4e01cb059f1c")

#logger.info(f"Results: {results}")
    
