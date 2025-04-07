import os
import sys
from enum import IntEnum

from loguru import logger

default_log_level = os.getenv("LOG_LEVEL", "INFO")


# Define custom log levels
class LogLevel(IntEnum):
    VERBOSE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# Configuration Constants
COLORED_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> | "
    "<blue>{file}:{line}</blue> | "
    "<level>{message}</level>"
)


class LogManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance.handler_id = None
            cls._instance.current_level = default_log_level
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize logging with console handler."""
        logger.remove()  # Remove default handler
        self.handler_id = logger.add(sys.stdout, format=COLORED_FORMAT, level=self.current_level, colorize=True)
        # Add custom level
        logger.level("VERBOSE", no=LogLevel.VERBOSE, color="<magenta>")

    def get_current_log_level(self):
        """Get the current log level."""
        return self.current_level

    def update_log_level(self, level):
        """Update the log level of the console handler.
        This can be called at any time during runtime to change the log level.
        """
        level = level.upper()
        if level not in ["VERBOSE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {level}")
        logger.remove(self.handler_id)
        self.current_level = level
        self.handler_id = logger.add(sys.stdout, format=COLORED_FORMAT, level=self.current_level, colorize=True)


# Instantiate LogManager to ensure logging is initialized on module import
log_manager = LogManager()


# Add verbose method to logger
def verbose(self, message, *args, **kwargs):
    self.log("VERBOSE", message, *args, **kwargs)


logger.__class__.verbose = verbose


# Function to get the logger
def get_logger(name):
    return logger.bind(name=name)
