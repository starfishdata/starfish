import typer
from pathlib import Path
from typing import Optional
from starfish.data_gen_template.core import data_gen_template

app = typer.Typer(help="Data Template CLI")


@app.command()
def list_templates(detail: bool = False):
    """List all available templates"""
    templates = data_gen_template.list(is_detail=detail)
    if detail:
        for template in templates:
            typer.echo(f"Template: {template['name']}")
            typer.echo(f"  Description: {template['description']}")
            typer.echo(f"  Author: {template['author']}")
            typer.echo(f"  Version: {template['starfish_version']}")
            typer.echo(f"  Dependencies: {', '.join(template.get('dependencies', []))}")
            typer.echo()
    else:
        for template in templates:
            typer.echo(template)


@app.command()
def get_template(name: str):
    """Get details about a specific template"""
    try:
        data_gen_template.list()
        template = data_gen_template.get(name)
        typer.echo(f"Template: {template.name}")
        typer.echo(f"Description: {template.description}")
        typer.echo(f"Author: {template.author}")
        typer.echo(f"Version: {template.starfish_version}")
        typer.echo(f"Dependencies: {', '.join(template.dependencies)}")
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)


# @app.command()
# def export_template(name: str, output_path: str):
#     """Export a template to a specific path"""
#     try:
#         template = data_gen_template.get(name)
#         exported_path = template.export(output_path)
#         typer.echo(f"Template exported to: {exported_path}")
#     except Exception as e:
#         typer.echo(f"Error: {str(e)}", err=True)


@app.command()
def run_template(
    name: str,
    input_file: Optional[Path] = typer.Option(None, help="Path to JSON file with input data"),
    output_file: Optional[Path] = typer.Option(None, help="Path to save output to"),
):
    """Run a template with the provided input data"""
    try:
        data_gen_template.list()
        template = data_gen_template.get(name)

        # Load input data
        if input_file:
            import json

            with open(input_file) as f:
                input_data = json.load(f)
        else:
            typer.echo("Please enter the input data (JSON format):")
            input_data = json.loads(typer.prompt("Input data"))

        # Run the template
        import asyncio

        result = asyncio.run(template.run(input_data=input_data))

        # Handle output
        if output_file:
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            typer.echo(f"Output saved to {output_file}")
        else:
            typer.echo(json.dumps(result, indent=2))

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)


@app.command()
def print_schema(name: str):
    """Print the input schema for a template"""
    try:
        data_gen_template.list()
        template = data_gen_template.get(name)
        template.print_schema()
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)


@app.command()
def print_example(name: str):
    """Print an example input for a template"""
    try:
        data_gen_template.list()
        template = data_gen_template.get(name)
        template.print_example()
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)


def main():
    app()


if __name__ == "__main__":
    main()
