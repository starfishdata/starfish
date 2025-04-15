from typing import Callable
import asyncio
from starfish.data_factory.constants import STORAGE_TYPE_LOCAL

def storage_action():
    """Decorator to handle storage-specific async operations"""
    # to be replaced by the registery pattern
    def decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            if self.storage == STORAGE_TYPE_LOCAL:
                return asyncio.run(func(self, *args, **kwargs))
        return wrapper
    return decorator