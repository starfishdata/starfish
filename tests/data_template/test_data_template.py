import nest_asyncio
import pytest
from pydantic import BaseModel
from starfish.common.env_loader import load_env_file
from starfish.data_template.template_gen import data_gen_template
from starfish.data_template.utils.error import DataTemplateValueError, ImportPackageError
from starfish import StructuredLLM, data_factory

nest_asyncio.apply()
load_env_file()


# Define input schema
class TopicGeneratorInput(BaseModel):
    community_name: str
    seed_topics: list[str]
    num_topics: int
    language: str = "en"


# Define output schema
class TopicGeneratorOutput(BaseModel):
    generated_topics: list[str]
    success: bool
    message: str


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
# @pytest.mark.skip(reason="Skipping this test case as not implementing data_factory decorator outside the function")
async def test_get_datafactory_run():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    get_city_info_wf = data_gen_template.get("starfish/get_city_info_wf")
    results = get_city_info_wf.run(
        city_name=["San Francisco", "New York", "Los Angeles"] * 5,
        region_code=["DE", "IT", "US"] * 5,
    )
    assert len(results) == 15


@pytest.mark.asyncio
async def test_get_run_dependencies_not_met():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    with pytest.raises(ModuleNotFoundError):
        topic_generator = data_gen_template.get("starfish/math_problem_gen_wf")


@pytest.mark.asyncio
async def test_get_run_dependencies_not_met():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    with pytest.raises(ImportPackageError):
        topic_generator = data_gen_template.get("community/topic_generator")


@pytest.mark.asyncio
async def test_get_run_template_Input_Success():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    template = data_gen_template.get("community/topic_generator_success")

    # input_data = TopicGeneratorInput(
    #         community_name="AI Enthusiasts",
    #         seed_topics=["Machine Learning", "Deep Learning"],
    #         num_topics=5
    #     )
    input_data = {"community_name": "AI Enthusiasts", "seed_topics": ["Machine Learning", "Deep Learning"], "num_topics": 1}
    # results = template.run(input_data.model_dump())
    results = template.run(input_data)
    print(results)

    assert len(results.generated_topics) == 3


@pytest.mark.asyncio
async def test_get_run_template_Input_Schema_Not_Match():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    with pytest.raises(DataTemplateValueError) as exc_info:
        topic_generator = data_gen_template.get("community/topic_generator_success_1")

        input_data = TopicGeneratorInput(
            community_name="AI Enthusiasts",
        )
        topic_generator.run(input_data)

    # Assert the error message
    assert "Template community/topic_generator_success_1 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gen_cities_info():
    data_gen_template.list()
    city_name = ["San Francisco", "New York", "Los Angeles"] * 5
    region_code = ["DE", "IT", "US"] * 5
    input_data = {"city_name": city_name, "region_code": region_code}
    template = data_gen_template.get("starfish/generate_city_info")
    results = template.run(input_data)
    assert len(results) == 15


