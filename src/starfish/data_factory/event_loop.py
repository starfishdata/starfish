import asyncio

import nest_asyncio

from starfish.common.logger import get_logger

logger = get_logger(__name__)


def run_in_event_loop(coroutine):
    """Run a coroutine in the event loop, handling both nested and new loop cases.

    Args:
        coroutine: The coroutine to be executed

    Returns:
        The result of the coroutine execution

    Note:
        If an event loop is already running, nest_asyncio will be used to allow
        nested execution. If no loop is running, a new event loop will be created.
    """
    try:
        # This call will raise an RuntimError if there is no event loop running.
        asyncio.get_running_loop()

        # If there is an event loop running (the call above doesn't raise an exception), we can use nest_asyncio to patch the event loop.
        nest_asyncio.apply()
        logger.debug(f"Running nested coroutine: {coroutine.__name__}")
    except RuntimeError as e:
        # If no event loop is running, asyncio
        # Explicitly pass, since we want to fallback to asyncio.run
        logger.debug(str(e))
        logger.debug(f"Running coroutine: {coroutine.__name__}")
    return asyncio.run(coroutine)
