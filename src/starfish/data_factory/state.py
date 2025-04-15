import threading
from typing import Any, Dict, Optional

from pydantic import BaseModel


# from starfish.data_factory.utils.decorator import async_to_sync_event_loop
class MutableSharedState(BaseModel):
    _data: Dict[str, Any] = {}

    # If you want each MutableSharedState instance to have its own independent
    # synchronization, you should move the lock initialization into __init__.
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._lock = threading.Lock()  # Instance-level lock
        if initial_data is not None:
            self._data = initial_data.copy()

    # Use data when you want to emphasize you're accessing the current state
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

    # Use to_dict when you want to emphasize you're converting/serializing the state

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()


# # Set the entire state
# state.data = {"key": "value"}

# # Get the entire state
# current_state = state.data

# # Set a value
# state.set("key", "value")

# # Get a value
# value = state.get("key")

# # Update multiple values
# state.update({"key1": "value1", "key2": "value2"})

# # Get a copy of the entire state
# state_dict = state.to_dict()
