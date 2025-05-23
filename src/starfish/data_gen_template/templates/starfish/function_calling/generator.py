from starfish import data_gen_template
from starfish.components.prepare_topic import generate_topics
from pydantic import BaseModel

from typing import Optional, Dict, Any
import random

from .utils import (
    generate_sub_topic,
    generator_query_answer,
    update_query_answer,
    verify_queries_with_llm,
    calculate_balanced_distribution,
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

    # Model Configuration
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
    input_example="""{
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
    }""",
)
async def api_contract_workflow(input_data: GenerateFuncCallDataSet):
    api_contract = input_data.api_contract.model_dump()
    num_records = input_data.num_records
    user_instruction = api_contract["description"]
    topic_model_name = input_data.topic_model_name
    topic_model_kwargs = input_data.topic_model_kwargs
    generation_model_name = input_data.generation_model_name

    # Print overall process overview
    print("🌟 Function Calling Dataset Generation Pipeline")
    print("=" * 60)
    print("📋 Process Overview:")
    print("   1. Calculate optimal data distribution")
    print("   2. Generate diverse topics")
    print("   3. Create subtopics for each topic")
    print("   4. Generate query-answer pairs")
    print("   5. Verify and validate generated data")
    print("   6. Regenerate failed cases")
    print("=" * 60)

    # Calculate the balanced distribution using utility function
    distribution = calculate_balanced_distribution(num_records)

    # Extract the calculated values
    num_topics_needed = distribution["num_topics"]
    subtopics_per_topic = distribution["subtopics_per_topic"]
    records_per_subtopic = distribution["records_per_subtopic"]
    total_subtopics = distribution["total_subtopics"]
    total_generation_needed = num_topics_needed * subtopics_per_topic * records_per_subtopic

    print(f"📊 Data Distribution Plan:")
    print(f"   • Requested: {num_records} records")
    print(f"   • Distribution: {num_topics_needed} topics × {subtopics_per_topic} subtopics × {records_per_subtopic} records")
    print(f"   • Total generation: {total_generation_needed} records")
    print(f"   • API calls needed: {distribution['api_calls']}")
    print("")

    # Step 1: Generate Topics
    print("🎯 Step 1: Generating diverse topics...")
    generated_topics = await generate_topics(
        user_instruction=user_instruction,
        num_topics=num_topics_needed,
        model_name=topic_model_name,
        model_kwargs=topic_model_kwargs,
    )
    print(f"   ✅ Generated {len(generated_topics)} topics")
    print("")

    # Step 2: Generate Subtopics
    print("🌿 Step 2: Creating subtopics for each topic...")
    sub_topic_input_data = [{"topic": topic, "user_instruction": user_instruction} for topic in generated_topics]
    generate_sub_topic.factory.config.update(input_data.data_factory_config)
    all_topics = generate_sub_topic.run(data=sub_topic_input_data, num_topics=subtopics_per_topic, model_name=topic_model_name, model_kwargs=topic_model_kwargs)
    print(f"   ✅ Generated {len(all_topics)} subtopics total")
    print("")

    # Step 3: Generate Query-Answer Pairs
    print("💬 Step 3: Generating query-answer pairs...")
    generator_query_answer.factory.config.update(input_data.data_factory_config)
    query_answer_pairs = generator_query_answer.run(
        data=all_topics, api_contract=api_contract, model_name=generation_model_name, num_records=records_per_subtopic
    )
    initial_pairs_count = len(query_answer_pairs)
    print(f"   ✅ Generated {initial_pairs_count} initial query-answer pairs")
    print("")

    # Step 4: Verify and Validate
    print("🔍 Step 4: Verifying data quality...")
    verify_queries_with_llm.factory.config.update(input_data.data_factory_config)
    check_result = verify_queries_with_llm.run(data=query_answer_pairs, api_contract=api_contract, model_name=generation_model_name)
    check_result_idx_arr = verify_queries_with_llm.get_index_completed()

    failed_data_set = []
    result = []

    for i in range(len(check_result)):
        item = check_result[i]
        query_answer_pair = query_answer_pairs[check_result_idx_arr[i]]
        if not item["format_checker_passed"] or not item["semantic_checker_passed"]:
            query_answer_pair["failed_reason"] = item["reason"]
            failed_data_set.append(query_answer_pair)
        else:
            result.append(query_answer_pair)

    passed_count = len(result)
    failed_count = len(failed_data_set)
    print(f"   ✅ Quality check complete: {passed_count} passed, {failed_count} failed")
    print("")

    # Step 5: Regenerate Failed Cases
    if len(failed_data_set) > 0:
        print("🔄 Step 5: Regenerating failed cases...")
        update_query_answer.factory.config.update(input_data.data_factory_config)
        updated_data_set = update_query_answer.run(data=failed_data_set, api_contract=api_contract, model_name=generation_model_name)

        # Verify regenerated data
        check_result = verify_queries_with_llm.run(data=updated_data_set, api_contract=api_contract, model_name=generation_model_name)
        filtered_check_result = [item for item in check_result if not item["format_checker_passed"] or not item["semantic_checker_passed"]]

        regenerated_count = len(updated_data_set)
        still_failed_count = len(filtered_check_result)
        print(f"   ✅ Regenerated {regenerated_count} pairs, {still_failed_count} still failing")

        if still_failed_count > 0:
            logger.warning("Some data still failing after regeneration - prompts may need improvement")

        result.extend(updated_data_set)
    else:
        print("✨ Step 5: No failed cases to regenerate - all data passed validation!")
        print("")

    # Trim to requested amount if needed
    if len(result) > num_records:
        result = random.sample(result, num_records)
        print(f"📎 Trimmed to requested {num_records} records")
    elif len(result) < num_records:
        print(f"⚠️  Generated {len(result)} records (less than requested {num_records}) due to quality filtering")
    else:
        print(f"🎯 Perfect! Generated exactly {len(result)} records as requested")

    print("")
    print("🎉 Generation Complete!")
    print("=" * 60)
    print(f"📈 Final Results:")
    print(f"   • Records generated: {len(result)}")
    print(f"   • Success rate: {len(result)}/{initial_pairs_count} ({len(result)/initial_pairs_count*100:.1f}%)")
    print(f"   • Distribution used: {num_topics_needed}T × {subtopics_per_topic}S × {records_per_subtopic}R")
    print("")
    print("⭐ If you found this helpful, please consider starring our repo!")
    print("   Your support means the world to us! 🌟")
    print("=" * 60)

    return result
