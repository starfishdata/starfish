from typing import Any, Dict

from starfish.core.structured_llm import StructuredLLM
from starfish.utils.data_factory import data_factory
from starfish.utils.constants import RECORD_STATUS_COMPLETED, RECORD_STATUS_DUPLICATE, RECORD_STATUS_FILTERED, RECORD_STATUS_FAILED

# Add callback for error handling
async def handle_error(data: Any, state: Dict[str, Any]):
    print(f"Error occurred: {data}")
    return RECORD_STATUS_FAILED

async def handle_record_complete(data: Any, state: Dict[str, Any]):
    print(f"Record complete: {data}")
    return RECORD_STATUS_COMPLETED

async def handle_duplicate_record(data: Any, state: Dict[str, Any]):
    print(f"Record duplicated: {data}")
    #return RECORD_STATUS_DUPLICATE
    return RECORD_STATUS_COMPLETED

@data_factory(
    storage="local", max_concurrency=50, state={}, on_record_complete=[handle_record_complete, handle_duplicate_record], on_record_error=[handle_error]
)
async def get_city_info_wf(city_name, region_code):
    structured_llm = StructuredLLM(
        model_name="openai/gpt-4o-mini",
        prompt="Facts about city {{city_name}} in region {{region_code}}.",
        output_schema=[{"name": "question", "type": "str"}, {"name": "answer", "type": "str"}],
        model_kwargs={"temperature": 0.7},
    )
    output = await structured_llm.run(city_name=city_name, region_code=region_code)
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

    return output.data


# Execute with batch processing
# results = generate_city_info(
#     cities=["Paris", "Tokyo", "New York", "London"],
#     num_facts=3
# )

# return results// not loop forever
results = get_city_info_wf.run(
    #data=[{"city_name": "Berlin"}, {"city_name": "Rome"}],
    #[{"city_name": "Berlin"}, {"city_name": "Rome"}],
    city_name=["San Francisco", "New York", "Los Angeles"],
    region_code=["DE", "IT", "US"],
    # city_name="Beijing",  ### Overwrite the data key
    # num_records_per_city = 3
)
