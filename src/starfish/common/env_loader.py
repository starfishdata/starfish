"""Environment variable loader utility.

This module provides functionality to load environment variables from a .env file
in non-production environments. In production, environment variables should be
set through the system/platform instead of using .env files for security reasons.

Uses python-dotenv for loading environment variables from .env files.
"""

import os
from typing import Optional

# Import python-dotenv
from dotenv import dotenv_values
from dotenv import find_dotenv as dotenv_find_dotenv
from dotenv import load_dotenv as dotenv_load_dotenv

from starfish.common.logger import get_logger

logger = get_logger(__name__)


def load_env_file(env_path: Optional[str] = None, override: bool = False) -> bool:
    """Load environment variables from .env file for non-production environments.

    Args:
        env_path: Path to the .env file. If None, looks for .env file in the current
                 working directory and parent directories.
        override: Whether to override existing environment variables. Default is False.

    Returns:
        True if environment variables were loaded, False otherwise.
    """
    # Skip loading in production environments
    if os.getenv("ENV") == "PROD":
        logger.info("Production environment detected. Skipping .env file loading.")

    # Find the .env file if path not provided
    if env_path is None:
        env_path = dotenv_find_dotenv(usecwd=True)
        if not env_path:
            logger.warning("No .env file found in the current or parent directories.")

    # Load environment variables
    loaded = dotenv_load_dotenv(dotenv_path=env_path, override=override)

    if loaded:
        # Get the loaded variables to count and log them
        loaded_vars = dotenv_values(env_path)
        logger.debug(f"Loaded {len(loaded_vars)} environment variables from {env_path}")
    else:
        logger.warning(f"Failed to load environment variables from {env_path}")
