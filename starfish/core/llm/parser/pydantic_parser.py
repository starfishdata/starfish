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
            return PydanticParser.parse_dict_or_list(json_data, model)

        except ValidationError as e:
            # Handle Pydantic validation errors
            if strict:
                raise PydanticParserError("Failed to validate against Pydantic model", details={"errors": e.errors()})
            logger.warning(f"Failed to validate LLM response against Pydantic model: {str(e)}")
            logger.debug(f"Validation errors: {e.errors()}")
            return None
        except TypeError as e:
            # Handle type errors from parse_dict_or_list
            if strict:
                raise PydanticParserError(f"Type error during parsing: {str(e)}")
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
        return JSONParser.get_format_instructions(json_schema, json_wrapper_key, show_array_items)
