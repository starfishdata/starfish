# from typing import Any, Dict, List
# from unittest.mock import AsyncMock, MagicMock, patch

# import pytest
# from pydantic import BaseModel, ConfigDict

# from starfish.common.exceptions import JsonParserError, SchemaValidationError
# from starfish.common.prompt import PromptManager
# from starfish.common.utils import to_sync
# from starfish.core.structured_llm import LLMResponse, StructuredLLM, get_structured_llm


# class MockResponse:
#     def __init__(self, content: str):
#         self.choices = [MagicMock(message=MagicMock(content=content))]


# class TestSchema(BaseModel):
#     model_config = ConfigDict(arbitrary_types_allowed=True)

#     question: str
#     answer: str


# @pytest.fixture
# def sample_json_schema() -> List[Dict[str, Any]]:
#     return [
#         {"name": "question", "type": "str", "description": "A test question", "required": True},
#         {"name": "answer", "type": "str", "description": "The answer to the question", "required": True},
#     ]


# @pytest.fixture
# def sample_prompt() -> str:
#     return "Generate a question and answer about {{topic}}{% if difficulty %} with difficulty level {{difficulty}}{% endif %}"


# @pytest.fixture
# def mock_llm_response() -> MockResponse:
#     return MockResponse("""[{
#         "question": "What is the capital of France?",
#         "answer": "Paris"
#     }]""")


# @pytest.mark.asyncio
# async def test_structured_llm_initialization(sample_json_schema, sample_prompt):
#     """Test that StructuredLLM initializes correctly."""
#     builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema, model_kwargs={"temperature": 0.7})

#     assert isinstance(builder, StructuredLLM)
#     assert builder.model_name == "openai/gpt-4o-mini"
#     assert builder.model_kwargs == {"temperature": 0.7}
#     assert isinstance(builder.prompt_manager, PromptManager)
#     assert builder.is_pydantic is False
#     assert builder.json_schema is not None


# @pytest.mark.asyncio
# async def test_structured_llm_initialization_with_pydantic(sample_prompt):
#     """Test that StructuredLLM initializes correctly with Pydantic schema."""
#     builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=TestSchema, model_kwargs={"temperature": 0.7})

#     assert isinstance(builder, StructuredLLM)
#     assert builder.is_pydantic is True
#     assert builder.output_schema == TestSchema
#     assert isinstance(builder.prompt_manager, PromptManager)


# @pytest.mark.asyncio
# async def test_structured_llm_direct_call(sample_json_schema, sample_prompt, mock_llm_response):
#     """Test that StructuredLLM can be called directly using __call__."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks
#             mock_call_chat.return_value = mock_llm_response
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(
#                 model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema, model_kwargs={"temperature": 0.7}
#             )

#             # Test direct call using __call__
#             response = await builder(topic="history")

#             # Check that the prompt manager was called with the right parameters
#             mock_get_messages.assert_called_once()
#             call_args = mock_get_messages.call_args[0][0]
#             assert call_args["topic"] == "history"

#             # Check response format
#             assert isinstance(response, LLMResponse)
#             assert response.raw == mock_llm_response
#             assert isinstance(response.data, list)
#             assert len(response.data) == 1
#             assert response.data[0]["question"] == "What is the capital of France?"
#             assert response.data[0]["answer"] == "Paris"


# @pytest.mark.asyncio
# async def test_structured_llm_run_method(sample_json_schema, sample_prompt, mock_llm_response):
#     """Test that StructuredLLM can be called using the run method."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks
#             mock_call_chat.return_value = mock_llm_response
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(
#                 model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema, model_kwargs={"temperature": 0.7}
#             )

#             # Test explicit run method
#             response = await builder.run(topic="science")

#             # Check that the prompt manager was called with the right parameters
#             mock_get_messages.assert_called_once()
#             call_args = mock_get_messages.call_args[0][0]
#             assert call_args["topic"] == "science"

#             # Check response format
#             assert isinstance(response, LLMResponse)
#             assert response.raw == mock_llm_response
#             assert isinstance(response.data, list)
#             assert len(response.data) == 1
#             assert response.data[0]["question"] == "What is the capital of France?"
#             assert response.data[0]["answer"] == "Paris"


# def test_run_sync_method(sample_json_schema, sample_prompt):
#     """Test the synchronous run_sync method."""
#     builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema)

#     # Patch run since that's what run_sync calls under the hood
#     with patch.object(builder, "run") as mock_run:
#         # Setup the mock to return a predefined response
#         mock_response = LLMResponse(
#             raw_response=MockResponse('{"question": "Test?", "answer": "Answer"}'), parsed_data={"question": "Test?", "answer": "Answer"}
#         )
#         mock_run.return_value = mock_response

#         # Call run_sync which should pass through to run
#         result = builder.run_sync(topic="history")

#         # Verify run was called with the right parameters
#         mock_run.assert_called_once_with(topic="history")

#         # Verify the result is the same as what run would return
#         assert result is mock_response


# def test_to_sync_decorator():
#     """Test the to_sync decorator on a simple async function."""

#     async def test_async_func(arg1: str, arg2: str) -> str:
#         return f"{arg1}-{arg2}"

#     # Mock asyncio.run to avoid trying to actually run the event loop
#     with patch("asyncio.run") as mock_run:
#         mock_run.return_value = "hello-world"

#         # Apply the decorator
#         sync_func = to_sync(test_async_func)

#         # Test that the sync function works
#         result = sync_func("hello", "world")
#         assert result == "hello-world"
#         mock_run.assert_called_once()


# @pytest.mark.asyncio
# async def test_structured_llm_with_optional_params(sample_json_schema, sample_prompt, mock_llm_response):
#     """Test that StructuredLLM handles optional parameters in the template."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks
#             mock_call_chat.return_value = mock_llm_response
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema)

#             # Test both required and optional parameters using run method
#             response = await builder.run(topic="science", difficulty="hard")

#             # Check that the prompt manager was called with both parameters
#             mock_get_messages.assert_called_once()
#             call_args = mock_get_messages.call_args[0][0]
#             assert call_args["topic"] == "science"
#             assert call_args["difficulty"] == "hard"


# @pytest.mark.asyncio
# async def test_parsing_error_handling(sample_json_schema, sample_prompt):
#     """Test that StructuredLLM handles parsing errors gracefully in non-strict mode."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks
#             mock_call_chat.return_value = MockResponse("This is not valid JSON")
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema)

