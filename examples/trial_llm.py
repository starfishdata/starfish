

from typing import Callable, Dict, List, Any, Union
from starfish.utils.data_factory import data_factory
from starfish.utils.job_manager import JobManager
from starfish.utils.event_loop import run_in_event_loop
from starfish.core.structured_llm import get_structured_llm, StructuredLLM

async def run_workflow(llm: StructuredLLM, city_name: str):
    model_response = await llm.run(city_name=city_name)
    return model_response.data

#-> List[Dict]
#@data_factory(storage_option='filesystem', batch_size=2)
async def generate_city_info(cities: List[str], num_facts: int, llms: List[StructuredLLM]) :
    """Sample workflow processing cities in batches"""
    cities_info = []
    for city in cities:
        model_response = await llms[0].run(city_name=city)
        facts = model_response.data
        validation = await llms[1].run(data=facts)
        cities_info.append({
            "city": city,
            "facts": facts,
            "validation": validation.data
        })
    return cities_info

# manager could be a singleton for user to reuse
manager = JobManager(data_factory(storage_option='filesystem', batch_size=2), rate_limit=5)
cities = ["new york", "los angeles", "chicago"]  # your city list

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

            

# Process with rate limiting and retries
results = manager.execute_with_retry(generate_city_info, cities=cities, num_facts=3, llms=[first_llm, validation_llm])

# Get job status
print(manager.get_job_status())

# Get cached batches
print(manager.get_cached_batches())
