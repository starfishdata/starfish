class DuplicateRecordError(Exception):
    """Raised when a record is identified as a duplicate"""
    def __init__(self, message="Duplicate record detected"):
        self.message = message
        super().__init__(self.message)

class FilterRecordError(Exception):
    """Raised when a record is filtered out based on business rules"""
    def __init__(self, message="Record filtered by business rules"):
        self.message = message
        super().__init__(self.message)