#             # Test error handling in non-strict mode
#             response = await builder(topic="history")

#             # Check response structure - data should be None but raw should be available
#             assert isinstance(response, LLMResponse)
#             assert response.raw is not None
#             assert response.data is None


# @pytest.mark.asyncio
# async def test_parsing_error_handling_strict(sample_json_schema, sample_prompt):
#     """Test that StructuredLLM raises errors in strict mode."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks
#             mock_call_chat.return_value = MockResponse("This is not valid JSON")
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema, strict_parsing=True)

#             # Test error handling in strict mode - should raise JsonParserError
#             with pytest.raises(JsonParserError) as excinfo:
#                 await builder(topic="history")

#             # Verify error message
#             assert "Failed to extract JSON" in str(excinfo.value) or "No valid JSON content" in str(excinfo.value)


# @pytest.mark.asyncio
# async def test_schema_validation_error_handling(sample_json_schema, sample_prompt):
#     """Test that StructuredLLM handles schema validation errors gracefully in non-strict mode."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks with invalid schema response
#             invalid_response = MockResponse('{"invalid_field": "value"}')  # Missing required fields
#             mock_call_chat.return_value = invalid_response
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema)

#             # Test schema validation error handling in non-strict mode
#             response = await builder(topic="history")

#             # Check response structure - data should be None but raw should be available
#             assert isinstance(response, LLMResponse)
#             assert response.raw is not None
#             assert response.data is None


# @pytest.mark.asyncio
# async def test_schema_validation_error_handling_strict(sample_json_schema, sample_prompt):
#     """Test that LLMBuilder raises errors on schema validation failures in strict mode."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch.object(PromptManager, "construct_messages") as mock_get_messages:
#             # Setup the mocks with invalid schema response
#             invalid_response = MockResponse('{"invalid_field": "value"}')  # Missing required fields
#             mock_call_chat.return_value = invalid_response
#             mock_get_messages.return_value = [{"role": "system", "content": "Test message"}]

#             builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema, strict_parsing=True)

#             # Test schema validation error handling in strict mode - should raise SchemaValidationError
#             with pytest.raises(SchemaValidationError) as excinfo:
#                 await builder(topic="history")

#             # Verify error details
#             assert "Schema validation failed" in str(excinfo.value)
#             assert excinfo.value.details is not None
#             assert "errors" in excinfo.value.details


# @pytest.mark.asyncio
# async def test_using_complete_data_gen_prompt(sample_json_schema, mock_llm_response):
#     """Test using the data_gen complete prompt directly."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch("starfish.common.prompt.get_prompt") as mock_get_prompt:
#             # Setup the mocks
#             mock_call_chat.return_value = mock_llm_response

#             # Mock the get_prompt to return the data_gen template string
#             data_gen_prompt = """
#             You are a data generation expert. Your primary objective is to create 
#             high-quality synthetic data that strictly adheres to the provided guidelines.
            
