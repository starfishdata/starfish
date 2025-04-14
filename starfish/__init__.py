
# Expose core directly from easy access
from .core.llm.structured_llm import StructuredLLM
from .core.data_factory.factory import data_factory


# Define what 'from starfish import *' imports (good practice)
__all__ = [
    "StructuredLLM",
    "data_factory",
]

# You might also include the package version here
# This is often automatically managed by build tools like setuptools_scm
try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("starfish-data") # Use the PyPI package name here
    except PackageNotFoundError:
            # package is not installed
        __version__ = "unknown"
except ImportError:
    # Fallback for older Python versions
    __version__ = "unknown"
