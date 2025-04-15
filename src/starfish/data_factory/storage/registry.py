"""Central registry for component factories.
This module contains the registries used for component factories.
"""

from typing import Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from starfish.common.logger import get_logger

logger = get_logger(__name__)

# Define the base type for components
T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry for component factories.

    This registry allows for lazy registration of component factories
    and prevents circular imports by decoupling registration from implementation.

    It also supports associating input models with component implementations.
    """

    def __init__(self, base_type: Type[T]):
        self._registry: Dict[str, Callable[..., T]] = {}
        self._input_models: Dict[str, Type[BaseModel]] = {}
        self._base_type = base_type

    def register(self, name: str, input_model: Optional[Type[BaseModel]] = None, factory_func: Callable[..., T] = None) -> Callable:
        """Register a component factory function with an optional input model.

        Can be used as:
            @registry.register("name", input_model=MyModel)
            def factory_func(): ...

        Args:
            name: The name to register the factory under
            input_model: Optional Pydantic model used for validating input to the component
            factory_func: The factory function that creates the component

        Returns:
            The factory function for decorator usage
        """

        def decorator(func):
            logger.debug(f"Registering type: {name}")
            self._registry[name] = func
            if input_model:
                logger.debug(f"Associating input model {input_model.__name__} with {name}")
                self._input_models[name] = input_model
            return func

        if factory_func is None:
            # Called as @register("name", input_model=...)
            return decorator
        else:
            # Called as register("name", input_model=..., factory_func=...)
            self._registry[name] = factory_func
            if input_model:
                self._input_models[name] = input_model
            return factory_func

    def create(self, config) -> T:
        """Create a component instance using a config object.

        Args:
            config: Either a Pydantic model with a 'type' attribute,
                or a dictionary with a 'type' key

        Returns:
            An instance of the component
        """
        # Extract the type from config
        if isinstance(config, dict):
            type_name = config.get("type")
            dict_config = config
        elif hasattr(config, "type"):
            type_name = config.type
            # If it's already a Pydantic model, use it directly
            parsed_config = config
            dict_config = None
        else:
            raise ValueError("Config must have a 'type' attribute")

        if not type_name:
            raise ValueError("Config must specify a 'type'")

        # Lazy import handling
        if type_name not in self._registry:
            try:
                module_name = self._get_module_name(type_name)
                logger.debug(f"Attempting to import {module_name}")
                __import__(module_name)
            except ImportError as e:
                logger.debug(f"Failed to import {type_name}: {e}")
                pass

        if type_name not in self._registry:
            raise ValueError(f"Unknown {self._base_type.__name__} type: {type_name}")

        # Get the factory function
        factory_func = self._registry[type_name]

        # If we have a dictionary config and an input model, validate it
        if dict_config is not None:
            input_model = self._input_models.get(type_name)
            if input_model:
                # Validate using the input model - pass the entire dictionary
                parsed_config = input_model(**dict_config)
            else:
                # No model, just use the dict directly
                parsed_config = dict_config

        # Return the result of the factory function with our parsed config
        return factory_func(parsed_config)

    def _get_module_name(self, type_name: str) -> str:
        """Get the module name to import for a given type name.

        Current pattern supports components that are two levels deep under the "data_factory" folder:
        e.g., starfish.data_factory.storage.prefixed_filesystem for prefixed_filesystem storage type

        Args:
            type_name: The name of the type to get the module for

        Returns:
            The module path to import
        """
        base_module = self._base_type.__module__

        # Components under core/ folder (standard pattern)
        module_parts = base_module.split(".")
        core_index = module_parts.index("data_factory")

        # Get the component type (e.g., "storage" from "starfish.data_factory.storage.base")
        if core_index + 1 < len(module_parts):
            component_type = module_parts[core_index + 1]
            return f"starfish.data_factory.{component_type}.{type_name}"

    def get_input_model(self, type_name: str) -> Optional[Type[BaseModel]]:
        """Get the input model associated with a component type.

        Args:
            type_name: The name of the component type

        Returns:
            The associated input model class, or None if no model is registered
        """
        # Try to import the module if not already registered
        if type_name not in self._registry and type_name not in self._input_models:
            try:
                module_name = self._get_module_name(type_name)
                logger.debug(f"Attempting to import {module_name} for input model")
                __import__(module_name)
            except ImportError as e:
                logger.debug(f"Failed to import {type_name} for input model: {e}")
                pass

        return self._input_models.get(type_name)

    def get_available_types(self) -> List[str]:
        """Get all registered component types."""
        return list(self._registry.keys())

    def get_all_input_models(self) -> Dict[str, Type[BaseModel]]:
        """Get all registered input models.

        Returns:
            A dictionary mapping component type names to their input models
        """
        # Return a copy to prevent external modification
        return self._input_models.copy()
