from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio

class MutableSharedState(BaseModel):
    _data: Dict[str, Any] = {}
    #If you want each MutableSharedState instance to have its own independent 
    # synchronization, you should move the lock initialization into __init__.
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._lock = asyncio.Lock()  # Instance-level lock
        if initial_data is not None:
            self._data = initial_data.copy()

    # Use data when you want to emphasize you're accessing the current state
    @property
    async def data(self) -> Dict[str, Any]:
        return await self.to_dict()

    @data.setter
    async def data(self, value: Dict[str, Any]) -> None:
        async with self._lock:
            self._data = value.copy()

    async def get(self, key: str) -> Any:
        async with self._lock:
            return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._data[key] = value

    async def update(self, updates: Dict[str, Any]) -> None:
        async with self._lock:
            self._data.update(updates)

    # Use to_dict when you want to emphasize you're converting/serializing the state
    async def to_dict(self) -> Dict[str, Any]:
        async with self._lock:
            return self._data.copy()

# # Set the entire state
# await state.data = {"key": "value"}

# # Get the entire state
# current_state = await state.data

# # Set a value
# await state.set("key", "value")

# # Get a value
# value = await state.get("key")

# # Update multiple values
# await state.update({"key1": "value1", "key2": "value2"})

# # Get a copy of the entire state
# state_dict = await state.to_dict()
