from starfish import data_factory, StructuredLLM
from starfish.components.prepare_topic import prepare_topic, generate_topics
from starfish.data_factory.utils.state import MutableSharedState
from starfish.data_template.template_gen import data_gen_template
from pydantic import BaseModel

from typing import Optional, List, Union, Dict, Any
import random


## Pydantic Input Schema
class GenerateFuncCallDataSet(BaseModel):
    """
    Input schema for the generate_by_topic template.

    IMPORTANT: This Pydantic model is the single source of truth for default values.
    The validation and default values are controlled by this model, not the function signature.
    """

    user_instruction: Optional[str] = None
    num_records: Optional[int] = 10
    api_contract: Dict[str, Any] = None
    sub_topic_num: int = (5,)
    topics: Optional[List[Union[str, Dict[str, int]]]] = None
    topic_model_name: str = "openai/gpt-4o-mini"
    existing_topics: Optional[list] = []
    topic_model_kwargs: Optional[Dict[str, Any]] = None
    generation_model_name: str = "openai/gpt-4o-mini"
    generation_model_kwargs: Optional[Dict[str, Any]] = None
    output_schema: Optional[Union[List[Dict[str, Any]], Dict[str, Any], type]] = [{"name": "question", "type": "str"}, {"name": "answer", "type": "str"}]
    data_factory_config: Optional[Dict[str, Any]] = {}


