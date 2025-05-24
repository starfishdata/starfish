import nest_asyncio
import pytest
import os
from starfish.common.env_loader import load_env_file
from starfish import data_gen_template

nest_asyncio.apply()
load_env_file()


@pytest.mark.asyncio
async def test_list():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    result = data_gen_template.list()
    assert len(result) != 0


@pytest.mark.asyncio
async def test_list_detail():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    result = data_gen_template.list(is_detail=True)
    assert len(result) != 0


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping in CI environment")
async def test_get_generate_by_topic_Success():
    data_gen_template.list()
    topic_generator_temp = data_gen_template.get("starfish/generate_by_topic")
    num_records = 20
    input_data = {
        "user_instruction": "Generate Q&A pairs about machine learning concepts",
        "num_records": num_records,
        "records_per_topic": 5,
        "topics": [
            "supervised learning",
            "unsupervised learning",
            {"reinforcement learning": 3},  # This means generate 3 records for this topic
            "neural networks",
        ],
        "topic_model_name": "openai/gpt-4",
        "topic_model_kwargs": {"temperature": 0.7},
        "generation_model_name": "openai/gpt-4",
        "generation_model_kwargs": {"temperature": 0.8, "max_tokens": 200},
        "output_schema": [
            {"name": "question", "type": "str"},
            {"name": "answer", "type": "str"},
            {"name": "difficulty", "type": "str"},  # Added an additional field
        ],
        "data_factory_config": {"max_concurrency": 4, "task_runner_timeout": 60 * 2},
    }
    # results = topic_generator_temp.run(input_data.model_dump())
    results = await topic_generator_temp.run(input_data)

    assert len(results) == num_records


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping in CI environment")
async def test_get_generate_func_call_dataset():
    data_gen_template.list()
    generate_func_call_dataset = data_gen_template.get("starfish/generate_func_call_dataset")
    input_data = {
        "num_records": 4,
        "api_contract": {
            "name": "weather_api.get_current_weather",
            "description": "Retrieves the current weather conditions for a specified location .",
            "parameters": {
                "location": {"type": "string", "description": "The name of the city or geographic location .", "required": True},
                "units": {"type": "string", "description": "The units for temperature measurement( e.g., 'Celsius', 'Fahrenheit') .", "required": False},
            },
        },
        "topic_model_name": "openai/gpt-4",
        "topic_model_kwargs": {"temperature": 0.7},
        "generation_model_name": "openai/gpt-4o-mini",
        "generation_model_kwargs": {"temperature": 0.8, "max_tokens": 200},
        "data_factory_config": {"max_concurrency": 24, "task_runner_timeout": 60 * 2},
    }
    results = await generate_func_call_dataset.run(input_data)

    assert len(results) >= input_data["num_records"]
