from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from starfish.common.exceptions import PydanticParserError
from starfish.common.logger import get_logger

from .json_parser import JSONParser

logger = get_logger(__name__)


class PydanticParser:
    """Handles parsing and validation using Pydantic models.

    Provides utilities for converting between Pydantic and JSON schemas.
    """

    @staticmethod
    def to_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
        """Convert a Pydantic model to JSON schema.

        Args:
            model: Pydantic model class

        Returns:
            JSON schema dictionary

        Raises:
            TypeError: If model is not a Pydantic model
        """
        # Handle both Pydantic v1 and v2
        if hasattr(model, "model_json_schema"):
            # Pydantic v2
            return model.model_json_schema()
        else:
            # Pydantic v1
            return model.schema()

    @staticmethod
    def _process_schema_for_formatting(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Pydantic-generated JSON schema for better format instruction display.

        This resolves $ref references to make a flattened schema for display purposes.

        Args:
            schema: The Pydantic JSON schema

        Returns:
            A processed schema with resolved references
        """
        # Create a copy to avoid modifying the original schema
        processed_schema = schema.copy()

        # Process the schema recursively
        def process_node(node):
            if not isinstance(node, dict):
                return node

            processed_node = node.copy()

            # Handle $ref directly
            if "$ref" in processed_node:
                ref_path = processed_node["$ref"]
                if ref_path.startswith("#/$defs/"):
                    def_name = ref_path.split("/")[-1]
                    if "$defs" in schema and def_name in schema["$defs"]:
                        # Replace the reference with the actual definition
                        ref_definition = schema["$defs"][def_name].copy()

                        # Preserve any additional properties like description
                        for key, value in processed_node.items():
                            if key != "$ref":
                                ref_definition[key] = value

                        # Process the referenced definition recursively
                        processed_node = process_node(ref_definition)

            # Handle anyOf with references (used for Optional fields)
            if "anyOf" in processed_node:
                # For format instructions, we'll just take the first non-null type
                # from anyOf as a simplification
                for item in processed_node["anyOf"]:
                    if item.get("type") != "null" and "$ref" in item:
                        ref_path = item["$ref"]
                        if ref_path.startswith("#/$defs/"):
                            def_name = ref_path.split("/")[-1]
                            if "$defs" in schema and def_name in schema["$defs"]:
                                # Replace anyOf with the referenced definition
                                ref_definition = schema["$defs"][def_name].copy()

                                # Preserve any additional properties like description from the parent
                                for key, value in processed_node.items():
                                    if key != "anyOf":
                                        ref_definition[key] = value

                                # Process the referenced definition recursively
                                processed_node = process_node(ref_definition)
                                break

            # Process properties recursively
            if "properties" in processed_node:
                for prop_name, prop_value in list(processed_node["properties"].items()):
                    processed_node["properties"][prop_name] = process_node(prop_value)

            # Process array items recursively
            if "items" in processed_node:
                processed_node["items"] = process_node(processed_node["items"])

            return processed_node

        # Start the recursive processing at the root level
        if "properties" in processed_schema:
            for prop_name, prop_value in list(processed_schema["properties"].items()):
                processed_schema["properties"][prop_name] = process_node(prop_value)

        return processed_schema

    @staticmethod
    def parse_dict_or_list(data: Union[Dict[str, Any], List[Dict[str, Any]]], model: Type[BaseModel]) -> Union[BaseModel, List[BaseModel]]:
        """Parse data into Pydantic model instances.

        Args:
            data: Dictionary or list of dictionaries to parse
            model: Pydantic model class to parse into

        Returns:
            Single model instance or list of model instances

        Raises:
            TypeError: If model is not a Pydantic model or data has invalid type
            ValidationError: If Pydantic validation fails
        """
        if isinstance(data, list):
            # Handle list of objects
            if not all(isinstance(item, dict) for item in data):
                raise TypeError("All items in list must be dictionaries")

            if hasattr(model, "model_validate"):
                # Pydantic v2
                return [model.model_validate(item) for item in data]
            else:
                # Pydantic v1
                return [model.parse_obj(item) for item in data]
        else:
            # Handle single object
            if hasattr(model, "model_validate"):
                # Pydantic v2
                return model.model_validate(data)
            else:
                # Pydantic v1
                return model.parse_obj(data)

    @staticmethod
    def parse_llm_output(
        text: str, model: Type[BaseModel], json_wrapper_key: Optional[str] = None, strict: bool = False
    ) -> Optional[Union[BaseModel, List[BaseModel]]]:
        """Parse LLM output text into Pydantic model instances with configurable error handling.

        Args:
            text: Raw text from LLM that may contain JSON
            model: Pydantic model class to parse into
            json_wrapper_key: Optional key that may wrap the actual data
            strict: If True, raise errors. If False, return None and log warning

        Returns:
            Single model instance or list of model instances if successful,
            None if parsing fails in non-strict mode

        Raises:
            PydanticParserError: If parsing fails in strict mode
            JsonParserError: If JSON parsing fails in strict mode
            SchemaValidationError: If JSON schema validation fails in strict mode
        """
        try:
            # Use JSONParser to handle initial JSON parsing (let its errors propagate in strict mode)
            json_data = JSONParser.parse_llm_output(
                text,
                json_wrapper_key=json_wrapper_key,
                strict=strict,  # Pass through the strict parameter
            )

            # If JSONParser returned None (in non-strict mode), return None
            if json_data is None:
                return None

            # Convert to Pydantic model(s)
            parsed_data = PydanticParser.parse_dict_or_list(json_data, model)

            # If the parsed data is a list of one item and not wrapped, return just the item
            # This makes it consistent with how most APIs would expect a single object
            if isinstance(parsed_data, list) and len(parsed_data) == 1 and not json_wrapper_key:
                return parsed_data[0]

            return parsed_data

        except ValidationError as e:
            # Handle Pydantic validation errors
            if strict:
                raise PydanticParserError("Failed to validate against Pydantic model", details={"errors": e.errors()}) from e
            logger.warning(f"Failed to validate LLM response against Pydantic model: {str(e)}")
            logger.debug(f"Validation errors: {e.errors()}")
            return None
        except TypeError as e:
            # Handle type errors from parse_dict_or_list
            if strict:
                raise PydanticParserError(f"Type error during parsing: {str(e)}") from e
            logger.warning(f"Type error in LLM response: {str(e)}")
            return None

    @staticmethod
    def get_format_instructions(model: Type[BaseModel], json_wrapper_key: Optional[str] = None, show_array_items: int = 1) -> str:
        """Format a Pydantic model schema as human-readable instructions.

        Args:
            model: Pydantic model class
            json_wrapper_key: Optional key to wrap the schema in an array
            show_array_items: Number of example items to show in an array wrapper

        Returns:
            Formatted string with schema instructions

        Raises:
            TypeError: If model is not a Pydantic model
        """
        json_schema = PydanticParser.to_json_schema(model)
        # Process the schema to resolve references for better display
        processed_schema = PydanticParser._process_schema_for_formatting(json_schema)
        return JSONParser.get_format_instructions(processed_schema, json_wrapper_key, show_array_items)
