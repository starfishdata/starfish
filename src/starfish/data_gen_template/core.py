from pathlib import Path
import importlib.metadata
from packaging import requirements
import pydantic
import importlib.util
import ast
from typing import Any, Union, List, Dict, get_type_hints
import inspect
import json
from starfish.data_gen_template.utils.errors import DataTemplateValueError, ImportModuleError, ImportPackageError
from starfish.common.logger import get_logger

logger = get_logger(__name__)


def _check_dependencies(dependencies: list[str]) -> None:
    """Check if all required dependencies are installed and meet version requirements."""
    missing_deps: list[str] = []
    version_mismatches: list[str] = []

    for dep in dependencies:
        try:
            req = requirements.Requirement(dep)
            installed_version = importlib.metadata.version(req.name)
            if not req.specifier.contains(installed_version):
                version_mismatches.append(f"{req.name} (installed: {installed_version}, required: {req.specifier})")
        except importlib.metadata.PackageNotFoundError:
            missing_deps.append(req.name)

    if missing_deps or version_mismatches:
        error_msg = "Dependency check failed:\n"
        if missing_deps:
            error_msg += f"Missing packages: {', '.join(missing_deps)}\n"
        if version_mismatches:
            error_msg += f"Version mismatches: {', '.join(version_mismatches)}"
        raise ImportPackageError(error_msg)


# ====================
# Template Class
# ====================
class Template:
    """Class representing a single template instance."""

    def __init__(
        self,
        name: str,
        func: callable,
        input_schema: type,
        input_example: str,
        output_schema: type,
        description: str,
        author: str,
        starfish_version: str,
        dependencies: list[str],
    ):
        self.name = name
        self.func = func
        self.input_schema = input_schema
        self.input_example = input_example
        self.output_schema = output_schema
        self.description = description
        self.author = author
        self.starfish_version = starfish_version
        self.dependencies = dependencies

        # Add run method if not present
        if not hasattr(self.func, "run"):
            self.func.run = lambda *args, **kwargs: self.func(*args, **kwargs)

        # Detect if function expects a single input_data parameter
        self.expects_model_input = False
        try:
            self.func_signature = inspect.signature(self.func)

            # Check if the function has a single parameter that matches the input_schema type
            if len(self.func_signature.parameters) == 1:
                param_name, param = next(iter(self.func_signature.parameters.items()))
                # Check if the parameter has an annotation matching input_schema
                if param.annotation == self.input_schema:
                    self.expects_model_input = True
        except (TypeError, ValueError):
            # Can't get signature (e.g., for data_factory decorated functions)
            # Default to False (use individual parameters) which is safer
            self.expects_model_input = False

        # Check dependencies on initialization
        # if self.dependencies:
        #     _check_dependencies(self.dependencies)

    async def run(self, *args, **kwargs) -> Any:
        """Execute the wrapped function with schema validation.

        This method supports multiple calling patterns:
        - template.run(param1=val1, param2=val2)  # Keyword arguments
        - template.run({"param1": val1, "param2": val2})  # Dictionary
        - template.run(model_instance)  # Pydantic model instance

        The template function can be defined in two ways:
        1. Taking a single Pydantic model parameter: func(input_data: Model)
        2. Taking individual parameters: func(param1, param2, param3)

        In all cases, validation happens through the Pydantic model.
        """
        # STEP 1: Get a validated Pydantic model instance from the inputs
        validated_model = self._get_validated_model(args, kwargs)

        # STEP 2: Call the function with appropriate arguments based on its signature
        try:
            if self.expects_model_input:
                # Pass the whole model to functions expecting a model parameter
                result = await self.func.run(validated_model)
            else:
                # Expand model fields for functions expecting individual parameters
                result = await self.func.run(**validated_model.model_dump())
        except Exception as e:
            raise DataTemplateValueError(f"Template execution failed: {str(e)}")

        # STEP 3: Validate the output if an output schema is provided
        if self.output_schema is not None:
            try:
                # Use model_validate instead of validate (which is deprecated in Pydantic v2)
                self.output_schema.model_validate(result)
            except pydantic.ValidationError as e:
                raise DataTemplateValueError(f"Output validation failed: {str(e)}")

        return result

    def print_schema(self):
        type_hints = get_type_hints(self.func)
        input_schema = type_hints.get("input_data").schema()
        # Pretty print the schema
        logger.info("Please run the template with this input schema")
        logger.info(json.dumps(input_schema, indent=4))

    def print_example(self):
        logger.info("Here is an example with api_contract.name as weather_api.get_current_weather")
        logger.info(self.input_example)  # Pretty print with 4-space indentation

    def _get_validated_model(self, args, kwargs):
        """Convert input arguments into a validated Pydantic model instance."""
        # Case 1: User passed a model instance directly
        if len(args) == 1 and isinstance(args[0], self.input_schema):
            return args[0]

        # Case 2: User passed a dictionary as the first positional argument
        if len(args) == 1 and isinstance(args[0], dict):
            # Merge dictionary with any keyword arguments
            input_data = {**args[0], **kwargs}
        # Case 3: User passed keyword arguments only
        elif not args:
            input_data = kwargs
        # Case 4: Invalid input (multiple positional args or wrong type)
        else:
            raise DataTemplateValueError("Invalid arguments: Please provide either keyword arguments, " "a single dictionary, or a model instance.")

        # Validate and return a model instance
        try:
            return self.input_schema.model_validate(input_data)
        except pydantic.ValidationError as e:
            raise DataTemplateValueError(f"Input validation failed: {str(e)}")


