

from typing import Callable, Dict, List, Any, Union
from starfish.utils.data_factory import data_factory

#-> List[Dict]
@data_factory(storage_option='filesystem', batch_size=2)
async def generate_city_info(cities: List[str], num_facts: int) :
    """Sample workflow processing cities in batches"""
    return [
        {"city": city, "facts": [f"Fact {i+1} about {city}" for i in range(num_facts)]}
        for city in cities
    ]

# Add callback for error handling
def handle_error(e: Exception):
    print(f"Error occurred: {str(e)}")

generate_city_info.add_callback('on_error', handle_error)

# Execute with batch processing
results = generate_city_info(
    cities=["Paris", "Tokyo", "New York", "London"],
    num_facts=3
)


# import nest_asyncio
# nest_asyncio.apply()

# from starfish.utils.event_loop import run_in_event_loop

# from starfish.core.structured_llm import get_structured_llm, StructuredLLM

# async def run_workflow(llm: StructuredLLM):
#     model_response = await llm.run(city_name="New York")
#     return model_response.data


# first_llm = get_structured_llm(
#     model_name="openai/gpt-4o-mini",
#     prompt="Facts about city {{city_name}}.",
#     output_schema=[{'name': 'question', 'type': 'str'}, 
#                    {'name': 'answer', 'type': 'str'}],
#     model_kwargs={"temperature": 0.7}
# )

# #model_response = run_in_event_loop(run_workflow(first_llm))


# # ### Local model
# local_model_llm = get_structured_llm(
#     model_name="ollama/gemma3:1b",
#     prompt="Facts about city {{city_name}}.",
#     output_schema=[{'name': 'question', 'type': 'str'}, 
#                    {'name': 'answer', 'type': 'str'}],
#     model_kwargs={"temperature": 0.7}
# )

# model_response = run_in_event_loop(run_workflow(local_model_llm))

# print(model_response)