#             The user has provided specific instructions for data generation. 
#                 - Carefully analyze the given instructions.
#                 - Ensure the generated data aligns with the specified requirements.
#                 - Maintain accuracy, coherence, and logical consistency.
#             user_instruction: {{user_instruction}}
            
#             {% if good_examples %}
#             The user has provided high-quality reference examples.  
#                 - Identify patterns, structures, and key characteristics from these examples.
#                 - Generate data that maintains a similar style, quality, and relevance.
#                 - Ensure variations while preserving meaningful consistency.
#                 good_examples: {{good_examples}}
#             {% endif %}
            
#             Generate exactly {{num_records}} unique and high-quality synthetic data points.  
#             - Ensure diversity in the dataset while maintaining coherence.
#             - Avoid redundant or repetitive entries.
            
#             Please return data in the following JSON format:    
#                 {{schema_instruction}}
#             """
#             mock_get_prompt.return_value = data_gen_prompt

#             # Create an LLMBuilder using the prompt from get_prompt
#             builder = get_structured_llm(
#                 model_name="openai/gpt-4o-mini",
#                 prompt=mock_get_prompt("data_gen"),  # Use the mock instead of actual get_prompt
#                 output_schema=sample_json_schema,
#             )

#             # Test using run method
#             response = await builder.run(
#                 user_instruction="Generate Q&A pairs about history", num_records=2, schema_instruction="JSON format with question and answer fields"
#             )

#             # Check that get_prompt was called correctly
#             mock_get_prompt.assert_called_once_with("data_gen")

#             # Check response
#             assert isinstance(response, LLMResponse)
#             assert response.raw == mock_llm_response


# @pytest.mark.asyncio
# async def test_using_partial_data_gen_prompt(sample_json_schema, mock_llm_response):
#     """Test using the data_gen partial prompt with StructuredLLM."""
#     with patch("starfish.services.structured_llm.call_chat_model", new_callable=AsyncMock) as mock_call_chat:
#         with patch("starfish.services.structured_llm.get_partial_prompt") as mock_get_partial:
#             # Setup the mocks
#             mock_call_chat.return_value = mock_llm_response

#             # Create a mock prompt manager that will be returned by get_partial_prompt
#             mock_prompt_manager = MagicMock(spec=PromptManager)
#             mock_prompt_manager.construct_messages.return_value = [{"role": "system", "content": "Test data gen message"}]
#             mock_prompt_manager.get_all_variables.return_value = ["topic", "num_records", "schema_instruction"]
#             mock_prompt_manager.get_required_variables.return_value = ["topic", "num_records", "schema_instruction"]
#             mock_prompt_manager.get_optional_variables.return_value = ["good_examples"]

#             mock_get_partial.return_value = mock_prompt_manager

#             # Custom prompt content to use with the partial template
#             template_content = "Generate educational questions about {{topic}}"

#             # Create LLMBuilder with partial prompt template
#             builder = get_structured_llm(
#                 model_name="openai/gpt-4o-mini",
#                 prompt=template_content,
#                 output_schema=sample_json_schema,
#                 prompt_template="data_gen",  # Use data_gen partial template
#             )

#             # Test using direct call
#             response = await builder(topic="history", num_records=2, schema_instruction="JSON format with question and answer fields")

#             # Check that get_partial_prompt was called correctly with data_gen
#             mock_get_partial.assert_called_once_with(prompt_name="data_gen", template_str=template_content)

#             # Check that the prompt manager was used correctly
#             mock_prompt_manager.construct_messages.assert_called_once()

#             # Verify params passed to construct_messages
#             call_args = mock_prompt_manager.construct_messages.call_args[0][0]
#             assert call_args["topic"] == "history"
#             assert call_args["num_records"] == 2

#             # Check response
#             assert isinstance(response, LLMResponse)
#             assert response.raw == mock_llm_response


# @pytest.mark.asyncio
# async def test_prompt_variables_exposure(sample_json_schema, sample_prompt):
#     """Test that the LLMBuilder exposes template variables correctly."""
#     builder = get_structured_llm(model_name="openai/gpt-4o-mini", prompt=sample_prompt, output_schema=sample_json_schema)

#     # Check that variable lists are available
#     assert hasattr(builder, "prompt_variables")
#     assert hasattr(builder, "required_prompt_variables")
#     assert hasattr(builder, "optional_prompt_variables")

#     # Since our sample prompt has "topic" as required and "difficulty" as optional
#     assert "topic" in builder.required_prompt_variables
#     assert "difficulty" in builder.optional_prompt_variables
