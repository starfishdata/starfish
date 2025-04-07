
from typing import Callable, Dict, List, Any, Union
from starfish.utils.data_factory import data_factory
from starfish.utils.job_manager import JobManager
from starfish.utils.event_loop import run_in_event_loop
from starfish.core.structured_llm import  StructuredLLM

#-> List[Dict] job hooks hook-up

# Add callback for error handling
def handle_error(err_str: str):
    print(f"Error occurred: {err_str}")

# is this record or job complete?

async def handle_record_complete(data: Any, state: Dict[str, Any]):
    print(f"Record complete: {data}")

async def handle_duplicate_record(data: Any, state: Dict[str, Any]):
    print(f"Record duplicated: {data}")

@data_factory(storage='local',max_concurrency=50, state = {}, on_record_complete=[handle_record_complete, handle_duplicate_record], on_record_error=[handle_error])
async def get_city_info_wf(city_name, region_code):
    structured_llm = StructuredLLM(
        model_name="openai/gpt-4o-mini",
        prompt="Facts about city {{city_name}} in region {{region_code}}.",
        output_schema=[{'name': 'question', 'type': 'str'}, 
                    {'name': 'answer', 'type': 'str'}],
        model_kwargs={"temperature": 0.7}
    )
    output = await structured_llm.run(city_name=city_name, region_code=region_code)
    return output.data


# Execute with batch processing
# results = generate_city_info(
#     cities=["Paris", "Tokyo", "New York", "London"],
#     num_facts=3
# )


results = get_city_info_wf.run(
    data = [
    {'city_name': 'Berlin'}, 
    {'city_name': 'Rome'}
],
    region_code = ['DE', 'IT'],
    city_name = 'Beijing', ### Overwrite the data key
    #num_records_per_city = 3
)