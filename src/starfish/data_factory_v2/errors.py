import asyncio


class InputError(Exception):
    """Input data does not match expected format."""

    def __init__(self, message="Input does not match expected format"):
        super().__init__(message)


class OutputError(Exception):
    """No output was generated."""

    def __init__(self, message="No result was generated"):
        super().__init__(message)


class TaskTimeoutError(asyncio.TimeoutError):
    """Task execution timed out."""

    def __init__(self, message="Task execution timed out"):
        self.message = message
        super().__init__(message)


class NoResumeSupportError(Exception):
    """Function cannot be serialized for resume."""

    def __init__(self, message="Function does not support resume. Ensure it supports cloudpickle serialization."):
        super().__init__(message)
