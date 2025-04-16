from enum import Enum


class RecordStatus(Enum):
    COMPLETED = "completed"
    DUPLICATE = "duplicate"
    FILTERED = "filtered"
    FAILED = "failed"
