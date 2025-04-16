from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from starfish.llm.parser.json_parser import JSONParser


# Pydantic models for field definitions
class SimpleField(BaseModel):
    """Pydantic model for simple field definitions."""

    name: str = Field(..., description="Name of the field")
    type: str = Field(..., description="Type of the field (str, int, float, bool, list, dict)")
    description: str = Field("", description="Description of the field")
    required: bool = Field(True, description="Whether the field is required")

    @field_validator("type")
    def validate_field_type(self, v):
        valid_types = ["str", "int", "float", "bool", "list", "dict", "null"]
        if v not in valid_types:
            raise ValueError(f"Field type must be one of {valid_types}")
        return v


class ArrayField(BaseModel):
    """Pydantic model for array field definitions."""

    name: str = Field(..., description="Name of the field")
    type: Literal["list"] = Field("list", description="Type is always 'list' for array fields")
    items: Dict[str, Any] = Field(..., description="Definition of array items")
    description: str = Field("", description="Description of the field")
    required: bool = Field(True, description="Whether the field is required")


class NestedObjectField(BaseModel):
    """Pydantic model for nested object field definitions."""

    name: str = Field(..., description="Name of the field")
    type: Literal["dict"] = Field("dict", description="Type is always 'dict' for nested objects")
    properties: Dict[str, Dict[str, Any]] = Field(..., description="Dictionary of property definitions")
    description: str = Field("", description="Description of the field")
    required: bool = Field(True, description="Whether this field is required")
    required_props: Optional[List[str]] = Field(None, description="List of required properties in the nested object")


class JsonSchemaBuilder:
    """A utility class to build JSON schemas programmatically.
    This can be used directly through function calls or as a backend for a UI.
    Enhanced with Pydantic validation.
    """

    def __init__(self):
        """Initialize an empty schema builder."""
        self.fields = []

    def add_simple_field(self, name: str, field_type: str, description: str = "", required: bool = True) -> None:
        """Add a simple field to the schema. Validated with Pydantic.

        Args:
            name: Field name
            field_type: Field type (str, int, float, bool, list, dict)
            description: Field description
            required: Whether the field is required

        Raises:
            ValidationError: If the field definition is invalid
        """
        # Validate with Pydantic
        field = SimpleField(name=name, type=field_type, description=description, required=required)

        # Add validated field to the schema
        self.fields.append(field.model_dump())

    def add_nested_object(
        self, name: str, properties: Dict[str, Dict[str, Any]], description: str = "", required: bool = True, required_props: List[str] = None
    ) -> None:
        """Add a nested object field to the schema. Validated with Pydantic.

        Args:
            name: Field name
            properties: Dictionary of property definitions
            description: Field description
            required: Whether this field is required
            required_props: List of required properties in the nested object

        Raises:
            ValidationError: If the field definition is invalid
        """
        # Validate with Pydantic
        field = NestedObjectField(name=name, properties=properties, description=description, required=required, required_props=required_props)

        # Add validated field to the schema
        self.fields.append(field.model_dump())

    def add_array_field(self, name: str, items: Dict[str, Any], description: str = "", required: bool = True) -> None:
        """Add an array field to the schema. Validated with Pydantic.

        Args:
            name: Field name
            items: Definition of array items
            description: Field description
            required: Whether this field is required

        Raises:
            ValidationError: If the field definition is invalid
        """
        # Validate with Pydantic
        field = ArrayField(name=name, items=items, description=description, required=required)

        # Add validated field to the schema
        self.fields.append(field.model_dump())

    def get_schema(self) -> List[Dict[str, Any]]:
        """Get the built schema as a list of field definitions.

        Returns:
            The schema as a list of field definitions
        """
        return self.fields

    def get_json_schema(self) -> Dict[str, Any]:
        """Get the schema as a JSON schema object.

        Returns:
            The schema as a JSON schema dictionary
        """
        return JSONParser.convert_to_schema(self.fields)

    def preview_schema_format(self) -> str:
        """Preview the schema format instructions.

        Returns:
            A formatted string with instructions for the schema
        """
        json_schema = self.get_json_schema()
        return JSONParser.get_format_instructions(json_schema)

    def clear(self) -> None:
        """Clear the schema builder."""
        self.fields = []


### Example usage
# # Creating a schema with JsonSchemaBuilder
# from starfish.common.json_schema_utils import JsonSchemaBuilder

# # Create a builder
# builder = JsonSchemaBuilder()

# # Add fields
# builder.add_simple_field("name", "str", "Customer's full name")
# builder.add_simple_field("age", "int", "Age in years")
# builder.add_simple_field("is_active", "bool", "Whether the account is active")

# # Add a nested object
# builder.add_nested_object(
#     name="address",
#     properties={
#         "street": {"type": "string", "description": "Street address"},
#         "city": {"type": "string", "description": "City name"},
#         "zip": {"type": "string", "description": "ZIP code"}
#     },
#     description="Customer address"
# )

# # Get the schema
# schema = builder.get_json_schema()

# # Preview the schema format instructions
# instructions = builder.preview_schema_format()
