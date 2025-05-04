from pathlib import Path
import importlib.metadata
from packaging import requirements
import pydantic
import importlib.util
import ast
from typing import Any, Union, List, Dict

from starfish.data_template.utils.error import DataTemplateValueError, ImportModuleError, ImportPackageError


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
        self, name: str, func: callable, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list[str]
    ):
        self.name = name
        self.func = func
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.description = description
        self.author = author
        self.starfish_version = starfish_version
        self.dependencies = dependencies

        # Add run method if not present
        if not hasattr(self.func, "run"):
            self.func.run = lambda *args, **kwargs: self.func(*args, **kwargs)

        # Check dependencies on initialization
        # if self.dependencies:
        #     _check_dependencies(self.dependencies)

    def run(self, *args, **kwargs) -> Any:
        """Execute the wrapped function with schema validation."""
        # Pre-run hook: Validate input schema
        try:
            # Validate input against schema
            if args:
                self.input_schema.validate(args[0])
            elif kwargs:
                self.input_schema.validate(kwargs)
        except pydantic.ValidationError as e:
            raise DataTemplateValueError(f"Input validation failed: {str(e)}")

        # Execute the function
        try:
            result = self.func.run(*args, **kwargs)
        except Exception as e:
            raise DataTemplateValueError(f"Template execution failed: {str(e)}")

        # Post-run hook: Validate output schema
        if self.output_schema is not None:
            try:
                self.output_schema.validate(result)
            except pydantic.ValidationError as e:
                raise DataTemplateValueError(f"Output validation failed: {str(e)}")

        return result


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
                if subdir.is_dir():
                    # Find all .py files in the subdirectory
                    for template_file in subdir.glob("*.py"):
                        try:
                            module_name = f"starfish.data_template.templates.{subdir.name}.{template_file.stem}"
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
    def register(name: str, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list):
        """Decorator factory for registering data templates."""

        def decorator(func: callable):
            # Check if this is an import call (function already has _is_template flag)
            if name not in data_gen_template._template_instance_registry:
                data_gen_template._template_instance_registry[name] = Template(
                    name, func, input_schema, output_schema, description, author, starfish_version, dependencies
                )
            return func

        return decorator