# 4. Are there any inconsistencies between the query's intent and the answer's implementation?
@data_factory(max_concurrency=20)
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
        
        Given the API contract as 
        {
            "name": "weather_api.get_current_weather",
            "description": "Retrieves the current weather conditions for a specified location .",
            "parameters": {
                "location": {
                    "type": "string", 
                    "description": "The name of the city or geographic location .",
                    "required": True
                },
                "units": {
                    "type": "string", 
                    "description": "The units for temperature measurement( e.g., 'Celsius', 'Fahrenheit') .", 
                    "required": False
                },
            },
        },
        the valid query/answer pair would be something similar to this, watch for the optional parameters:
        Query: "Could you check the weather in Nairobi, Buenos Aires, and Bangkok? Also, I'd like to know the wind speed in Jakarta."
        Answer: [
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Nairobi'}},
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Buenos Aires','units': 'Fahrenheit'}},
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Bangkok'}},
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Jakarta'}}
        ]

        Analyze the following aspects:
        1. Does the query contain all necessary information that the API contract requires?
        2. Does the answer contain the correct number of function calls matching the requests in the query?
        3. Does each function call in the answer:
            - Use the correct API name as specified in the contract?
            - Include all required parameters from the API contract, the non required prameters is not necessary to include?
            - Use parameter values that semantically match the API contract's parameters description?

        Respond with 'Yes' or 'No', followed by a detailed reason explaining your analysis.
        If 'No', specify which aspect(s) failed and why.""",
        output_schema=[
            {"name": "match", "type": "str"},  # e.g., "Yes" or "No"
            {"name": "reason", "type": "str"},
        ],
        model_kwargs={"temperature": 0.3},  # Lower temperature for more deterministic output
    )

    format_checker_passed = True
    semantic_checker_passed = False
    reason_arr = []
    if query and answer:
        if isinstance(query, str) and isinstance(answer, (list, dict)):
            if isinstance(answer, dict):
                answer = [answer]
            for item in answer:
                # Basic structure validation
                if not isinstance(item, dict):
                    format_checker_passed = False
                    reason_arr.append("Answer items must be dictionaries")
                    continue

                # Required keys check
                if "name" not in item or "arguments" not in item:
                    format_checker_passed = False
                    reason_arr.append("Answer items must contain 'name' and 'arguments' keys")
                    continue

                # Arguments type check
                if not isinstance(item["arguments"], dict):
                    format_checker_passed = False
                    reason_arr.append("Arguments must be a dictionary")
                    continue

                # Function name validation
                if item["name"].strip() != api_contract["name"].strip():
                    format_checker_passed = False
                    reason_arr.append("function name not match with the api_contract")
                    continue

                # Parameter validation
                required_params = {param for param, details in api_contract["parameters"].items() if details.get("required", True)}
                api_params = set(api_contract["parameters"].keys())
                answer_args = set(item["arguments"].keys())

                # Required parameters check
                if not required_params.issubset(answer_args):
                    format_checker_passed = False
                    reason_arr.append(f"Missing required parameters: {required_params - answer_args}")
                    continue

                # Parameter keys validation
                if not answer_args.issubset(api_params):
                    format_checker_passed = False
                    reason_arr.append(f"Arguments {answer_args} must be subset of API parameters {api_params}")
                    continue

                # Type checking for each argument
                for arg_name, arg_value in item["arguments"].items():
                    expected_type = api_contract["parameters"][arg_name]["type"].lower()

                    type_checks = {
                        "string": isinstance(arg_value, str),
                        "number": isinstance(arg_value, (int, float)),
                        "float": isinstance(arg_value, (int, float)),
                        "integer": isinstance(arg_value, int),
                        "boolean": isinstance(arg_value, bool),
                        "array": isinstance(arg_value, list),
                        "object": isinstance(arg_value, dict),
                        "null": arg_value is None,
                    }

                    if not type_checks.get(expected_type, True):
                        format_checker_passed = False
                        reason_arr.append(f"Argument '{arg_name}' should be {expected_type}, got {type(arg_value)}")
                        continue

                # Add custom type checks here if needed
        if format_checker_passed:
            semantic_checker_llm_result = await semantic_checker_llm.run(api_contract=api_contract, query=query, answer=answer)
            if semantic_checker_llm_result and hasattr(semantic_checker_llm_result, "data") and semantic_checker_llm_result.data:
                result = semantic_checker_llm_result.data[0]  # Assuming one output per run
                match_status = result.get("match")
                reason = result.get("reason")
                print(f"Query: '{query}'")
                print(f"Answer: '{answer}'")
                print(f"  semantic checker Result: {match_status}")
                print(f"  Reason: {reason}")
                reason_arr.append(reason)
                if match_status == "Yes":
                    semantic_checker_passed = True
            else:
                print(f"Query: '{query}' - LLM semantic checker failed.")
    return [{"format_checker_passed": format_checker_passed, "semantic_checker_passed": semantic_checker_passed, "reason": "; ".join(reason_arr)}]


@data_factory(max_concurrency=10)
async def generate_sub_topic(
    user_instruction: str,
    num_topics: int,
    topic: str,
    model_name: str = "openai/gpt-4o-mini",
    model_kwargs: Optional[Dict[str, Any]] = None,
    existing_topics: Optional[List[str]] = None,
):
    user_instruction = f"{user_instruction}, generate sub topic based on the topic of {topic}"
    sub_topics = await generate_topics(
        user_instruction=user_instruction, num_topics=num_topics, model_name=model_name, model_kwargs=model_kwargs, existing_topics=existing_topics
    )
    result = [{"topic": topic} for topic in sub_topics]
    return result


# here is an example to follow, giving the function name/description/parameters. watch for the paramter which is optional in {{func_params}}
#             function name as  "weather_api.get_current_weather",
#             function description as "Retrieves the current weather conditions for a specified location .",
#             function parameters as  {
#                 "location": {
#                     "type": "string",
#                     "description": "The name of the city or geographic location .",
#                     "required": True
#                 },
#                 "units": {
#                     "type": "string",
#                     "description": "The units for temperature measurement( e.g., 'Celsius', 'Fahrenheit') .",
#                     "required": False
#                 },
#             },
#             this is the output given the conditions above.
#             {
#                 "query" :  "Could you check the weather in Nairobi, Buenos Aires, and Bangkok? Also, I'd like to know the wind speed in Jakarta.",
#                 "answer" : [
#                     {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Nairobi'}},
#                     {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Buenos Aires'}},
#                     {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Bangkok', "units":"Celsius"}},
#                     {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Jakarta'}}
#                 ]
#             }
@data_factory(max_concurrency=30)
async def generator_query_answer(api_contract: dict, topic: str):
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
        func_name=api_contract["name"],
        func_desc=api_contract["description"] + " in this topic :  " + topic,
        func_params=api_contract["parameters"],
        num_records=1,
    )
    return query_answer_pairs.data


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
async def test_api_contract_workflow(input_data: GenerateFuncCallDataSet):
    api_contract = input_data.api_contract
    sub_topic_num = input_data.sub_topic_num
    num_records = input_data.num_records
    num_topic = num_records // sub_topic_num
    num_records_reminder = num_records % sub_topic_num
    if num_records_reminder > 0:
        num_topic += 1
    user_instruction = api_contract["description"]
    topic_model_name = input_data.topic_model_name
    topic_model_kwargs = input_data.topic_model_kwargs
    generated_topics = await generate_topics(
        user_instruction=user_instruction,
        num_topics=num_topic,
        model_name=topic_model_name,
        model_kwargs=topic_model_kwargs,
        existing_topics=input_data.existing_topics,
    )
    sub_topic_input_data = [{"topic": topic, "user_instruction": user_instruction} for topic in generated_topics]

    all_topics = generate_sub_topic.run(data=sub_topic_input_data, num_topics=sub_topic_num, model_name=topic_model_name, model_kwargs=topic_model_kwargs)
    generator_query_answer_input_data = random.sample(all_topics, num_records)
    query_answer_pairs = generator_query_answer.run(data=generator_query_answer_input_data, api_contract=api_contract)
    check_result = verify_queries_with_llm.run(data=query_answer_pairs, api_contract=api_contract)
    # use index and check_result to filter out the failed dataset and and rerun the process to get the num_records
    # also try using duplicate-examples in the prompt
    return query_answer_pairs
