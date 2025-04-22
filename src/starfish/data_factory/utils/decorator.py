from typing import Callable

from starfish.data_factory.event_loop import run_in_event_loop

# from starfish.data_factory.constants import STORAGE_TYPE_LOCAL


def async_wrapper_func():
    """Decorator to convert synchronous functions to asynchronous execution.

    Returns:
        Callable: A decorator that wraps the target function with async execution.
    """

    # to be replaced by the registery pattern
    def decorator(func: Callable):
        """Inner decorator that wraps the target function.

        Args:
            func (Callable): The function to be wrapped for async execution.

        Returns:
            Callable: Wrapped function that runs synchronously but executes the original
                     function asynchronously.
        """

        def wrapper(*args, **kwargs):
            """Wrapper function that handles the async execution.

            Args:
                *args: Positional arguments passed to the original function.
                **kwargs: Keyword arguments passed to the original function.

            Returns:
                Any: The result of the original function execution.
            """
            return run_in_event_loop(func(*args, **kwargs))

    return decorator


def async_wrapper():
    """Decorator to convert class methods to asynchronous execution.

    Returns:
        Callable: A decorator that wraps the target method with async execution.
    """

    # to be replaced by the registery pattern
    def decorator(func: Callable):
        """Inner decorator that wraps the target method.

        Args:
            func (Callable): The method to be wrapped for async execution.

        Returns:
            Callable: Wrapped method that runs synchronously but executes the original
                     method asynchronously.
        """

        def wrapper(self, *args, **kwargs):
            """Wrapper function that handles the async execution for class methods.

            Args:
                self: The class instance.
                *args: Positional arguments passed to the original method.
                **kwargs: Keyword arguments passed to the original method.

            Returns:
                Any: The result of the original method execution.
            """
            # if self.storage == STORAGE_TYPE_LOCAL:
            return run_in_event_loop(func(self, *args, **kwargs))

        return wrapper

    return decorator
