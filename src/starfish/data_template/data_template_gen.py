import json
import inspect
from pathlib import Path


def data_template_generate(
    template_name: str, func: callable, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list
):
    """Generate and store a data template for a given function."""
    # Handle decorated functions by checking for closure
    original_func = func
    if hasattr(original_func, "__func__"):
        original_func = original_func.__func__
    # Get the file path of the original function
    current_file_path = Path(original_func.__code__.co_filename).resolve()

    # Split template_name and create subfolder structure
    template_parts = template_name.split("/")
    if len(template_parts) != 2:
        raise ValueError("template_name must be in format 'folder_name/template_name'")

    # Create templates directory and subdirectory
    templates_dir = Path("templates") / template_parts[0]
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Save the filtered module to a separate Python file
    function_file = templates_dir / f"{template_parts[1]}.py"
    with open(current_file_path, "r") as src_file, open(function_file, "w") as dest_file:
        dest_file.write(f"# Auto-generated module from template: {template_name}\n")
        skip = False
        for line in src_file:
            # Skip the import line for data_template_generate
            if "import data_template_generate" in line:
                continue
            # Skip the decorator line
            elif line.strip().startswith("@data_template_generate.register"):
                skip = True
            # Stop skipping when we hit the next function definition
            elif (
                skip and line.startswith(("def ", "@data_factory")) and not (line.startswith("def data_template_generate(") or line.startswith("def register("))
            ):
                skip = False
            # Write all other lines
            if not skip:
                dest_file.write(line)

    return func


def register(name: str, input_schema: type, output_schema: type, description: str, author: str, starfish_version: str, dependencies: list):
    """Decorator factory for registering data templates."""

    def decorator(func: callable):
        return data_template_generate(name, func, input_schema, output_schema, description, author, starfish_version, dependencies)

    return decorator


def list() -> list[str]:
    """List all available templates in the format 'subfolder_name/template_name'."""
    templates_dir = Path("templates")
    if not templates_dir.exists():
        return []

    templates = []
    for subfolder in templates_dir.iterdir():
        if subfolder.is_dir():
            for template_file in subfolder.glob("*.py"):
                if template_file.is_file():
                    templates.append(f"{subfolder.name}/{template_file.stem}")
    return templates


def get(template_path: str) -> callable:
    """Get a template function by its path.

    Args:
        template_path: Path to template in format 'folder_name/template_name'

    Returns:
        The template function
    """
    # Split the template path
    template_parts = template_path.split("/")
    if len(template_parts) != 2:
        raise ValueError("template_path must be in format 'folder_name/template_name'")

    # Import the module
    module_name = f"templates.{template_parts[0]}.{template_parts[1]}"
    try:
        module = __import__(module_name, fromlist=[template_parts[1]])
        func = getattr(module, template_parts[1])
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Failed to import template {template_path}: {str(e)}")

    # Verify the function has a run method
    if not hasattr(func, "run"):
        raise ValueError(f"Template {template_path} does not have a run method")

    return func


# def run(template_path: str, input_data: dict):
#     """Run a template with the given input data.

#     Args:
#         template_path: Path to template in format 'folder_name/template_name'
#         input_data: Input data dictionary to pass to the template
#     """
#     func = get(template_path)
#     return func.run(input_data)


# Update the existing decorator to use the new register function
data_template_generate.register = register
data_template_generate.list = list
data_template_generate.get = get
