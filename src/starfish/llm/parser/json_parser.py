import json
from typing import Any, Dict, List, Optional

from starfish.common.exceptions import JsonParserError, SchemaValidationError
from starfish.common.logger import get_logger

logger = get_logger(__name__)


class JSONParser:
    """Handles parsing and validation of JSON data against schemas.

    Provides utilities for JSON schema generation and formatting.
    """

    @staticmethod
    def _extract_json_from_text(text: str) -> str:
        """Clean a string that might contain JSON with markdown code block markers.

        Args:
            text: String potentially containing JSON within markdown formatting

        Returns:
            Cleaned JSON string with markdown and extra text removed

        Raises:
            JsonParserError: If no valid JSON content can be found in the text
        """
        # First try to extract from markdown code blocks
        if "```" in text:
            # Try extracting from ```json blocks first
            if "```json" in text and "```" in text.split("```json", 1)[1]:
                json_content = text.split("```json", 1)[1].split("```")[0]
                return json_content.strip()

            # Try extracting from any code block
            parts = text.split("```")
            if len(parts) >= 3:
                content = parts[1]
                if "\n" in content:
                    first_line, rest = content.split("\n", 1)
                    if not first_line.strip().startswith(("{", "[")):
                        content = rest
                return content.strip()

        # Try to find JSON content directly
        for i, char in enumerate(text):
            if char in ["{", "["]:
                # Find matching closing brace/bracket
                stack = []
                in_string = False
                escaped = False

                for j in range(i, len(text)):
                    char = text[j]

                    if in_string:
                        if char == "\\":
                            escaped = not escaped
                        elif char == '"' and not escaped:
                            in_string = False
                        else:
                            escaped = False
                    else:
                        if char == '"':
                            in_string = True
                            escaped = False
                        elif char in ["{", "["]:
                            stack.append(char)
                        elif char == "}" and stack and stack[-1] == "{":
                            stack.pop()
                        elif char == "]" and stack and stack[-1] == "[":
                            stack.pop()

                    if not stack:
                        return text[i : j + 1].strip()

        raise JsonParserError("No valid JSON content found in the text")

    @staticmethod
    def _unwrap_json_data(json_data: Any, json_wrapper_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract and normalize data from parsed JSON.

        Args:
            json_data: Parsed JSON data
            json_wrapper_key: Optional key that may wrap the actual data

        Returns:
            List of data items, ensuring the result is always a list

        Raises:
            TypeError: If data is not a dict or list
            KeyError: If json_wrapper_key is not found in the data
        """
        if json_wrapper_key and isinstance(json_data, dict):
            # Let KeyError propagate naturally if key doesn't exist
            result = json_data[json_wrapper_key]
        else:
            result = json_data

        if not isinstance(result, (dict, list)):
            raise TypeError(f"Expected dict or list, got {type(result).__name__}")

        return [result] if isinstance(result, dict) else result

    @staticmethod
    def convert_to_schema(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a JSON schema from field definitions.

        Args:
            fields: List of field definitions with name, type, description, and required flag

        Returns:
            A JSON schema dictionary

        Raises:
            TypeError: If fields is not a list or field is not a dict
            KeyError: If required field attributes are missing
            ValueError: If field type is invalid
        """
        if not isinstance(fields, list):
            raise TypeError(f"Expected list of fields, got {type(fields)}")

        schema = {"type": "object", "properties": {}, "required": []}

        type_mapping = {
            "str": {"type": "string"},
            "int": {"type": "integer"},
            "float": {"type": "number"},
            "bool": {"type": "boolean"},
            "list": {"type": "array"},
            "dict": {"type": "object"},
            "null": {"type": "null"},
        }

        for field in fields:
            if not isinstance(field, dict):
                raise TypeError(f"Expected dict for field definition, got {type(field)}")

            # Let KeyError propagate naturally for missing required attributes
            name = field["name"]
            field_type = field["type"]
            description = field.get("description", "")
            required = field.get("required", True)

            if field_type == "list" and "items" in field:
                schema["properties"][name] = {"type": "array", "items": field["items"], "description": description}
            elif field_type == "dict" and "properties" in field:
                schema["properties"][name] = {"type": "object", "properties": field["properties"], "description": description}
                if "required" in field:
                    schema["properties"][name]["required"] = field["required"]
            elif field_type in type_mapping:
                schema["properties"][name] = {**type_mapping[field_type], "description": description}
            else:
                raise ValueError(f"Invalid field type '{field_type}' for field '{name}'")

            if required:
                schema["required"].append(name)

        return schema

    @staticmethod
    def get_format_instructions(schema: Dict[str, Any], json_wrapper_key: Optional[str] = None, show_array_items: int = 1) -> str:
        """Format a JSON schema into human-readable instructions.

        Args:
            schema: A JSON schema dictionary
            json_wrapper_key: Optional key to wrap the schema in an array
            show_array_items: Number of example items to show in an array wrapper

        Returns:
            Formatted string with schema instructions
        """

        def format_property(name: str, prop: Dict[str, Any], required: List[str], indent_level: int = 1) -> List[str]:
            lines = []
            indent = "  " * indent_level
            field_type = prop.get("type", "string")
            description = prop.get("description", "")
            is_required = name in required

            comment = f"// {description}" + (" (required)" if is_required else " (optional)")

            if field_type == "object" and "properties" in prop:
                lines.append(f'{indent}"{name}": {{  {comment}')
                nested_props = prop.get("properties", {})
                nested_required = prop.get("required", [])

                # Recursively format properties of the nested object
                formatted_props = []
                for i, (nested_name, nested_prop) in enumerate(nested_props.items()):
                    # Increase indent level for properties inside the object
                    prop_lines = format_property(nested_name, nested_prop, nested_required, indent_level + 1)
                    # Add comma if not the last property
                    if i < len(nested_props) - 1 and prop_lines:
                        prop_lines[-1] = prop_lines[-1] + ","
                    formatted_props.extend(prop_lines)
                lines.extend(formatted_props)
                # End of recursive formatting

                lines.append(f"{indent}}}")

            elif field_type == "array" and "items" in prop:
                items = prop.get("items", {})
                item_type = items.get("type")
                lines.append(f'{indent}"{name}": [  {comment}')  # Start array

                # Check if items are objects and have properties
                if item_type == "object" and "properties" in items:
                    lines.append(f"{indent}  {{")  # Start example object in array
                    nested_props = items.get("properties", {})
                    nested_required = items.get("required", [])

                    # Recursively format the properties of the object within the array item
                    formatted_props = []
                    for i, (nested_name, nested_prop) in enumerate(nested_props.items()):
                        # Increase indent level for properties inside the object
                        prop_lines = format_property(nested_name, nested_prop, nested_required, indent_level + 2)
                        # Add comma if not the last property
                        if i < len(nested_props) - 1 and prop_lines:
                            prop_lines[-1] = prop_lines[-1] + ","
                        formatted_props.extend(prop_lines)
                    lines.extend(formatted_props)
                    # End of recursive formatting for array item properties

                    lines.append(f"{indent}  }}")  # End example object
                    lines.append(f"{indent}  // ... more items ...")  # Indicate potential for more items
                # Handle arrays of simple types (optional, could add examples here too)
                # elif item_type in type_mapping:
                #     lines.append(f"{indent}  // Example: {type_mapping[item_type]}")
                else:
                    lines.append(f"{indent}  // Example items of type {item_type}")

                lines.append(f"{indent}]")  # End array
            else:
                example_value = (
                    '""'
                    if field_type == "string"
                    else "number"
                    if field_type in ["integer", "number"]
                    else "true or false"
                    if field_type == "boolean"
                    else "[]"
                    if field_type == "array"
                    else "{}"
                )
                lines.append(f'{indent}"{name}": {example_value}  {comment}')

            return lines

        schema_lines = []

        if json_wrapper_key:
            schema_lines.extend(["{", f'  "{json_wrapper_key}": ['])

            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for item_idx in range(show_array_items):
                schema_lines.append("    {")

                for i, (name, prop) in enumerate(properties.items()):
                    prop_lines = format_property(name, prop, required, indent_level=3)
                    if i < len(properties) - 1 and prop_lines:
                        prop_lines[-1] = prop_lines[-1] + ","
                    schema_lines.extend(prop_lines)

                schema_lines.append("    }" + ("," if item_idx < show_array_items - 1 else ""))

            schema_lines.append("    ...")

            schema_lines.extend(["  ]", "}"])
        else:
            # Always format as a list structure
            schema_lines.append("[")
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for item_idx in range(show_array_items):
                schema_lines.append("    {")

                for i, (name, prop) in enumerate(properties.items()):
                    prop_lines = format_property(name, prop, required, indent_level=2)
                    if i < len(properties) - 1 and prop_lines:
                        prop_lines[-1] = prop_lines[-1] + ","
                    schema_lines.extend(prop_lines)

                schema_lines.append("    }" + ("," if item_idx < show_array_items - 1 else ""))

            schema_lines.append("    ...")
            schema_lines.append("]")

        if schema.get("title") or schema.get("description"):
            schema_lines.append("")
            if schema.get("title"):
                schema_lines.append(schema["title"])
            if schema.get("description"):
                schema_lines.append(schema["description"])

        required = schema.get("required", [])
        if required:
            schema_lines.append(f"\nRequired fields: {', '.join(required)}")

        return "\n".join(schema_lines)

    @staticmethod
    def validate_against_schema(data: List[Dict[str, Any]], schema: Dict[str, Any], type_check: bool = False) -> None:
        """Validate data against a JSON schema.

        Args:
            data: List of data items to validate
            schema: JSON schema to validate against
            type_check: If True, check field types against schema. If False, skip type validation.

        Raises:
            TypeError: If data or schema have invalid types
            KeyError: If schema is missing required fields
            SchemaValidationError: If validation fails with specific validation errors
        """
        properties = schema["properties"]
        required_fields = schema.get("required", [])

        type_mapping = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}

        validation_errors = []

        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise TypeError(f"Item {index}: expected dict, got {type(item)}")

            # Check required fields
            for field_name in required_fields:
                if field_name not in item:
                    validation_errors.append(f"Item {index}: Missing required field '{field_name}'")

            # Check unexpected fields
            for field_name in item:
                if field_name not in properties:
                    validation_errors.append(f"Item {index}: Unexpected field '{field_name}' not defined in schema")

            # Check field types only if type_check is True
            if type_check:
                for field_name, field_schema in properties.items():
                    if field_name not in item:
                        continue

                    field_value = item[field_name]
                    if field_value is None:
                        if field_schema.get("type") != "null" and "null" not in field_schema.get("type", []):
                            validation_errors.append(f"Item {index}: Field '{field_name}' is null but type should be {field_schema['type']}")
                        continue

                    # Let KeyError propagate naturally
                    expected_type = field_schema["type"]
                    expected_python_type = type_mapping.get(expected_type)

                    if expected_python_type and not isinstance(field_value, expected_python_type):
                        validation_errors.append(f"Item {index}: Field '{field_name}' has type {type(field_value).__name__} " f"but should be {expected_type}")

                    # Validate nested objects
                    if expected_type == "object" and isinstance(field_value, dict):
                        # Let KeyError propagate naturally
                        nested_schema = {"properties": field_schema["properties"], "required": field_schema.get("required", [])}
                        try:
                            JSONParser.validate_against_schema([field_value], nested_schema, type_check=type_check)
                        except SchemaValidationError as e:
                            for error in e.details["errors"]:
                                validation_errors.append(error.replace("Item 0:", f"Item {index}: Field '{field_name}'"))

                    # Validate arrays
                    if expected_type == "array" and isinstance(field_value, list):
                        # Let KeyError propagate naturally
                        items_schema = field_schema["items"]
                        if items_schema.get("type") == "object":
                            nested_schema = {"properties": items_schema["properties"], "required": items_schema.get("required", [])}
                            for array_idx, array_item in enumerate(field_value):
                                if not isinstance(array_item, dict):
                                    validation_errors.append(f"Item {index}: Field '{field_name}[{array_idx}]' should be an object")
                                    continue

                                try:
                                    JSONParser.validate_against_schema([array_item], nested_schema, type_check=type_check)
                                except SchemaValidationError as e:
                                    for error in e.details["errors"]:
                                        validation_errors.append(error.replace("Item 0:", f"Item {index}: Field '{field_name}[{array_idx}]'"))

        if validation_errors:
            raise SchemaValidationError("Schema validation failed", details={"errors": validation_errors})

    @staticmethod
    def parse_llm_output(
        text: str, schema: Optional[Dict[str, Any]] = None, json_wrapper_key: Optional[str] = None, strict: bool = False, type_check: bool = False
    ) -> Optional[Any]:
        """Complete JSON parsing pipeline for LLM outputs with configurable error handling.

        Args:
            text: Raw text from LLM that may contain JSON
            schema: Optional JSON schema to validate against
            json_wrapper_key: Optional key that may wrap the actual data
            strict: If True, raise errors. If False, return None and log warning
            type_check: If True, check field types against schema. If False, skip type validation.

        Returns:
            Parsed data if successful, None if parsing fails in non-strict mode

        Raises:
            JsonParserError: If parsing fails in strict mode
            SchemaValidationError: If schema validation fails in strict mode
            json.JSONDecodeError: If JSON syntax is invalid in strict mode
        """
        try:
            cleaned_text = JSONParser._extract_json_from_text(text)
            parsed_json = json.loads(cleaned_text)
            data = JSONParser._unwrap_json_data(parsed_json, json_wrapper_key)

            if schema:
                JSONParser.validate_against_schema(data, schema, type_check=type_check)

            return data

        except JsonParserError as e:
            # Handle JSON extraction errors
            if strict:
                raise
            logger.warning(f"Failed to extract JSON from LLM response: {str(e)}")
            return None

        except json.JSONDecodeError as e:
            # Handle JSON syntax errors
            if strict:
                raise JsonParserError(f"Invalid JSON syntax: {str(e)}") from e
            logger.warning(f"Invalid JSON syntax in LLM response: {str(e)}")
            return None

        except SchemaValidationError as e:
            # Handle schema validation errors
            if strict:
                raise
            logger.warning(f"LLM response failed schema validation: {str(e)}")
            if e.details and "errors" in e.details:
                for error in e.details["errors"]:
                    logger.debug(f"- {error}")
            return None

        except (TypeError, KeyError) as e:
            # Handle data structure errors
            if strict:
                raise JsonParserError(f"Data structure error: {str(e)}") from e
            logger.warning(f"Data structure error in LLM response: {str(e)}")
            return None