@pytest.mark.asyncio
async def test_api_contract_workflow():
    api_contract = {
        "name": "weather_api.get_current_weather",
        "description": "Retrieves the current weather conditions for a specified location .",
        "parameters": {
            "location": {"type": "string", "description": "The name of the city or geographic location .", "required": True},
            "units": {"type": "string", "description": "The units for temperature measurement( e . g ., ’ Celsius ’, ’ Fahrenheit ’) .", "required": False},
        },
    }

    import re

    def validate_with_regex(input_string, api_contract):
        """
        Validates an input string against an API contract using regular expressions.
        This is a simplified approach and may not handle all cases.

        Args:
            input_string (str): The string to validate.
            api_contract (dict): The API contract dictionary.

        Returns:
            bool: True if the string matches the expected pattern, False otherwise.
        """
        api_name = re.escape(api_contract.get("name", ""))
        required_params = []
        if "parameters" in api_contract and api_contract["parameters"]:
            for param_name, param_details in api_contract["parameters"].items():
                if param_details.get("required", False):
                    required_params.append(re.escape(param_name.strip()))

        # Construct a regex pattern
        # This is a basic pattern that expects the function name followed by
        # parentheses and at least the required parameters in some form.
        # It doesn't deeply parse the parameter values.
        pattern = rf"^{api_name}\s*\("
        if required_params:
            # This part is simplified; a real regex would be more complex
            # to handle different orders and optional parameters.
            pattern += r".*" + r".*".join([rf"{param}\s*=\s*['\"].*?['\"]" for param in required_params]) + r".*"

        pattern += r"\)$"

        # Using re.IGNORECASE to handle variations in casing
        if re.search(pattern, input_string, re.IGNORECASE):
            return True
        else:
            return False

    # Example usage:
    input_string1 = "weather_api.get_current_weather(location='Mumbai')"
    input_string2 = "weather_api.get_current_weather()"  # Missing required parameter
    input_string3 = "get_current_weather(location='London')"  # Incorrect function name
    input_string4 = "weather_api.get_current_weather(location= 'New York', units='Celsius')"  # With optional parameter

    print(f"'{input_string1}' matches: {validate_with_regex(input_string1, api_contract)}")
    print(f"'{input_string2}' matches: {validate_with_regex(input_string2, api_contract)}")
    print(f"'{input_string3}' matches: {validate_with_regex(input_string3, api_contract)}")
    print(f"'{input_string4}' matches: {validate_with_regex(input_string4, api_contract)}")

    # Assuming query_answer_pairs is available from the data_gen_workflow function
    # and api_contract is the dictionary defined in the notebook.
    @data_factory(max_concurrency=2)
    async def verify_queries_with_llm(query, answer, api_contract):
        """
        Uses an LLM to verify if generated queries match the API contract.

        Args:
            query_answer_pairs (list): A list of dictionaries with 'query' and 'answer' keys.
            api_contract (dict): The API contract dictionary.
        """
        format_checker_llm = StructuredLLM(
            model_name="openai/gpt-4o-mini",  # You can choose a different model
            prompt="Given this API contract: {{api_contract}} ,  this query: '{{query}}',  this answer: '{{answer}}'. Does the query/answer align with the required parameters of the API contract? Respond with 'Yes' or 'No', followed by a brief reason.",
            output_schema=[
                {"name": "match", "type": "str"},  # e.g., "Yes" or "No"
                {"name": "reason", "type": "str"},
            ],
            model_kwargs={"temperature": 0.3},  # Lower temperature for more deterministic output
        )

        semantic_checker_llm = StructuredLLM(
            model_name="openai/gpt-4o-mini",  # You can choose a different model
            prompt="Given this API contract: {{api_contract}} ,  this query: '{{query}}',  this answer: '{{answer}}'. Does the query/answer align with the semantic meaning of the API contract? Respond with 'Yes' or 'No', followed by a brief reason.",
            output_schema=[
                {"name": "match", "type": "str"},  # e.g., "Yes" or "No"
                {"name": "reason", "type": "str"},
            ],
            model_kwargs={"temperature": 0.3},  # Lower temperature for more deterministic output
        )

        print(f"Query: '{query}'")
        print(f"Answer: '{answer}'")
        format_checker_passed = False
        semantic_checker_passed = False
        if query and answer:
            format_checker_llm_result = await format_checker_llm.run(api_contract=api_contract, query=query, answer=answer)
            if format_checker_llm_result and hasattr(format_checker_llm_result, "data") and format_checker_llm_result.data:
                result = format_checker_llm_result.data[0]  # Assuming one output per run
                match_status = result.get("match")
                reason = result.get("reason")

                print(f"  format checker Result: {match_status}")
                print(f"  Reason: {reason}")
                if match_status == "Yes":
                    format_checker_passed = True
            else:
                print(f"Query: '{query}' - LLM format checker failed.")
            if validate_with_regex(answer, api_contract=api_contract):
                semantic_checker_llm_result = await semantic_checker_llm.run(api_contract=api_contract, query=query, answer=answer)
                if semantic_checker_llm_result and hasattr(semantic_checker_llm_result, "data") and semantic_checker_llm_result.data:
                    result = semantic_checker_llm_result.data[0]  # Assuming one output per run
                    match_status = result.get("match")
                    reason = result.get("reason")
                    print(f"  semantic checker Result: {match_status}")
                    print(f"  Reason: {reason}")
                    if match_status == "Yes":
                        semantic_checker_passed = True
                else:
                    print(f"Query: '{query}' - LLM semantic checker failed.")
        return [{"format_checker_passed": format_checker_passed, "semantic_checker_passed": semantic_checker_passed}]

    query_answer_generator = StructuredLLM(
        model_name="openai/gpt-4o-mini",
        prompt="Given this {{api_contract}}, generate various queries that might invole this api",
        output_schema=[
            {"name": "query", "type": "str"},
            {"name": "answer", "type": "str"},
        ],
        model_kwargs={"temperature": 0.7},
    )
    query_answer_pairs = await query_answer_generator.run(api_contract=api_contract, num_records=10)
    print(query_answer_pairs.data)
    output = verify_queries_with_llm.run(data=query_answer_pairs.data, api_contract=api_contract)
    print(output)


@pytest.mark.asyncio
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
