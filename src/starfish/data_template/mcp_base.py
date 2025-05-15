from typing import Any, Dict, Callable
from mcp.server.fastmcp import FastMCP


class MCPProtocol:
    """
    Base class for Model Context Protocol (MCP) using FastMCP.
    Provides context management and tool registration capabilities.
    """

    def __init__(self, name: str):
        """
        Initialize the MCP protocol with a name and FastMCP instance.

        Args:
            name: A unique name for this MCP component.
        """
        self._name = name
        self._context: Dict[str, Any] = {}
        self._mcp = FastMCP(name)  # Initialize FastMCP with the component name

    def get_context(self) -> Dict[str, Any]:
        """
        Get the current context dictionary.

        Returns:
            Dict[str, Any]: The current context.
        """
        return self._context

    def set_context(self, context: Dict[str, Any]) -> None:
        """
        Set the context dictionary.

        Args:
            context: The new context dictionary.
        """
        self._context = context

    def update_context(self, key: str, value: Any) -> None:
        """
        Update a specific context value.

        Args:
            key: The key to update.
            value: The new value for the key.
        """
        self._context[key] = value

    def clear_context(self) -> None:
        """
        Clear the context dictionary.
        """
        self._context = {}

    def register_tool(self, func: Callable) -> Callable:
        """
        Register a function as an MCP tool.

        Args:
            func: The function to register as a tool.

        Returns:
            Callable: The registered function.
        """
        return self._mcp.tool()(func)

    def run(self, transport: str = "stdio") -> None:
        """
        Run the MCP component with the specified transport.

        Args:
            transport: The transport mode (e.g., "stdio").
        """
        self._mcp.run(transport=transport)
