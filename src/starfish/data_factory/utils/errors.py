import asyncio


class DuplicateRecordError(Exception):
    """Raised when a record is identified as a duplicate."""

    def __init__(self, message="Duplicate record detected"):
        """Initialize the DuplicateRecordError with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Duplicate record detected".
        """
        self.message = message
        super().__init__(self.message)


class RecordError(Exception):
    """Raised when a record is not processed successfully."""

    def __init__(self, message="Record not processed successfully"):
        """Initialize the RecordError with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Record not processed successfully".
        """
        self.message = message
        super().__init__(self.message)


class FilterRecordError(Exception):
    """Raised when a record is filtered out based on business rules."""

    def __init__(self, message="Record filtered by business rules"):
        """Initialize the FilterRecordError with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Record filtered by business rules".
        """
        self.message = message
        super().__init__(self.message)


class TimeoutErrorAsyncio(asyncio.TimeoutError):
    """Raised when a task execution times out."""

    def __init__(self, message="Task execution timed out"):
        """Initialize the TimeoutErrorAsyncio with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Task execution timed out".
        """
        self.message = message
        super().__init__(self.message)
