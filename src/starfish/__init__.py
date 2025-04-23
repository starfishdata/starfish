"""Starfish Core - A framework for structured data processing and LLM integration.

Provides core components for:
- StructuredLLM: Interface for working with large language models
- data_factory: Factory pattern for creating and managing data pipelines
"""

# Expose core directly from easy access
from .data_factory.factory import data_factory
from .llm.structured_llm import StructuredLLM

# Define what 'from starfish import *' imports (good practice)
__all__ = [
    "StructuredLLM",
    "data_factory",
]