# ====================
# Template Management Class
# ====================
class data_gen_template:
    """Class for template management and registration."""

    _template_registry = {}
    _template_instance_registry = {}

    @staticmethod
    def list(is_detail: bool = False) -> list[Any]:
        # airbyte structuredio
        """List all available templates in the format 'subfolder_name/template_name'."""
        templates_dir = Path(__file__).resolve().parent / "templates"
        result = list(data_gen_template._template_registry.keys())
        if len(result) == 0:
            # Walk through all subdirectories in templates folder
            for subdir in templates_dir.iterdir():
                for sub_subdir in subdir.iterdir():
                    # Find all .py files in the subdirectory
                    for template_file in sub_subdir.glob("*.py"):
                        try:
                            module_name = f"starfish.data_gen_template.templates.{subdir.name}.{sub_subdir.name}.{template_file.stem}"
                            # Parse the file's AST to extract decorator information
                            with open(template_file, "r") as f:
                                tree = ast.parse(f.read())

                            # Find both class and function definitions with decorators
                            for node in ast.walk(tree):
                                if hasattr(node, "decorator_list"):
                                    template_args = None
                                    # Check all decorators
                                    for decorator in node.decorator_list:
                                        # Handle @data_gen_template.register
                                        if (
                                            isinstance(decorator, ast.Call)
                                            and isinstance(decorator.func, ast.Attribute)
                                            and decorator.func.attr == "register"
                                            and isinstance(decorator.func.value, ast.Name)
                                            and decorator.func.value.id == "data_gen_template"
                                        ):
                                            # Extract the decorator arguments
                                            args = {"module_name": module_name}
                                            for keyword in decorator.keywords:
                                                if isinstance(keyword.value, (ast.Str, ast.Num, ast.List, ast.Dict, ast.Tuple, ast.NameConstant)):
                                                    args[keyword.arg] = ast.literal_eval(keyword.value)
                                                elif isinstance(keyword.value, ast.Name):
                                                    # Store the class name as a string for class references
                                                    args[keyword.arg] = keyword.value.id
                                            template_args = args
                                            break
                                    # Register the template if we found the registration decorator
                                    if template_args:
                                        data_gen_template._template_registry[f"{template_args['name']}"] = template_args
                                        break

                        except Exception as e:
                            print(f"Warning: Could not parse {template_file}: {e}")
                            continue

        # Return the registered templates from the registry
        if is_detail:
            return [v for _, v in data_gen_template._template_registry.items()]
        return list(data_gen_template._template_registry.keys())

    @staticmethod
    def get(template_name: str) -> Template:
        """Get a template function by its name."""
        if template_name in data_gen_template._template_instance_registry:
            return data_gen_template._template_instance_registry[template_name]
        if template_name not in data_gen_template._template_registry:
            raise DataTemplateValueError(f"Template {template_name} not found")
        # Get the file path and metadata
        try:
            module_name = data_gen_template._template_registry[template_name].get("module_name")
            dependencies = data_gen_template._template_registry[template_name].get("dependencies")
            if dependencies:
                _check_dependencies(dependencies)
            importlib.import_module(module_name)
        except (ImportPackageError, ModuleNotFoundError, Exception) as e:
            raise e
        return data_gen_template._template_instance_registry[template_name]

    @staticmethod
    def register(
        name: str, input_schema: type, input_example: str, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list
    ):
        """Decorator factory for registering data templates."""

        def decorator(func: callable):
            # Check if this is an import call (function already has _is_template flag)
            if name not in data_gen_template._template_instance_registry:
                data_gen_template._template_instance_registry[name] = Template(
                    name, func, input_schema, input_example, output_schema, description, author, starfish_version, dependencies
                )
            return func

        return decorator
