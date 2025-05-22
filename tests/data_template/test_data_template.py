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


# Here are examples of queries and corresponding answers for similar functions:
# similar functions:
# {{examples}}
@pytest.mark.asyncio
async def test_api_contract_workflow():
    api_contract = {
        "name": "weather_api.get_current_weather",
        "description": "Retrieves the current weather conditions for a specified location .",
        "parameters": {
            "location": {"type": "string", "description": "The name of the city or geographic location .", "required": True},
            "units": {"type": "string", "description": "The units for temperature measurement( e.g., 'Celsius', 'Fahrenheit') .", "required": False},
        },
    }

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

        semantic_checker_llm = StructuredLLM(
            model_name="openai/gpt-4o-mini",  # You can choose a different model
            prompt="""Given this API contract: {{api_contract}}, this query: '{{query}}', and this answer: '{{answer}}'.
            
            Here's an example of a valid query/answer pair:
            Query: "Could you check the weather in Nairobi, Buenos Aires, and Bangkok? Also, I'd like to know the wind speed in Jakarta."
            Answer: [
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Nairobi'}},
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Buenos Aires'}},
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Bangkok'}},
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Jakarta'}}
            ]

            Analyze the following aspects:
            1. Does the query contain all necessary information that the API contract requires?
            2. Does the answer contain the correct number of function calls matching the requests in the query?
            3. Does each function call in the answer:
               - Use the correct API name as specified in the contract?
               - Include all required parameters from the API contract, the non required prameters is not necessary to include?
               - Use parameter values that semantically match the query's requests?
            4. Are there any inconsistencies between the query's intent and the answer's implementation?

            Respond with 'Yes' or 'No', followed by a detailed reason explaining your analysis.
            If 'No', specify which aspect(s) failed and why.""",
            output_schema=[
                {"name": "match", "type": "str"},  # e.g., "Yes" or "No"
                {"name": "reason", "type": "str"},
            ],
            model_kwargs={"temperature": 0.3},  # Lower temperature for more deterministic output
        )

        format_checker_passed = False
        semantic_checker_passed = False
        reason = None
        if query and answer:
            if isinstance(query, str) and isinstance(answer, (list, dict)):
                if isinstance(answer, list):
                    for item in answer:
                        if not isinstance(item, dict):
                            return [{"format_checker_passed": False, "semantic_checker_passed": False, "reason": "Answer items must be dictionaries"}]
                        if "name" not in item or "arguments" not in item:
                            return [
                                {
                                    "format_checker_passed": False,
                                    "semantic_checker_passed": False,
                                    "reason": "Answer items must contain 'name' and 'arguments' keys",
                                }
                            ]
                        if not isinstance(item["arguments"], dict):
                            return [{"format_checker_passed": False, "semantic_checker_passed": False, "reason": "Arguments must be a dictionary"}]
                        if item["name"].strip() != api_contract["name"].strip():
                            return [
                                {"format_checker_passed": False, "semantic_checker_passed": False, "reason": "function name not match with the api_contract"}
                            ]
                        # Check if argument keys match API contract parameters
                        api_params = set(api_contract["parameters"].keys())
                        answer_args = set(item["arguments"].keys())
                        if not answer_args.issubset(api_params):
                            return [
                                {
                                    "format_checker_passed": False,
                                    "semantic_checker_passed": False,
                                    "reason": f"Arguments {answer_args} must be subset of API parameters {api_params}",
                                }
                            ]

            semantic_checker_llm_result = await semantic_checker_llm.run(api_contract=api_contract, query=query, answer=answer)
            if semantic_checker_llm_result and hasattr(semantic_checker_llm_result, "data") and semantic_checker_llm_result.data:
                result = semantic_checker_llm_result.data[0]  # Assuming one output per run
                match_status = result.get("match")
                reason = result.get("reason")
                print(f"Query: '{query}'")
                print(f"Answer: '{answer}'")
                print(f"  semantic checker Result: {match_status}")
                print(f"  Reason: {reason}")
                if match_status == "Yes":
                    semantic_checker_passed = True
            else:
                print(f"Query: '{query}' - LLM semantic checker failed.")
        return [{"format_checker_passed": format_checker_passed, "semantic_checker_passed": semantic_checker_passed, "reason": reason}]

    query_answer_generator_prompt = """
        You are a data labeler. The responsibility for you is to generate a set of diverse queries and corresponding answers for the given functions in JSON format.
        Construct queries and answers that exemplifies how to use these functions in a practical scenario. Include in each query specific, plausible values for each parameter. For instance, if the function requires a date, use a typical and reasonable date.
        Ensure the query:
            − Is clear and concise
            − Contain multiple parallel queries in natural language for the given functions, they could use either the same function with different arguments or different functions
            − Demonstrates typical use cases
            − Includes all necessary parameters in a meaningful way. For numerical parameters, it could be either numerals or words
            − Across a variety level of difficulties, ranging from beginner and advanced use cases
            − The corresponding result's parameter types and ranges match with the functions descriptions.
        Ensure the answer:
            − Is a list of function calls in JSON format.
            − The length of the answer list should be equal to the number of requests in the query
            − Can solve all the requests in the query effectively

        Note that the query could be interpreted as a combination of several independent requests.  
        Based on these examples and the above instructions, generate {{num_records}} diverse query and answer pairs for the functions '{{func_name}}'.
        The detailed functions description is as follows:
        {{func_desc}}
        The detailed functions paramters is as follows, the generated outputs shall have some records having the optional parameters:
        {{func_params}}
        The output MUST strictly adhere to the following JSON format, and NO other text MUST be included:
        [
            {
                "query": "The generated query.",
                "answers": [
                    {
                    "name": "api_name",
                    "arguments": {
                        "arg_name": "value",
                        ... (more arguments as required)
                    }       
                    },
                ... (more API calls as required)
                ]
            }
        ]
        here is an example of the output. watch for the paramter which is optional in {{func_params}}
            Query: "Could you check the weather in Nairobi, Buenos Aires, and Bangkok? Also, I'd like to know the wind speed in Jakarta."
            Answer: [
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Nairobi'}},
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Buenos Aires'}},
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Bangkok', "units":"Celsius"}},
                {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Jakarta'}}
            ]
        Now please generate {{num_records}} diverse query and answer pairs following the above format.
    """
    query_answer_generator = StructuredLLM(
        model_name="openai/gpt-4o-mini",
        prompt=query_answer_generator_prompt,
        output_schema=[
            {"name": "query", "type": "str"},
            {"name": "answer", "type": "str"},
        ],
        model_kwargs={"temperature": 0.7},
    )
    query_answer_pairs = await query_answer_generator.run(
        func_name=api_contract["name"], func_desc=api_contract["description"], func_params=api_contract["parameters"], num_records=5
    )
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


@pytest.mark.asyncio
async def test_get_generate_func_call_dataset():
    data_gen_template.list()
    generate_func_call_dataset = data_gen_template.get("starfish/generate_func_call_dataset")
    input_data = {
        "user_instruction": "Generate Q&A pairs about machine learning concepts",
        "num_records": 5,
        "sub_topic_num": 2,
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
        "generation_model_name": "openai/gpt-4",
        "generation_model_kwargs": {"temperature": 0.8, "max_tokens": 200},
        "data_factory_config": {"max_concurrency": 4, "task_runner_timeout": 60 * 2},
    }
    # results = topic_generator_temp.run(input_data.model_dump())
    results = await generate_func_call_dataset.run(input_data)

    assert len(results) == input_data["num_records"]
