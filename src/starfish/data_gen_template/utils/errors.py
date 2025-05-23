class ImportPackageError(Exception):
    """Raised when a record is identified as a duplicate."""

    def __init__(self, message="data template import package error"):
        """Initialize the ImportPackageError with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Duplicate record detected".
        """
        self.message = f"data template : {message}"
        super().__init__(self.message)


class ImportModuleError(Exception):
    """Raised when a record is identified as a duplicate."""

    def __init__(self, message="data template import module error"):
        """Initialize the ImportPackageError with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Duplicate record detected".
        """
        self.message = f"data template : {message}"
        super().__init__(self.message)


class DataTemplateValueError(Exception):
    """Raised when a record is identified as a duplicate."""

    def __init__(self, message="data template value error"):
        """Initialize the ImportPackageError with a custom message.

        Args:
            message (str): The error message to display. Defaults to "Duplicate record detected".
        """
        self.message = f"data template : {message}"
        super().__init__(self.message)
