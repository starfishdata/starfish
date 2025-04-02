
from fastapi import APIRouter
from pydantic import BaseModel, Field
from enum import Enum
from starfish.common.logger import get_logger, log_manager

router = APIRouter()
logger = get_logger(__name__)

class LogLevelEnum(str, Enum):
    verbose = "VERBOSE"
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"

    @classmethod
    def _missing_(cls, value):
        try:
            return cls[value.upper()]
        except KeyError:
            return None


class LogLevelRequest(BaseModel):
    level: LogLevelEnum = Field(..., description="Log level (case-insensitive)")


@router.get("/log-level")
async def get_log_level():
    """Get the current log level."""
    current_level = log_manager.get_current_log_level()
    logger.info(f"Current log level retrieved: {current_level}")
    return {"current_log_level": current_level}


@router.post("/log-level")
async def set_log_level(log_level: LogLevelRequest):
    """Set the log level."""
    log_manager.update_log_level(log_level.level.value)
    new_level = log_manager.get_current_log_level()
    logger.info(f"Log level changed to: {new_level}")
    return {"message": f"Log level set to {new_level}"}