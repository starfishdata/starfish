from starfish import data_factory, StructuredLLM
from starfish.components.prepare_topic import generate_topics
from typing import Optional, List, Dict, Any
from starfish.common.logger import get_logger
import math

logger = get_logger(__name__)


def calculate_balanced_distribution(target_records: int, max_per_subtopic: int = 10) -> Dict[str, int]:
    """
    Calculate a balanced distribution of topics, subtopics, and records.

    Rules:
    1. If <= 10 records: 1 topic, 1 subtopic, X records
    2. If > 10 records: Balance topics and subtopics, maximize records per subtopic
    3. Prefer higher records per subtopic, then better balance, then fewer API calls

    Args:
        target_records: Number of records to generate
        max_per_subtopic: Maximum records per subtopic (default: 10)

    Returns:
        Dict with num_topics, subtopics_per_topic, records_per_subtopic, total_subtopics, api_calls
    """

    # Simple case: small numbers
    if target_records <= max_per_subtopic:
        return {
            "num_topics": 1,
            "subtopics_per_topic": 1,
            "records_per_subtopic": target_records,
            "total_subtopics": 1,
            "api_calls": 3,  # 1 + 1 topic + 1 subtopic
        }

    best_distribution = None

    # Try different records per subtopic (prioritize higher numbers first)
    for records_per_subtopic in range(max_per_subtopic, 0, -1):
        # Calculate how many subtopics we need
        total_subtopics_needed = math.ceil(target_records / records_per_subtopic)

        # Find all factor pairs of total_subtopics_needed
        factors = []
        for num_topics in range(1, int(math.sqrt(total_subtopics_needed)) + 1):
            if total_subtopics_needed % num_topics == 0:
                subtopics_per_topic = total_subtopics_needed // num_topics
                factors.append((num_topics, subtopics_per_topic))

        # Also add the reverse factors
        for num_topics, subtopics_per_topic in factors[:]:
            if (subtopics_per_topic, num_topics) not in factors:
                factors.append((subtopics_per_topic, num_topics))

        # Find the best factor pair for this records_per_subtopic
        best_for_this_level = None
        min_balance_score = float("inf")
        min_api_calls = float("inf")

        for num_topics, subtopics_per_topic in factors:
            total_generated = num_topics * subtopics_per_topic * records_per_subtopic

            # Calculate API calls: 1 + num_topics + total_subtopics
            api_calls = 1 + num_topics + (num_topics * subtopics_per_topic)

            if total_generated >= target_records:
                # Balance score: prefer closer to equal topics and subtopics
                balance_score = abs(num_topics - subtopics_per_topic)

                is_better = False

                # For this level of records_per_subtopic, prefer balance first, then API calls
                if balance_score < min_balance_score:
                    is_better = True
                elif balance_score == min_balance_score and api_calls < min_api_calls:
                    is_better = True

                if is_better:
                    min_balance_score = balance_score
                    min_api_calls = api_calls
                    best_for_this_level = {
                        "num_topics": num_topics,
                        "subtopics_per_topic": subtopics_per_topic,
                        "records_per_subtopic": records_per_subtopic,
                        "total_subtopics": num_topics * subtopics_per_topic,
                        "api_calls": api_calls,
                    }

        # Since we try higher records_per_subtopic first, take the first perfect solution
        if best_for_this_level and (num_topics * subtopics_per_topic * records_per_subtopic == target_records):
            best_distribution = best_for_this_level
            break
        elif best_for_this_level and best_distribution is None:
            best_distribution = best_for_this_level

    return best_distribution


@data_factory(max_concurrency=20)
async def verify_queries_with_llm(model_name, query, answer, api_contract):
    """
    Uses an LLM to verify if generated queries match the API contract.

    Args:
        query_answer_pairs (list): A list of dictionaries with 'query' and 'answer' keys.
        api_contract (dict): The API contract dictionary.
    """

    semantic_checker_llm = StructuredLLM(
        model_name=model_name,  # You can choose a different model
        prompt="""Given this API contract: {{api_contract}}, this query: '{{query}}', and this answer: '{{answer}}'.
        Here is an example for your reference ONLY - DO NOT compare it directly with the given query/answer pair:
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
        A valid query/answer pair would be something similar to this:
        Query: "Could you check the weather in Nairobi, Buenos Aires, and Bangkok? Also, I'd like to know the wind speed in Jakarta."
        Answer: [
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Nairobi'}},
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Buenos Aires','units': 'Fahrenheit'}},
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Bangkok'}},
            {'name': 'weather_api.get_current_weather', 'arguments': {'location': 'Jakarta'}}
        ]

        Analyze the following aspects of the given query/answer pair (NOT the example):
        1. Does the query contain all necessary information that the API contract requires?
        2. Does the answer contain the correct number of function calls matching the requests in the query?
        3. Does each function call in the answer:
            - Use the correct API name as specified in the contract?
            - Include all required parameters from the API contract (optional parameters are not necessary)?
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
                # logger.info(f"Query: '{query}'")
                # logger.info(f"Answer: '{answer}'")
                # logger.info(f"  semantic checker Result: {match_status}")
                # logger.info(f"  Reason: {reason}")
                reason_arr.append(reason)
                if match_status == "Yes":
                    semantic_checker_passed = True
            else:
                logger.info(f"Query: '{query}' - LLM semantic checker failed.")
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
    user_instruction = f"{user_instruction}, generate sub topic on the topic of {topic}"
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
async def generator_query_answer(model_name, api_contract: dict, topic: str, num_records: int = 5):
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
        model_name=model_name,
        # model_name="openai/gpt-4o-mini",
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
        num_records=num_records,
    )
    return query_answer_pairs.data


@data_factory(max_concurrency=30)
async def update_query_answer(model_name: str, api_contract: dict, query, answer, failed_reason):
    update_answer_generator_prompt = """
        Given this API contract: {{api_contract}}, this query: '{{query}}', and this answer: '{{answer}}'. It failed the format or semantic check 
        with this reason {{reason}}.
        Please update the answer to pass the check. Here is the requirement

        Ensure the query be the same:
        Ensure the answer:
            − Is a list of function calls in JSON format.
            − The length of the answer list should be equal to the number of requests in the query
            − Can solve all the requests in the query effectively
 
        Based on these examples and the above instructions, update query and answer pair for the functions '{{func_name}}'.
        The detailed functions description is as follows:
        {{func_desc}}
        The detailed functions paramters is as follows, the generated outputs shall have some records having the optional parameters:
        {{func_params}}
        The output MUST strictly adhere to the following JSON format, and NO other text MUST be included:
        [
            {
                "query": "The generated query.",
                "answer": [
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
        
        update the answer to pass the check.
    """

    query_answer_updator = StructuredLLM(
        model_name=model_name,
        prompt=update_answer_generator_prompt,
        output_schema=[
            {"name": "query", "type": "str"},
            {"name": "answer", "type": "str"},
        ],
        model_kwargs={"temperature": 0.7},
    )
    query_answer_pairs = await query_answer_updator.run(
        api_contract=api_contract,
        func_name=api_contract["name"],
        func_desc=api_contract["description"],
        func_params=api_contract["parameters"],
        num_records=1,
        query=query,
        answer=answer,
        reason=failed_reason,
    )
    return query_answer_pairs.data
