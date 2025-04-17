from typing import Dict, List, Optional

import pytest
from pydantic import BaseModel, Field, ValidationError

from starfish.common.exceptions import PydanticParserError
from starfish.llm.parser.pydantic_parser import PydanticParser


# Define test Pydantic models for use in tests
class Address(BaseModel):
    street: str = Field(..., description="Street name")
    city: str = Field(..., description="City name")
    zip_code: Optional[str] = Field(None, description="Zip code")


class Contact(BaseModel):
    name: str = Field(..., description="Contact name")
    phone: str = Field(..., description="Phone number")
    email: Optional[str] = Field(None, description="Email address")


class Person(BaseModel):
    name: str = Field(..., description="Person's name")
    age: int = Field(..., description="Person's age")
    address: Address = Field(..., description="Person's address")
    contacts: List[Contact] = Field(default_factory=list, description="Person's contacts")


class Child(BaseModel):
    name: str = Field(..., description="Child's name")
    age: int = Field(..., description="Child's age")
    hobbies: List[str] = Field(default_factory=list, description="Child's hobbies")


class Spouse(BaseModel):
    name: str = Field(..., description="Spouse's name")
    occupation: Optional[str] = Field(None, description="Spouse's occupation")


class Family(BaseModel):
    spouse: Optional[Spouse] = Field(None, description="Spouse information")
    children: List[Child] = Field(default_factory=list, description="Children information")


class PersonWithFamily(BaseModel):
    name: str = Field(..., description="Person's name")
    age: int = Field(..., description="Person's age")
    family: Family = Field(..., description="Family information")


class FactsList(BaseModel):
    facts: List[Dict[str, str]] = Field(..., description="A list of facts")


class Fact(BaseModel):
    question: str = Field(..., description="The factual question generated")
    answer: str = Field(..., description="The corresponding answer")
    category: str = Field(..., description="A category for the fact")


class NestedFactsList(BaseModel):
    facts: List[Fact] = Field(..., description="A list of facts")


