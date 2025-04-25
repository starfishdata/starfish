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

    # # Create templates directory if it doesn't exist
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Save the filtered module to a separate Python file
    function_file = templates_dir / f'{template_name.replace("/", "_")}.py'
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


# Update the existing decorator to use the new register function
data_template_generate.register = register
