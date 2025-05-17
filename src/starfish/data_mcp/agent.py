from abc import ABC
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Type, TypeVar, Union
from collections import defaultdict

from starfish.data_template.template_gen import data_gen_template
from starfish.common.logger import get_logger

logger = get_logger(__name__)
# Type variable for tool classes
TTool = TypeVar("TTool", bound="Tool")


def iter_subclasses(cls: Type) -> Generator[Type, None, None]:
    """Recursively iterate through all subclasses of a class."""
    for subclass in cls.__subclasses__():
        yield subclass
        yield from iter_subclasses(subclass)


class StarfishAgent:
    """
    A flexible agent framework that can be used in various scenarios.
    """

    def __init__(self, activation_callback: Optional[Callable[[], None]] = None):
        """
        Initialize the StarfishAgent with optional configuration.

        :param config_file_path: Path to a configuration file (YAML)
        :param activation_callback: Callback function when a context is activated
        """
        # Load configuration
        self._activation_callback = activation_callback

        # Discover and initialize all tools
        self._all_tools: Dict[Type[Tool], Tool] = {}
        self._discover_tools()

    def _discover_tools(self) -> None:
        """Discover and initialize all available tools."""
        for tool_class in iter_tool_classes():
            tool_instance = tool_class(self)
            self._all_tools[tool_class] = tool_instance
        self._active_tools = dict(self._all_tools)
        logger.info(f"Loaded tools ({len(self._all_tools)}): {', '.join([tool.get_name() for tool in self._all_tools.values()])}")

    def get_exposed_tools(self) -> List["Tool"]:
        """Return list of tools to be exposed to clients."""
        return list(self._active_tools.values())

    def get_tool(self, tool_class: Type[TTool]) -> TTool:
        """Get a tool instance by its class."""
        return self._all_tools[tool_class]  # type: ignore


class Component(ABC):
    """Base class for all components."""

    def __init__(self, agent: StarfishAgent):
        self.agent = agent


class Tool(Component):
    """Base class for all tools."""

    @classmethod
    def get_name(cls) -> str:
        """Get the name of the tool."""
        name = cls.__name__
        if name.endswith("Tool"):
            name = name[:-4]
        # Convert to snake_case
        name = "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
        return name

    def get_apply_fn(self) -> Callable:
        """Get the apply function of the tool."""
        apply_fn = getattr(self, "apply", None)
        if apply_fn is None:
            raise RuntimeError(f"apply not defined in {self}. Did you forget to implement it?")
        return apply_fn

    def get_tool_description(self) -> str:
        """Get the description of the tool."""
        return self.__class__.__doc__ or ""

    def get_function_description(self) -> str:
        """Get the description of the apply function."""
        apply_fn = self.get_apply_fn()
        return apply_fn.__doc__ or ""

    def apply_ex(self, log_call: bool = False, catch_exceptions: bool = False, **kwargs) -> str:
        """Execute the tool with the given arguments."""

        # Log the call if requested
        if log_call:
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            logger.info(f"Executing tool {self.get_name()}({args_str})")

        # Execute the tool
        try:
            result = self.get_apply_fn()(**kwargs)
            return result
        except Exception as e:
            error_msg = f"Error executing tool {self.get_name()}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if catch_exceptions:
                return error_msg
            raise


def iter_tool_classes(same_module_only: bool = True) -> Generator[type[Tool], None, None]:
    """
    Iterate over Tool subclasses.

    :param same_module_only: Whether to only iterate over tools defined in the same module as the Tool class
        or over all subclasses of Tool.
    """
    for tool_class in iter_subclasses(Tool):
        if same_module_only and tool_class.__module__ != Tool.__module__:
            continue
        yield tool_class


class ListDataGenTemplateTool(Tool):
    """Lists all available data generation templates."""

    def apply(self) -> List[str]:
        """Retrieves a list of all available data generation templates.

        Returns:
            List[str]: A list of template names that are available for use

        Raises:
            Exception: If template listing fails
        """
        try:
            return data_gen_template.list()
        except Exception as e:
            return f"Error executing template: {str(e)}"


# Example tool implementations
class GenerateCityInfoTool(Tool):
    """Reads a file from the filesystem."""

    def apply(self, template_name: str, input_data: Any) -> Any:
        """Run a template with provided input data.

        Args:
            template_name: Name of the template to execute
            input_data: Input data to pass to the template

        Returns:
            Results from the template execution

        Raises:
            Exception: If template execution fails
        """
        try:
            data_gen_template.list()
            topic_generator_temp = data_gen_template.get(template_name=template_name)
            result = topic_generator_temp.run(input_data)
            print(result)
            return result
        except Exception as e:
            return f"Error executing template: {str(e)}"


class ReadFileTool(Tool):
    """Reads a file from the filesystem"""

    def apply(self, path: str, max_chars: int = 200000) -> str:
        """Read the content of a file"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) > max_chars:
                return f"File too large (>{max_chars} chars)"
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"


class WebSearchTool(Tool):
    """Performs a web search"""

    def apply(self, query: str, max_results: int = 5) -> str:
        """Search the web for the given query"""
        # Implementation would depend on search API
        pass


class DatabaseQueryTool(Tool):
    """Executes a database query"""

    def apply(self, query: str, database: str) -> str:
        """Execute a query against the specified database"""
        # Implementation would depend on database connection
        pass
