from starfish import data_factory, StructuredLLM
from starfish.components.prepare_topic import prepare_topic
from starfish import data_gen_template
from pydantic import BaseModel

from typing import Optional, List, Union, Dict, Any
import random

from .utils import fetch_values_by_topic, save_value_by_topic


## Pydantic Input Schema
class GenerateByTopicInput(BaseModel):
    """
    Input schema for the generate_by_topic template.

    IMPORTANT: This Pydantic model is the single source of truth for default values.
    The validation and default values are controlled by this model, not the function signature.
    """

    user_instruction: Optional[str] = None
    num_records: Optional[int] = 10
    records_per_topic: int = 10
    topics: Optional[List[Union[str, Dict[str, int]]]] = None
    topic_model_name: str = "openai/gpt-4o-mini"
    topic_model_kwargs: Optional[Dict[str, Any]] = None
    generation_model_name: str = "openai/gpt-4o-mini"
    generation_model_kwargs: Optional[Dict[str, Any]] = None
    output_schema: Optional[Union[List[Dict[str, Any]], Dict[str, Any], type]] = [{"name": "question", "type": "str"}, {"name": "answer", "type": "str"}]
    data_factory_config: Optional[Dict[str, Any]] = {}


## Main
@data_gen_template.register(
    name="starfish/generate_by_topic",
    input_schema=GenerateByTopicInput,
    output_schema=None,
    description="""Generates diverse synthetic data across multiple topics based on user instructions.
                   Automatically creates relevant topics if not provided and handles deduplication across generated content.
                """,
    author="Wendao Liu",
    starfish_version="0.1.3",
    dependencies=[],
    input_example="""{
        "user_instruction": "Generate Q&A pairs about machine learning concepts",
        "num_records": 4,
        "records_per_topic": 2,
        "topics": [
            "supervised learning",
            "unsupervised learning",
            {"reinforcement learning": 3},  # This means generate 3 records for this topic
            "neural networks",
        ],
        "topic_model_name": "openai/gpt-4.1-mini",
        "topic_model_kwargs": {"temperature": 0.7},
        "generation_model_name": "openai/gpt-4.1-mini",
        "generation_model_kwargs": {"temperature": 0.8, "max_tokens": 200},
        "output_schema": [
            {"name": "question", "type": "str"},
            {"name": "answer", "type": "str"},
            {"name": "difficulty", "type": "str"},  # Added an additional field
        ],
        "data_factory_config": {"max_concurrency": 4, "task_runner_timeout": 60 * 2},
    }""",
)
async def generate_by_topic(input_data: GenerateByTopicInput):
    """
    Generates diverse synthetic data across multiple topics based on user instructions and defined output schema.

    If topics are not provided, it automatically generates relevant topics based on the instruction.
    The function reduce deduplication by tracking previously generated examples for each topic and
    avoids repeating similar content.

    The data generation process has two main phases: first, topics are prepared (either using
    provided topics or generating them); second, data is generated for each topic.
    Topics are shuffled to ensure even distribution and better deduplication in the output data.

    Each generated record includes the topic it belongs to.
    """
    topic_list = await prepare_topic(
        topics=input_data.topics,
        num_records=input_data.num_records,
        records_per_topic=input_data.records_per_topic,
        user_instruction=input_data.user_instruction,
        model_name=input_data.topic_model_name,
        model_kwargs=input_data.topic_model_kwargs,
    )
    ## Shuffle the topic list to be more eventually distributed for better deduplication
    random.shuffle(topic_list)

    @data_factory(**input_data.data_factory_config)
    async def batch_generate_record(topic: str):
        ## duplicate_example
        generated_data = fetch_values_by_topic(batch_generate_record.state, topic)
        if generated_data:
            duplicate_example = random.choice(generated_data)
        else:
            duplicate_example = None

        prompt = """
        You are a helpful synthetic data generation assistant. 
        Your task is to generate synthetic data based on the provided information. 

        User instructions are provided:
          - Carefully consider the user instructions
          - Create data that aligns with these instructions
        
        Please generate the synthetic data based on the given information and guidelines.

        here is user_instruction: {{user_instruction}}
        
        please generate sythentic data in this '{{topic}}' topics or themes

        {% if duplicate_example %}
        To avoid duplication, here are samples of existing data and please do not repeat from this: 
          {{duplicate_example}}
        {% endif %}
        """

        generation_llm = StructuredLLM(
            prompt=prompt, model_name=input_data.generation_model_name, model_kwargs=input_data.generation_model_kwargs, output_schema=input_data.output_schema
        )

        generated_response = await generation_llm.run(user_instruction=input_data.user_instruction, topic=topic, duplicate_example=duplicate_example)

        save_value_by_topic(batch_generate_record.state, topic, str(generated_response.data))

        ## Adding topic to the data and there is only one record so it is safe to use index 0
        generated_response.data[0]["topic"] = topic

        return generated_response.data

    data = batch_generate_record.run(topic_list)

    return data
