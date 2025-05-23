from starfish.components.prepare_topic import generate_topics
from starfish.data_template.template_gen import data_gen_template
from pydantic import BaseModel

from typing import Optional, Dict, Any
import random

from starfish.data_template.templates.starfish.func_call.utils import (
    generate_sub_topic,
    generator_query_answer,
    update_query_answer,
    verify_queries_with_llm,
    num_records_,
    sub_topic_num,
)
from starfish.common.logger import get_logger

logger = get_logger(__name__)


class ParameterDefinition(BaseModel):
    """
    Pydantic model representing parameter definition in an API contract.
    """

    type: str
    description: str
    required: bool = True


class APIContract(BaseModel):
    """
    Pydantic model representing an API contract structure.
    """

    name: str
    description: str
    parameters: Dict[str, ParameterDefinition]


## Pydantic Input Schema
class GenerateFuncCallDataSet(BaseModel):
    """
    Input schema for the generate_by_topic template.

    IMPORTANT: This Pydantic model is the single source of truth for default values.
    The validation and default values are controlled by this model, not the function signature.
    """

    num_records: Optional[int] = 10
    api_contract: APIContract
    topic_model_name: str = "openai/gpt-4o-mini"
    topic_model_kwargs: Optional[Dict[str, Any]] = None
    generation_model_name: str = "openai/gpt-4o-mini"
    generation_model_kwargs: Optional[Dict[str, Any]] = None
    data_factory_config: Optional[Dict[str, Any]] = {}


@data_gen_template.register(
    name="starfish/generate_func_call_dataset",
    input_schema=GenerateFuncCallDataSet,
    output_schema=None,
    description="""Generates diverse synthetic data across multiple topics based on user instructions.
                   Automatically creates relevant topics if not provided and handles deduplication across generated content.
                """,
    author="Wendao Liu",
    starfish_version="0.1.3",
    dependencies=[],
)
async def api_contract_workflow(input_data: GenerateFuncCallDataSet):
    api_contract = input_data.api_contract.model_dump()
    num_records = input_data.num_records
    records_per_topic = sub_topic_num * num_records_
    num_topic = num_records // records_per_topic
    num_records_reminder = num_records % records_per_topic
    if num_records_reminder > 0 or num_topic == 0:
        num_topic += 1
    user_instruction = api_contract["description"]
    topic_model_name = input_data.topic_model_name
    topic_model_kwargs = input_data.topic_model_kwargs
    generation_model_name = input_data.generation_model_name
    generated_topics = await generate_topics(
        user_instruction=user_instruction,
        num_topics=num_topic,
        model_name=topic_model_name,
        model_kwargs=topic_model_kwargs,
    )
    sub_topic_input_data = [{"topic": topic, "user_instruction": user_instruction} for topic in generated_topics]
    generate_sub_topic.factory.config.update(input_data.data_factory_config)
    all_topics = generate_sub_topic.run(data=sub_topic_input_data, num_topics=sub_topic_num, model_name=topic_model_name, model_kwargs=topic_model_kwargs)
    # generator_query_answer_input_data = random.sample(all_topics, num_records//num_records_)
    generator_query_answer_input_data = all_topics
    generator_query_answer.factory.config.update(input_data.data_factory_config)
    query_answer_pairs = generator_query_answer.run(data=generator_query_answer_input_data, api_contract=api_contract, model_name=generation_model_name)
    verify_queries_with_llm.factory.config.update(input_data.data_factory_config)
    check_result = verify_queries_with_llm.run(data=query_answer_pairs, api_contract=api_contract, model_name=generation_model_name)
    check_result_idx_arr = verify_queries_with_llm.get_index_completed()
    failed_data_set = []
    result = []
    updated_data_set = []
    for i in range(0, len(check_result)):
        item = check_result[i]
        query_answer_pair = query_answer_pairs[check_result_idx_arr[i]]
        if not item["format_checker_passed"] or not item["semantic_checker_passed"]:
            query_answer_pair["failed_reason"] = item["reason"]
            failed_data_set.append(query_answer_pair)
        else:
            result.append(query_answer_pair)

    if len(failed_data_set) > 0:
        update_query_answer.factory.config.update(input_data.data_factory_config)
        updated_data_set = update_query_answer.run(data=failed_data_set, api_contract=api_contract, model_name=generation_model_name)
        check_result = verify_queries_with_llm.run(data=updated_data_set, api_contract=api_contract, model_name=generation_model_name)
        filtered_check_result = [item for item in check_result if not item["format_checker_passed"] or not item["semantic_checker_passed"]]
        if len(filtered_check_result) > 0:
            logger.warning("verify_queries_with_llm promp need improve or the data set need improve")

    result.extend(updated_data_set)
    # also try using duplicate-examples in the prompt
    return result
