import asyncio
import functools
from typing import Callable, TypeVar, Union, cast

from starfish.common.logger import get_logger

logger = get_logger(__name__)

# Type variable for generic return types
T = TypeVar("T")


def retries(max_retries: Union[int, Callable[..., int]] = 3):
    """Decorator to add retry logic to async functions.

    Args:
        max_retries: Maximum number of retry attempts, either a fixed integer
                    or a callable that returns an integer when invoked with
                    the same arguments as the decorated function.

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Determine max retries - either use the fixed value or call the function
            retries = max_retries(*args, **kwargs) if callable(max_retries) else max_retries

            if retries is None or retries < 1:
                logger.warning(f"Invalid max_retries value: {retries}, defaulting to 1")
                retries = 1

            last_exception = None

            for attempt in range(retries):
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    logger.error(f"Error on attempt {attempt+1}/{retries}: {str(e)}")

                    if attempt < retries - 1:
                        logger.info(f"Retrying... (attempt {attempt+2}/{retries})")
                    else:
                        logger.error(f"All {retries} attempts failed")
                        raise last_exception

            # This should never be reached due to the raise above
            assert last_exception is not None
            raise last_exception

        return cast(Callable[..., T], wrapper)

    return decorator


def to_sync(async_func):
    """Decorator to make async functions synchronous.

    This converts an async function into a sync function that can be called normally.
    For Jupyter notebooks, it provides a clear error message if nest_asyncio is needed.

    """

    @functools.wraps(async_func)
    def sync_wrapper(*args, **kwargs):
        try:
            return asyncio.run(async_func(*args, **kwargs))
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                raise RuntimeError(
                    "This function can't be called in Jupyter without nest_asyncio. " "Please add 'import nest_asyncio; nest_asyncio.apply()' to your notebook."
                )
            raise

    return sync_wrapper


def merge_structured_outputs(*lists):
    """Merge multiple lists of dictionaries element-wise.
    Assumes all lists have the same length.
    Raises an error if there are key conflicts.
    """
    if not lists:
        return []

    merged_list = []
    for elements in zip(*lists, strict=False):
        merged_dict = {}
        for d in elements:
            if any(key in merged_dict for key in d):
                raise ValueError(f"Key conflict detected in {elements}")
            merged_dict.update(d)
        merged_list.append(merged_dict)
    return merged_list
