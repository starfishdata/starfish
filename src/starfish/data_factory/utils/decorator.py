import asyncio
from typing import Callable

# from starfish.data_factory.constants import STORAGE_TYPE_LOCAL


def async_wrapper():
    """Decorator to handle storage-specific async operations."""

    # to be replaced by the registery pattern
    def decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            # if self.storage == STORAGE_TYPE_LOCAL:
            return asyncio.run(func(self, *args, **kwargs))

        return wrapper

    return decorator


def async_to_sync_event_loop():
    """Decorator to handle storage-specific async operations."""

    def decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            return asyncio.run(func(self, *args, **kwargs))

        return wrapper

    return decorator
