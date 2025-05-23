import threading
from typing import Any, Dict, Optional

from pydantic import BaseModel


class MutableSharedState(BaseModel):
    """A thread-safe, mutable shared state container that allows concurrent access to shared data.

    This class provides a dictionary-like interface for storing and retrieving data with thread safety
    ensured by a lock mechanism. It's particularly useful in multi-threaded environments where
    multiple threads need to access and modify shared state.
    """

    _data: Dict[str, Any] = {}

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initializes a new MutableSharedState instance.

        Args:
            initial_data: Optional dictionary to initialize the state with. If provided,
                         the state will be initialized with a copy of this dictionary.
        """
        super().__init__()
        self._lock = threading.RLock()  # Changed to threading.Lock
        if initial_data is not None:
            self._data = initial_data.copy()

    # Use data when you want to emphasize you're accessing the current state
    @property
    def data(self) -> Dict[str, Any]:
        """Returns a copy of the current state as a dictionary."""
        return self.to_dict()

    @data.setter
    def data(self, value: Dict[str, Any]) -> None:
        """Sets the entire state with a new dictionary.

        Args:
            value: Dictionary containing the new state values
        """
        with self._lock:
            self._data = value.copy()

    def get(self, key: str) -> Any:
        """Retrieves a value from the state by key.

        Args:
            key: The key to look up in the state

        Returns:
            The value associated with the key, or None if the key doesn't exist
        """
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the state by key.

        Args:
            key: The key to set
            value: The value to associate with the key
        """
        with self._lock:
            self._data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """Updates multiple values in the state.

        Args:
            updates: Dictionary of key-value pairs to update
        """
        with self._lock:
            self._data.update(updates)

    # Use to_dict when you want to emphasize you're converting/serializing the state
    def to_dict(self) -> Dict[str, Any]:
        """Returns a copy of the current state as a dictionary.

        Returns:
            A copy of the current state dictionary
        """
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
