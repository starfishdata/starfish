from enum import Enum, auto

class RecordStatus(Enum):
    COMPLETED = auto()
    DUPLICATE = auto()
    FILTERED = auto()
    FAILED = auto()