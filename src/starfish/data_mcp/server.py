"""
The Serena Model Context Protocol (MCP) Server
"""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from logging import Formatter, Logger, StreamHandler
from typing import Any, Literal

import click  # Add click import
import docstring_parser
from mcp.server.fastmcp import server
from mcp.server.fastmcp.server import FastMCP, Settings
from mcp.server.fastmcp.tools.base import Tool as MCPTool
from mcp.server.fastmcp.utilities.func_metadata import func_metadata
from loguru import logger  # Add this import

from starfish.data_mcp.agent import StarfishAgent, Tool

LOG_FORMAT = "%(levelname)-5s %(asctime)-15s %(name)s:%(funcName)s:%(lineno)d - %(message)s"
LOG_LEVEL = "INFO"  # Change to string for loguru compatibility


def configure_logging(*args, **kwargs) -> None:  # type: ignore
    """
    Configures logging to stderr with a specific format and level.

    This function replaces the default logging configuration in fastmcp to ensure
    logs are properly captured by Claude Desktop. Stdio cannot be used as it's
    reserved for MCP communication.
    """
    logger.remove()  # Remove default logger
    logger.add(sys.stderr, format=LOG_FORMAT, level=LOG_LEVEL)


# patch the logging configuration function in fastmcp, because it's hard-coded and broken
# server.configure_logging = configure_logging


@dataclass
class SerenaMCPRequestContext:
    agent: StarfishAgent


def make_tool(
    tool: Tool,
) -> MCPTool:
    """
    Converts a Starfish Tool into an MCP-compatible tool.

    Args:
        tool: The Starfish Tool to convert

    Returns:
        MCPTool: An MCP-compatible tool with proper metadata and documentation

    Raises:
        ValueError: If the tool doesn't have an apply method
    """
    func_name = tool.get_name()

    apply_fn = getattr(tool, "apply")
    if apply_fn is None:
        raise ValueError(f"Tool does not have an apply method: {tool}")

    func_doc = apply_fn.__doc__ or ""
    is_async = False

    func_arg_metadata = func_metadata(apply_fn)
    parameters = func_arg_metadata.arg_model.model_json_schema()

    docstring = docstring_parser.parse(func_doc)

    # Mount the tool description as a combination of the docstring description and
    # the return value description, if it exists.
    if docstring.description:
        func_doc = f"{docstring.description.strip().strip('.')}."
    else:
        func_doc = ""
    if (docstring.returns) and (docstring_returns := docstring.returns.description):
        # Only add a space before "Returns" if func_doc is not empty
        prefix = " " if func_doc else ""
        func_doc = f"{func_doc}{prefix}Returns {docstring_returns.strip().strip('.')}."

    # Parse the parameter descriptions from the docstring and add pass its description
    # to the parameters schema.
    docstring_params = {param.arg_name: param for param in docstring.params}
    parameters_properties: dict[str, dict[str, Any]] = parameters["properties"]
    for parameter, properties in parameters_properties.items():
        if (param_doc := docstring_params.get(parameter)) and (param_doc.description):
            param_desc = f"{param_doc.description.strip().strip('.') + '.'}"
            properties["description"] = param_desc[0].upper() + param_desc[1:]

    def execute_fn(**kwargs) -> str:  # type: ignore
        return tool.apply_ex(log_call=True, catch_exceptions=True, **kwargs)

    return MCPTool(
        fn=execute_fn,
        name=func_name,
        description=func_doc,
        parameters=parameters,
        fn_metadata=func_arg_metadata,
        is_async=is_async,
        context_kwarg=None,
    )


def create_mcp_server(host: str = "0.0.0.0", port: int = 8000) -> FastMCP:
    """
    Creates and configures an MCP server instance.

    Args:
        host: The host address to bind to (default: "0.0.0.0")
        port: The port number to bind to (default: 8000)

    Returns:
        FastMCP: A configured MCP server instance

    Raises:
        Exception: If there's an error creating the StarfishAgent
    """
    mcp: FastMCP | None = None

    try:
        agent = StarfishAgent()
    except Exception as e:
        raise e

    def update_tools() -> None:
        """
        Updates the tools registered with the MCP server.

        This function refreshes the available tools from the StarfishAgent and
        registers them with the MCP server. Note that tools are only registered
        at startup due to limitations in Claude Desktop's tool discovery.
        """
        nonlocal mcp, agent
        tools = agent.get_exposed_tools()
        if mcp is not None:
            mcp._tool_manager._tools = {}
            for tool in tools:
                mcp._tool_manager._tools[tool.get_name()] = make_tool(tool)

    mcp_settings = Settings(host=host, port=port)
    mcp = FastMCP(**mcp_settings.model_dump())

    update_tools()

    return mcp


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    show_default=True,
    help="Transport protocol.",
)
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
    show_default=True,
    help="Host to bind to (for SSE transport).",
)
@click.option(
    "--port",
    type=int,
    default=8000,
    show_default=True,
    help="Port to bind to (for SSE transport).",
)
def start_mcp_server(transport: Literal["stdio", "sse"], host: str, port: int) -> None:
    """Starts the Serena MCP server.

    Accepts the project file path either via the --project-file option or as a positional argument.
    """

    mcp_server = create_mcp_server(host=host, port=port)
    mcp_server.run(transport=transport)


if __name__ == "__main__":
    start_mcp_server()
