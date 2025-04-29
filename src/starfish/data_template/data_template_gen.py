import json
import inspect
from pathlib import Path
import importlib

# Class func_wrapper :
#     input_scheme
#     output_scheme
#     func

#     def __init__(self, func:callable):
#         self.func = func

#     def run:
#         pre-hook
#         func.run
#         post-hook


# ====================
# Registry Management
# ====================
_template_registry = {}
_template_instance_registry = {}
is_get_template = False


def _list() -> list[str]:
    """List all available templates in the format 'subfolder_name/template_name'."""
    # templates_dir = Path("starfish/templates")
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    result = list(_template_registry.keys())
    if len(result) == 0:
        global is_get_template
        is_get_template = False
        # Walk through all subdirectories in templates folder
        for subdir in templates_dir.iterdir():
            if subdir.is_dir():
                # Find all .py files in the subdirectory
                for template_file in subdir.glob("*.py"):
                    try:
                        # Import the module
                        module_name = f"starfish.templates.{subdir.name}.{template_file.stem}"
                        importlib.import_module(module_name)
                    except ImportError as e:
                        print(f"Warning: Could not import {template_file}: {e}")
                        continue

    # Return the registered templates from the registry
    return list(_template_registry.keys())


def _get(template_name: str) -> callable:
    """Get a template function by its name."""
    if template_name not in _template_registry:
        raise ValueError(f"Template {template_name} not found")
    # Get the file path and metadata
    module_name = _template_registry[template_name]
    module = importlib.import_module(module_name)
    global is_get_template
    is_get_template = True
    module = importlib.reload(module)  # Force reload the module
    return _template_instance_registry[template_name]


def _register(name: str, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list):
    """Decorator factory for registering data templates."""

    def decorator(func: callable):
        # Check if this is an import call (function already has _is_template flag)
        global is_get_template
        if is_get_template:
            if name not in _template_instance_registry:
                _template_instance_registry[name] = data_template_generate(
                    func, input_schema, output_schema, description, author, starfish_version, dependencies
                )
        else:
            original_func = func
            if hasattr(original_func, "__func__"):
                original_func = original_func.__func__
            module_name = original_func.__module__
            # Store metadata and file path
            _template_registry[name] = str(module_name)

    return decorator


# ====================
# Template Generation
# ====================
def data_template_generate(func: callable, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list):
    """Generate a template instance with the provided metadata and function."""
    return Template(func, input_schema, output_schema, description, author, starfish_version, dependencies)


# Attach registry methods to data_template_generate
data_template_generate.register = _register
data_template_generate.list = _list
data_template_generate.get = _get


# ====================
# Template Class
# ====================
class Template:
    """Wrapper class for template functions with metadata and execution capabilities."""

    def __init__(self, func: callable, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list):
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

    def run(self, *args, **kwargs):
        """Execute the wrapped function."""
        return self.func.run(*args, **kwargs)
