import functools
import os
import traceback
import uuid
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

from starfish.common.logger import get_logger

logger = get_logger(__name__)

# Simple configuration flag (can be set from app config)
# Default to False for production safety
INCLUDE_TRACEBACK_IN_RESPONSE = os.environ.get("INCLUDE_TRACEBACK_IN_RESPONSE", False)

#############################################
# HTTP Status Codes
#############################################


class HTTPStatus:
    """Standard HTTP status codes."""

    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500


#############################################
# Error Response Model
#############################################


class ErrorResponse(BaseModel):
    """Standardized error response format for API errors."""

    status: str = "error"
    error_id: str = Field(..., description="Unique identifier for this error occurrence")
    message: str
    error_type: str
    details: Optional[Dict[str, Any]] = None


#############################################
# Exception Classes
#############################################


class StarfishException(Exception):
    """Base exception for all Starfish exceptions."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected error occurred"

    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message or self.default_message
        self.details = details
        self.error_id = str(uuid.uuid4())
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ValidationError(StarfishException):
    """Exception raised for validation errors."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    default_message = "Validation error"


class PydanticValidationError(ValidationError):
    """Exception raised for Pydantic validation errors.

    This class formats Pydantic validation errors into user-friendly messages
    and preserves the detailed error information for debugging.
    """

    default_message = "Data validation error"

    @staticmethod
    def format_validation_error(error: ValidationError) -> Tuple[str, Dict[str, Any]]:
        """Format a Pydantic ValidationError into a user-friendly message and details.

        Args:
            error: The Pydantic ValidationError to format

        Returns:
            Tuple of (message, details)
        """
        if not hasattr(error, "errors") or not callable(getattr(error, "errors", None)):
            return str(error), {}

        error_details = error.errors()
        if not error_details:
            return "Validation error", {}

        # Format fields with errors
        field_errors = []
        for err in error_details:
            # Get error type and location
            err_type = err.get("type", "unknown")
            loc = err.get("loc", [])

            # Special handling for discriminated unions
            # If first element is a string and subsequent elements exist, might be a discriminated union
            if len(loc) >= 2 and isinstance(loc[0], str) and isinstance(loc[1], str):
                # This might be a discriminated union error like ['vanilla', 'user_input']
                type_name = loc[0]
                field_name = loc[1]

                # Handle errors differently based on type
                if err_type == "missing":
                    field_errors.append(f"Field '{field_name}' is required for '{type_name}' type")
                    continue

            # Standard handling for other errors
            loc_str = ".".join(str(item) for item in loc) if loc else "unknown"
            msg = err.get("msg", "")

            # Create a user-friendly error message based on error type
            if err_type == "missing":
                field_errors.append(f"'{loc_str}' is required")
            elif err_type == "type_error":
                field_errors.append(f"'{loc_str}' has an invalid type")
            elif err_type == "value_error":
                field_errors.append(f"'{loc_str}' has an invalid value")
            elif err_type.startswith("value_error"):
                field_errors.append(f"'{loc_str}' {msg}")
            elif err_type.startswith("type_error"):
                field_errors.append(f"'{loc_str}' {msg}")
            elif err_type == "extra_forbidden":
                field_errors.append(f"'{loc_str}' is not allowed")
            else:
                field_errors.append(f"'{loc_str}': {msg}")

        # Create a combined message
        if len(field_errors) == 1:
            message = f"Validation error: {field_errors[0]}"
        else:
            message = f"Validation errors: {', '.join(field_errors)}"

        return message, {"validation_errors": error_details}

    def __init__(self, validation_error: ValidationError, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        # Format the validation error if no message is provided
        if message is None:
            message, error_details = self.format_validation_error(validation_error)

            # Merge error details with provided details
            if details is None:
                details = error_details
            else:
                details = {**details, **error_details}

        super().__init__(message=message, details=details)


class ParserError(StarfishException):
    """Base exception for all parser-related errors."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    default_message = "Parser error"


class JsonParserError(ParserError):
    """Exception raised when JSON parsing fails."""

    default_message = "JSON parsing error"


class SchemaValidationError(ParserError):
    """Exception raised when data doesn't conform to schema."""

    default_message = "Schema validation error"

    def __str__(self):
        if self.details and "errors" in self.details:
            errors_text = "\n".join([f"- {err}" for err in self.details["errors"]])
            return f"{self.message}:\n{errors_text}"
        return super().__str__()


class PydanticParserError(ParserError):
    """Exception raised when Pydantic parsing or validation fails."""

    default_message = "Pydantic parsing error"


#############################################
# Error Handling Functions
#############################################


def format_error(exc: Exception, include_traceback: bool = INCLUDE_TRACEBACK_IN_RESPONSE) -> Tuple[ErrorResponse, int]:
    """Format an exception into a standardized error response.

    Args:
        exc: The exception to format
        include_traceback: Whether to include traceback in the response details

    Returns:
        Tuple of (error_response, status_code)
    """
    # Get traceback for logging (always) - may optionally include in response
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Check for exception chaining
    cause = getattr(exc, "__cause__", None)
    cause_tb = None
    if cause:
        cause_tb = "".join(traceback.format_exception(type(cause), cause, cause.__traceback__))
        logger.error(f"Original exception: {type(cause).__name__}: {str(cause)}")
        logger.error(f"Original traceback: {cause_tb}")

    # Log the current exception
    logger.error(f"Exception: {type(exc).__name__}: {str(exc)}")
    logger.error(f"Traceback: {tb_str}")

    # Handle Starfish exceptions
    if isinstance(exc, StarfishException):
        error_id = getattr(exc, "error_id", str(uuid.uuid4()))
        status_code = exc.status_code
        details = exc.details or {}

        # Only add traceback to details if requested
        if include_traceback:
            details["traceback"] = tb_str
            if cause_tb:
                details["original_traceback"] = cause_tb

        return ErrorResponse(error_id=error_id, message=exc.message, error_type=type(exc).__name__, details=details if details else None), status_code

    # Handle Pydantic validation errors
    elif isinstance(exc, ValidationError):
        error_id = str(uuid.uuid4())
        status_code = HTTPStatus.UNPROCESSABLE_ENTITY
        details = {"validation_errors": exc.errors()}

        if include_traceback:
            details["traceback"] = tb_str
            if cause_tb:
                details["original_traceback"] = cause_tb

        return ErrorResponse(error_id=error_id, message="Validation error", error_type="ValidationError", details=details), status_code

    # Handle all other exceptions
    else:
        error_id = str(uuid.uuid4())
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        details = {}

        if include_traceback:
            details["traceback"] = tb_str
            if cause_tb:
                details["original_traceback"] = cause_tb

        return ErrorResponse(
            error_id=error_id, message=str(exc) or "An unexpected error occurred", error_type=type(exc).__name__, details=details if details else None
        ), status_code


#############################################
# Utility Decorators
#############################################


def handle_exceptions(return_value=None):
    """Decorator to handle exceptions in both async and sync functions.

    This decorator can be used with any function to catch exceptions,
    log them, and return a default value instead of raising.

    Args:
        return_value: The value to return if an exception occurs

    Returns:
        Decorated function with exception handling
    """

    def decorator(func):
        # Import asyncio here to avoid dependency if not needed
        try:
            import asyncio

            is_async_available = True
        except ImportError:
            is_async_available = False

        # Handle async functions
        if is_async_available and asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    # Format and log the error but don't raise
                    format_error(exc, include_traceback=True)
                    return return_value

            return async_wrapper

        # Handle synchronous functions
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    # Format and log the error but don't raise
                    format_error(exc, include_traceback=True)
                    return return_value

            return sync_wrapper

    return decorator
