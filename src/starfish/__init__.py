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

# You might also include the package version here
# This is often automatically managed by build tools like setuptools_scm
try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("starfish-core")  # Updated to match our package name
    except PackageNotFoundError:
        # package is not installed
        __version__ = "unknown"
except ImportError:
    # Fallback for older Python versions
    __version__ = "unknown"

# src/starfish/__init__.py
# try:
#     from ._version import version as __version__
# except ImportError:
#     __version__ = "unknown"
