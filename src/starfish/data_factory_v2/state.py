import threading
from typing import Any, Dict, Optional

from pydantic import BaseModel


class MutableSharedState(BaseModel):
    """Thread-safe mutable shared state container.

    Provides a dict-like interface with locking for concurrent access.
    Passed to hooks so they can read/write shared state.
    """

    _data: Dict[str, Any] = {}

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._lock = threading.RLock()
        if initial_data is not None:
            self._data = initial_data.copy()

    @property
    def data(self) -> Dict[str, Any]:
        return self.to_dict()

    @data.setter
    def data(self, value: Dict[str, Any]) -> None:
        with self._lock:
            self._data = value.copy()

    def get(self, key: str) -> Any:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        with self._lock:
            self._data.update(updates)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()