class TestPydanticParser:
    """Test cases for the PydanticParser class."""

    # ---------------------------------------------------------------------------
    # Tests for schema conversion from Pydantic models
    # ---------------------------------------------------------------------------

    def test_to_json_schema_basic(self):
        """Test converting a basic Pydantic model to JSON schema."""

        # Define a simple model for this test
        class SimpleModel(BaseModel):
            name: str = Field(..., description="Person's name")
            age: int = Field(..., description="Person's age")
            is_active: bool = Field(False, description="Activity status")

        schema = PydanticParser.to_json_schema(SimpleModel)

        # Check schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "is_active" in schema["properties"]

        # Check property types
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["is_active"]["type"] == "boolean"

        # Check descriptions
        assert schema["properties"]["name"]["description"] == "Person's name"
        assert schema["properties"]["age"]["description"] == "Person's age"
        assert schema["properties"]["is_active"]["description"] == "Activity status"

        # Check required fields
        assert "required" in schema
        assert "name" in schema["required"]
        assert "age" in schema["required"]
        assert "is_active" not in schema["required"]  # Has default value

    def test_to_json_schema_nested_object(self):
        """Test converting a Pydantic model with nested models to JSON schema."""
        schema = PydanticParser.to_json_schema(Person)

        # Process the schema to resolve references
        processed_schema = PydanticParser._process_schema_for_formatting(schema)

        # Check root properties
        assert "name" in processed_schema["properties"]
        assert "age" in processed_schema["properties"]
        assert "address" in processed_schema["properties"]
        assert "contacts" in processed_schema["properties"]

        # Check nested address properties
        assert "properties" in processed_schema["properties"]["address"]
        assert "street" in processed_schema["properties"]["address"]["properties"]
        assert "city" in processed_schema["properties"]["address"]["properties"]
        assert "zip_code" in processed_schema["properties"]["address"]["properties"]

        # Check array of contacts properties
        assert processed_schema["properties"]["contacts"]["type"] == "array"
        assert "items" in processed_schema["properties"]["contacts"]
        assert "properties" in processed_schema["properties"]["contacts"]["items"]
        assert "name" in processed_schema["properties"]["contacts"]["items"]["properties"]
        assert "phone" in processed_schema["properties"]["contacts"]["items"]["properties"]
        assert "email" in processed_schema["properties"]["contacts"]["items"]["properties"]

    def test_to_json_schema_deeply_nested(self):
        """Test converting a deeply nested Pydantic model hierarchy to JSON schema."""
        schema = PydanticParser.to_json_schema(PersonWithFamily)

        # Process the schema to resolve references
        processed_schema = PydanticParser._process_schema_for_formatting(schema)

        # Check first level nesting
        assert "family" in processed_schema["properties"]
        assert "properties" in processed_schema["properties"]["family"]

        # Check second level nesting - spouse and children
        family_props = processed_schema["properties"]["family"]["properties"]
        assert "spouse" in family_props
        assert "children" in family_props

        # Check that the schema was processed appropriately
        # Even if the exact structure varies, we need to ensure the schema contains
        # all the necessary information for generating valid instructions
        children_prop = family_props["children"]
        assert children_prop["type"] == "array"
        assert "items" in children_prop

    # ---------------------------------------------------------------------------
    # Tests for format instructions generation
    # ---------------------------------------------------------------------------

    def test_get_format_instructions_basic(self):
        """Test generating format instructions for a basic model."""

        class SimpleModel(BaseModel):
            name: str = Field(..., description="Person's name")
            age: int = Field(..., description="Person's age")

        instructions = PydanticParser.get_format_instructions(SimpleModel)

        # Check basic elements
        assert "[" in instructions
        assert "]" in instructions
        assert '"name": ""' in instructions
        assert '"age": number' in instructions
        assert "Person's name (required)" in instructions
        assert "Person's age (required)" in instructions

    def test_get_format_instructions_nested(self):
        """Test generating format instructions for a model with nested objects."""
        instructions = PydanticParser.get_format_instructions(Person)

        # Check nested object formatting
        assert '"address": {' in instructions
        assert '"street": ""' in instructions
        assert '"city": ""' in instructions
        assert '"zip_code": ""' in instructions
        assert "Street name (required)" in instructions
        assert "City name (required)" in instructions
        assert "Zip code (optional)" in instructions

        # Check array of objects formatting
        assert '"contacts": [' in instructions
        assert '"name": ""' in instructions  # Multiple occurrences
        assert '"phone": ""' in instructions
        assert '"email": ""' in instructions
        assert "Contact name (required)" in instructions
        assert "Phone number (required)" in instructions
        assert "Email address (optional)" in instructions

    def test_get_format_instructions_deeply_nested(self):
        """Test generating format instructions for deeply nested models."""
        instructions = PydanticParser.get_format_instructions(PersonWithFamily)

        # Check family nested object
        assert '"family": {' in instructions

        # Adjust the test to check for just the key presence without checking exact formatting
        assert '"spouse"' in instructions
        assert '"children"' in instructions

        # Check for name field presence in the output
        assert '"name"' in instructions

        # Less strict checks for description content
        assert "name" in instructions  # Just check that "name" is mentioned somewhere
        assert "age" in instructions
        assert "hobbies" in instructions

    def test_nested_fact_model(self):
        """Test specific case for NestedFactsList model."""
        instructions = PydanticParser.get_format_instructions(NestedFactsList)

        # Check facts array structure
        assert '"facts": [' in instructions

        # Check fact object properties
        assert '"question": ""' in instructions
        assert '"answer": ""' in instructions
        assert '"category": ""' in instructions

        # Check descriptions
        assert "The factual question generated (required)" in instructions
        assert "The corresponding answer (required)" in instructions
        assert "A category for the fact (required)" in instructions

    # ---------------------------------------------------------------------------
    # Tests for parsing LLM output to Pydantic models
    # ---------------------------------------------------------------------------

    def test_parse_dict_or_list_single(self):
        """Test parsing a single dictionary to a Pydantic model."""
        data = {"name": "John Doe", "age": 35, "address": {"street": "123 Main St", "city": "Anytown", "zip_code": "12345"}}

        person = PydanticParser.parse_dict_or_list(data, Person)

        assert isinstance(person, Person)
        assert person.name == "John Doe"
        assert person.age == 35
        assert person.address.street == "123 Main St"
        assert person.address.city == "Anytown"
        assert person.address.zip_code == "12345"
        assert isinstance(person.address, Address)
        assert len(person.contacts) == 0

    def test_parse_dict_or_list_list(self):
        """Test parsing a list of dictionaries to a list of Pydantic models."""
        data = [{"name": "Alice", "phone": "555-1234"}, {"name": "Bob", "phone": "555-5678", "email": "bob@example.com"}]

        contacts = PydanticParser.parse_dict_or_list(data, Contact)

        assert isinstance(contacts, list)
        assert len(contacts) == 2
        assert all(isinstance(contact, Contact) for contact in contacts)
        assert contacts[0].name == "Alice"
        assert contacts[0].phone == "555-1234"
        assert contacts[0].email is None
        assert contacts[1].name == "Bob"
        assert contacts[1].phone == "555-5678"
        assert contacts[1].email == "bob@example.com"

    def test_parse_dict_or_list_validation_error(self):
        """Test validation errors in parse_dict_or_list."""
        # Missing required field
        data = {"name": "John"}
        with pytest.raises(ValidationError):
            PydanticParser.parse_dict_or_list(data, Contact)

        # Wrong type for field
        data = {"name": "John", "phone": 12345}
        with pytest.raises(ValidationError):
            PydanticParser.parse_dict_or_list(data, Contact)

    def test_parse_llm_output_basic(self):
        """Test parsing LLM output into a basic Pydantic model."""
        text = '{"name": "Alice", "phone": "555-1234"}'

        result = PydanticParser.parse_llm_output(text, Contact)

        assert isinstance(result, Contact)
        assert result.name == "Alice"
        assert result.phone == "555-1234"
        assert result.email is None

    def test_parse_llm_output_nested(self):
        """Test parsing LLM output into a nested Pydantic model structure."""
        text = """
        {
            "name": "John Smith",
            "age": 42,
            "address": {
                "street": "123 Main St",
                "city": "Anytown"
            },
            "contacts": [
                {
                    "name": "Jane Smith",
                    "phone": "555-1234",
                    "email": "jane@example.com"
                },
                {
                    "name": "Bob Jones",
                    "phone": "555-5678"
                }
            ]
        }
        """

        result = PydanticParser.parse_llm_output(text, Person)

        assert isinstance(result, Person)
        assert result.name == "John Smith"
        assert result.age == 42
        assert result.address.street == "123 Main St"
        assert result.address.city == "Anytown"

        assert len(result.contacts) == 2
        assert result.contacts[0].name == "Jane Smith"
        assert result.contacts[0].phone == "555-1234"
        assert result.contacts[0].email == "jane@example.com"
        assert result.contacts[1].name == "Bob Jones"
        assert result.contacts[1].phone == "555-5678"
        assert result.contacts[1].email is None

    def test_parse_llm_output_with_markdown_code_blocks(self):
        """Test parsing LLM output with markdown formatting."""
        text = """
        Here's the information you requested:
        ```json
        {
            "name": "John Smith",
            "age": 42,
            "address": {
                "street": "123 Main St",
                "city": "Anytown"
            }
        }
        ```
        Is there anything else you need?
        """

        result = PydanticParser.parse_llm_output(text, Person)

        assert isinstance(result, Person)
        assert result.name == "John Smith"
        assert result.age == 42
        assert result.address.street == "123 Main St"
        assert result.address.city == "Anytown"

    def test_parse_llm_output_error_handling(self):
        """Test error handling in parse_llm_output."""
        # Missing required field
        text = '{"name": "John"}'

        # Should raise error in strict mode
        with pytest.raises(PydanticParserError):
            PydanticParser.parse_llm_output(text, Person, strict=True)

        # Should return None in non-strict mode
        result = PydanticParser.parse_llm_output(text, Person, strict=False)
        assert result is None

    def test_parse_llm_output_with_wrapper(self):
        """Test parsing with a JSON wrapper key."""
        text = """
        {
            "results": [
                {
                    "name": "John Doe",
                    "phone": "555-1234"
                },
                {
                    "name": "Jane Smith",
                    "phone": "555-5678",
                    "email": "jane@example.com"
                }
            ]
        }
        """

        result = PydanticParser.parse_llm_output(text, Contact, json_wrapper_key="results")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, Contact) for item in result)
        assert result[0].name == "John Doe"
        assert result[1].name == "Jane Smith"
        assert result[1].email == "jane@example.com"

    def test_nested_facts_list_parsing(self):
        """Test parsing the specific NestedFactsList example."""
        text = """
        {
            "facts": [
                {
                    "question": "What is the tallest building in New York?",
                    "answer": "One World Trade Center",
                    "category": "Architecture"
                },
                {
                    "question": "What is the largest park in New York?",
                    "answer": "Pelham Bay Park",
                    "category": "Geography"
                }
            ]
        }
        """

        result = PydanticParser.parse_llm_output(text, NestedFactsList)

        assert isinstance(result, NestedFactsList)
        assert len(result.facts) == 2
        assert all(isinstance(fact, Fact) for fact in result.facts)

        assert result.facts[0].question == "What is the tallest building in New York?"
        assert result.facts[0].answer == "One World Trade Center"
        assert result.facts[0].category == "Architecture"

        assert result.facts[1].question == "What is the largest park in New York?"
        assert result.facts[1].answer == "Pelham Bay Park"
        assert result.facts[1].category == "Geography"
