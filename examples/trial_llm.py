
from typing import Callable, Dict, List, Any, Union
from starfish.utils.data_factory import data_factory
from starfish.utils.job_manager import JobManager
from starfish.utils.event_loop import run_in_event_loop
from starfish.core.structured_llm import get_structured_llm, StructuredLLM

#-> List[Dict]
@data_factory(storage_option='filesystem', batch_size=2)
async def generate_city_info(cities: List[str], num_facts: int) :
    """Sample workflow processing cities in batches"""

    first_llm = get_structured_llm(
        model_name="openai/gpt-4o-mini",
        prompt="Facts about city {{city_name}}.",
        output_schema=[{'name': 'question', 'type': 'str'}, 
                    {'name': 'answer', 'type': 'str'}],
        model_kwargs={"temperature": 0.7}
    )
    # Second LLM: Fact Validation
    validation_llm = get_structured_llm(
        model_name='anthropic/claude-3',
        prompt='''Analyze these city facts and provide:
        1. Accuracy score (0-10)
        2. Potential sources for verification
        3. Confidence level (0-1)
        Facts: {{data}}''',
        output_schema=[
            {'name': 'accuracy_score', 'type': 'float'},
            #{'name': 'sources', 'type': 'List[str]'},
            {'name': 'confidence', 'type': 'float'}
        ],
        #max_tokens=500
    )
    cities_info = []
    for city in cities:
        model_response = await first_llm.run(city_name=city)
        facts = model_response.data
        validation = await validation_llm.run(data=facts)
        cities_info.append({
            "city": city,
            "facts": facts,
            "validation": validation.data
        })
    return cities_info

# Add callback for error handling
def handle_error(err_str: str):
    print(f"Error occurred: {err_str}")

generate_city_info.add_callback('on_error', handle_error)

# Execute with batch processing
results = generate_city_info(
    cities=["Paris", "Tokyo", "New York", "London"],
    num_facts=3
)
