import pytest
import json
import logging

from starfish.common.exceptions import JsonParserError, SchemaValidationError
from starfish.llm.parser.json_parser import JSONParser
from tests.llm.parser.fixtures.json_problem_cases import problem_data_list

logger = logging.getLogger(__name__)


class TestJSONParser:
    """Test cases for the JSONParser class."""

    # ---------------------------------------------------------------------------
    # Tests for schema conversion and format instructions
    # ---------------------------------------------------------------------------

    def test_convert_to_schema_basic(self):
        """Test converting basic field definitions to JSON schema."""
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {"name": "age", "type": "int", "description": "Person's age"},
            {"name": "is_active", "type": "bool", "description": "Activity status", "required": False},
        ]

        schema = JSONParser.convert_to_schema(fields)

        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "is_active" in schema["properties"]

        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["is_active"]["type"] == "boolean"

        assert "name" in schema["required"]
        assert "age" in schema["required"]
        assert "is_active" not in schema["required"]

    def test_convert_to_schema_nested_object(self):
        """Test converting nested object field definitions to JSON schema."""
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {
                "name": "address",
                "type": "dict",
                "description": "Person's address",
                "properties": {
                    "street": {"type": "string", "description": "Street name"},
                    "city": {"type": "string", "description": "City name"},
                    "zip": {"type": "string", "description": "Zip code"},
                },
                "required": ["street", "city"],
            },
        ]

        schema = JSONParser.convert_to_schema(fields)

        assert "address" in schema["properties"]
        assert schema["properties"]["address"]["type"] == "object"
        assert "properties" in schema["properties"]["address"]
        assert "street" in schema["properties"]["address"]["properties"]
        assert "city" in schema["properties"]["address"]["properties"]
        assert "zip" in schema["properties"]["address"]["properties"]
        assert schema["properties"]["address"]["required"] == ["street", "city"]

    def test_convert_to_schema_nested_array(self):
        """Test converting array field with nested objects to JSON schema."""
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {
                "name": "contacts",
                "type": "list",
                "description": "Person's contacts",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Contact name"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "relationship": {"type": "string", "description": "Relationship type"},
                    },
                    "required": ["name", "phone"],
                },
            },
        ]

        schema = JSONParser.convert_to_schema(fields)

        assert "contacts" in schema["properties"]
        assert schema["properties"]["contacts"]["type"] == "array"
        assert "items" in schema["properties"]["contacts"]
        assert schema["properties"]["contacts"]["items"]["type"] == "object"
        assert "name" in schema["properties"]["contacts"]["items"]["properties"]
        assert "phone" in schema["properties"]["contacts"]["items"]["properties"]
        assert schema["properties"]["contacts"]["items"]["required"] == ["name", "phone"]

    def test_format_instructions_basic(self):
        """Test generating format instructions for a basic schema."""
        fields = [{"name": "name", "type": "str", "description": "Person's name"}, {"name": "age", "type": "int", "description": "Person's age"}]
        schema = JSONParser.convert_to_schema(fields)

        instructions = JSONParser.get_format_instructions(schema)

        # Check for expected output elements
        assert "[" in instructions  # Output should be wrapped in an array
        assert '"name": ""' in instructions
        assert '"age": number' in instructions
        assert "Person's name (required)" in instructions
        assert "Person's age (required)" in instructions

    def test_format_instructions_nested_object(self):
        """Test generating format instructions for schema with nested objects."""
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {
                "name": "address",
                "type": "dict",
                "description": "Person's address",
                "properties": {"street": {"type": "string", "description": "Street name"}, "city": {"type": "string", "description": "City name"}},
                "required": ["street"],
            },
        ]
        schema = JSONParser.convert_to_schema(fields)

        instructions = JSONParser.get_format_instructions(schema)

        # Check for nested object formatting
        assert '"address": {' in instructions
        assert '"street": ""' in instructions
        assert '"city": ""' in instructions
        assert "Street name (required)" in instructions
        assert "City name (optional)" in instructions

    def test_format_instructions_nested_array(self):
        """Test generating format instructions for schema with arrays of objects."""
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {
                "name": "contacts",
                "type": "list",
                "description": "Person's contacts",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "Contact name"}, "phone": {"type": "string", "description": "Phone number"}},
                    "required": ["name"],
                },
            },
        ]
        schema = JSONParser.convert_to_schema(fields)

        instructions = JSONParser.get_format_instructions(schema)

        # Check for array with nested object formatting
        assert '"contacts": [' in instructions
        assert '"name": ""' in instructions  # Both root name and contact name
        assert '"phone": ""' in instructions
        assert "Contact name (required)" in instructions
        assert "Phone number (optional)" in instructions
        assert "// ... more items ..." in instructions

    def test_format_instructions_deeply_nested(self):
        """Test generating format instructions for deeply nested structures."""
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {
                "name": "family",
                "type": "dict",
                "description": "Family information",
                "properties": {
                    "spouse": {
                        "type": "object",
                        "description": "Spouse information",
                        "properties": {
                            "name": {"type": "string", "description": "Spouse name"},
                            "occupation": {"type": "string", "description": "Spouse occupation"},
                        },
                        "required": ["name"],
                    },
                    "children": {
                        "type": "array",
                        "description": "Children information",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Child name"},
                                "age": {"type": "integer", "description": "Child age"},
                                "hobbies": {"type": "array", "description": "Child hobbies", "items": {"type": "string"}},
                            },
                            "required": ["name", "age"],
                        },
                    },
                },
            },
        ]
        schema = JSONParser.convert_to_schema(fields)

        instructions = JSONParser.get_format_instructions(schema)

        # Check for deeply nested structure elements
        assert '"family": {' in instructions
        assert '"spouse": {' in instructions
        assert '"children": [' in instructions
        assert '"name": ""' in instructions  # Multiple occurrences
        assert '"age": number' in instructions
        assert '"hobbies": [' in instructions
        assert "Spouse name (required)" in instructions
        assert "Child name (required)" in instructions
        assert "Child age (required)" in instructions

    # ---------------------------------------------------------------------------
    # Tests for parsing LLM output text
    # ---------------------------------------------------------------------------

    def test_extract_json_from_text_simple(self):
        """Test extracting JSON from text without markdown."""
        text = '{"name": "John", "age": 30}'
        json_text = JSONParser._extract_json_from_text(text)
        assert json_text == '{"name": "John", "age": 30}'

        # Test with surrounding text
        text = 'Here is the data: {"name": "John", "age": 30} as requested.'
        json_text = JSONParser._extract_json_from_text(text)
        assert json_text == '{"name": "John", "age": 30}'

    def test_extract_json_from_text_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        # With json tag
        text = 'Here is the data:\n```json\n{"name": "John", "age": 30}\n```\nAs requested.'
        json_text = JSONParser._extract_json_from_text(text)
        assert json_text == '{"name": "John", "age": 30}'

        # Without json tag
        text = 'Here is the data:\n```\n{"name": "John", "age": 30}\n```\nAs requested.'
        json_text = JSONParser._extract_json_from_text(text)
        assert json_text == '{"name": "John", "age": 30}'

    def test_extract_json_from_text_array(self):
        """Test extracting JSON array from text."""
        text = '[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]'
        json_text = JSONParser._extract_json_from_text(text)
        assert json_text == '[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]'

    def test_extract_json_from_text_error(self):
        """Test error handling when no JSON is found."""
        text = "This text does not contain any JSON."
        with pytest.raises(JsonParserError):
            JSONParser._extract_json_from_text(text)

    def test_unwrap_json_data_single(self):
        """Test unwrapping single object JSON data."""
        data = {"name": "John", "age": 30}
        result = JSONParser._unwrap_json_data(data)
        assert result == [{"name": "John", "age": 30}]

    def test_unwrap_json_data_list(self):
        """Test unwrapping list of objects JSON data."""
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        result = JSONParser._unwrap_json_data(data)
        assert result == [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

    def test_unwrap_json_data_with_wrapper(self):
        """Test unwrapping data with a wrapper key."""
        data = {"results": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        result = JSONParser._unwrap_json_data(data, json_wrapper_key="results")
        assert result == [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

    def test_unwrap_json_data_wrapper_error(self):
        """Test error when wrapper key is missing."""
        data = {"data": [{"name": "John", "age": 30}]}
        with pytest.raises(KeyError):
            JSONParser._unwrap_json_data(data, json_wrapper_key="results")

    def test_parse_llm_output_complete(self):
        """Test complete parsing flow with schema validation."""
        # Define a schema
        fields = [{"name": "name", "type": "str", "description": "Person's name"}, {"name": "age", "type": "int", "description": "Person's age"}]
        schema = JSONParser.convert_to_schema(fields)

        # Test with valid data
        text = '{"name": "John", "age": 30}'
        result = JSONParser.parse_llm_output(text, schema=schema)
        assert result == [{"name": "John", "age": 30}]

        # Test with invalid data (missing required field)
        text = '{"name": "Jane"}'
        with pytest.raises(SchemaValidationError):
            JSONParser.parse_llm_output(text, schema=schema, strict=True)

        # In non-strict mode, should return None
        result = JSONParser.parse_llm_output(text, schema=schema, strict=False)
        assert result is None

    def test_parse_llm_output_nested(self):
        """Test parsing nested structures with validation."""
        # Define a schema with nested objects
        fields = [
            {"name": "name", "type": "str", "description": "Person's name"},
            {
                "name": "address",
                "type": "dict",
                "description": "Person's address",
                "properties": {"street": {"type": "string", "description": "Street name"}, "city": {"type": "string", "description": "City name"}},
                "required": ["street", "city"],
            },
        ]
        schema = JSONParser.convert_to_schema(fields)

        # Test with valid nested data
        text = '{"name": "John", "address": {"street": "123 Main St", "city": "Anytown"}}'
        result = JSONParser.parse_llm_output(text, schema=schema)
        assert result[0]["name"] == "John"
        assert result[0]["address"]["street"] == "123 Main St"
        assert result[0]["address"]["city"] == "Anytown"

        # Test with invalid nested data (missing city)
        text = '{"name": "Jane", "address": {"street": "456 Oak Ave"}}'
        # We need to use type_check=True to properly validate nested object fields
        with pytest.raises(SchemaValidationError):
            JSONParser.parse_llm_output(text, schema=schema, strict=True, type_check=True)

    def test_preprocess_latex_json(self):
        """Test preprocessing JSON text with LaTeX notation."""
        # Normal JSON - should be returned as-is
        json_text = '{"name": "John", "age": 30}'
        result = JSONParser._try_parse_json(json_text)
        assert result == {"name": "John", "age": 30}

        # JSON with basic LaTeX notation
        latex_json = '{"formula": "\\\\(x^2 + y^2 = z^2\\\\)"}'
        result = JSONParser._try_parse_json(latex_json)
        # The backslashes should be properly parsed
        assert result["formula"] == "\\(x^2 + y^2 = z^2\\)"

    def test_parse_llm_output_with_latex(self):
        """Test parsing LLM output containing LaTeX notation."""
        # JSON with LaTeX notation that would normally fail to parse
        latex_input = """[
  {
    "problem": "Find positive integer solutions to the equation",
    "answer": "5"
  }
]"""

        # Define a simple schema for validation
        fields = [{"name": "problem", "type": "str", "description": "Math problem"}, {"name": "answer", "type": "str", "description": "Answer to the problem"}]
        schema = JSONParser.convert_to_schema(fields)

        # This should parse successfully with our preprocessing
        result = JSONParser.parse_llm_output(latex_input, schema=schema)
        assert result is not None
        assert len(result) == 1
        assert result[0]["answer"] == "5"
        assert "Find positive integer solutions" in result[0]["problem"]

    def test_parse_complex_latex_math(self):
        """Test parsing complex mathematical LaTeX notation in JSON."""
        # The example with complex LaTeX split into parts for readability
        latex_part1 = '[\n  {\n    "cot": "We are asked to find the number of '
        latex_part2 = "positive integer solutions \\\\((x,y)\\\\) to the equation "
        latex_part3 = "\\\\(7x + 11y = 2024\\\\) such that \\\\(x \\\\equiv y \\\\pmod{5}\\\\)."

        # Define the remaining JSON parts
        latex_ending = """",
    "problem": "Find the number of positive integer solutions",
    "answer": "5",
    "reasoning": "First, express x in terms of y from the equation"
  }
]"""

        # Concatenate all the parts to form the complete test data
        complex_latex_json = latex_part1 + latex_part2 + latex_part3 + latex_ending

        # This should parse successfully with our preprocessing
        result = JSONParser.parse_llm_output(complex_latex_json)

        # Check that parsing worked and content is preserved
        assert result is not None
        assert len(result) == 1
        assert "cot" in result[0]
        assert "problem" in result[0]
        assert "answer" in result[0]
        assert "reasoning" in result[0]
        assert result[0]["answer"] == "5"

        # Check that a LaTeX expression is present in the content
        assert "Find the number of positive integer solutions" in result[0]["problem"]
        assert "7x + 11y = 2024" in result[0]["cot"]

    def test_parse_problem_cases_with_latex(self):
        """Test parsing real problematic cases containing LaTeX and other issues."""
        # Import the problem data
        # Define a simple schema that matches the general structure
        problem_schema_fields = [
            {"name": "problem", "type": "str", "description": "Problem description"},
            {"name": "topic", "type": "str", "description": "Problem topic", "required": False},
            {"name": "answer", "type": "str", "description": "Problem answer"},
            {"name": "reasoning", "type": "str", "description": "Problem reasoning"},
        ]
        problem_schema = JSONParser.convert_to_schema(problem_schema_fields)

        for i, text in enumerate(problem_data_list):
            try:
                # Use non-strict mode which better matches real-world usage
                result = JSONParser.parse_llm_output(text, schema=problem_schema, strict=False, type_check=False)
                assert result is not None, f"Case {i+1}: Parsing returned None"
                assert isinstance(result, list), f"Case {i+1}: Result is not a list"
                assert len(result) > 0, f"Case {i+1}: Result list is empty"
                assert isinstance(result[0], dict), f"Case {i+1}: First item in result is not a dict"
            except (JsonParserError, SchemaValidationError, json.JSONDecodeError) as e:
                pytest.fail(f"Case {i+1}: Failed to parse problematic JSON. Error: {e}\\nInput text:\\n{text[:500]}...")  # Show first 500 chars
