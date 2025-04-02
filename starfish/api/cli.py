"""
CLI commands for Starfish.
Currently focused on API server functionality.
"""
import typer
import sys

from starfish.common.logger import get_logger
from starfish.common.exceptions import StarfishException
from starfish.api.server import run_server

logger = get_logger(__name__)

# Create the main Typer app
app = typer.Typer(
    name="starfish",
    help="Starfish CLI - A tool for data generation using LLMs",
    add_completion=False
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Starfish CLI - A tool for data generation using LLMs"""
    # Only show welcome message if no subcommand was invoked
    if ctx.invoked_subcommand is None:
        typer.echo(f"🐠 Welcome to Starfish CLI! v0.1.0")
        typer.echo("A tool for data generation using LLMs\n")
        
        # Display available commands
        typer.echo("Available commands:")
        commands = [command for command in ctx.command.commands]
        for command in commands:
            cmd_help = ctx.command.commands[command].help or ""
            typer.echo(f"  {command:<20} {cmd_help}")
        
        typer.echo("\nRun 'starfish [COMMAND] --help' for more information on a command.")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to run the server on"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the server on"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload for development"),
    log_level: str = typer.Option("info", "--log-level", help="Logging level"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes (ignored when reload=True)")
):
    """Start the Starfish API server"""
    try:
        # Warn if both workers > 1 and reload are specified
        if workers > 1 and reload:
            logger.warning("Multiple workers cannot be used with reload mode. Setting workers=1.")
            workers = 1
            
        run_server(host=host, port=port, reload=reload, log_level=log_level, workers=workers)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except StarfishException as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)

def main():
    """Entry point for CLI when run as a module"""
    app()

if __name__ == "__main__":
    main() 