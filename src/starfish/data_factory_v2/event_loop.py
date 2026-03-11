import asyncio
import sys

from starfish.common.logger import get_logger

logger = get_logger(__name__)

_NEST_ASYNCIO_APPLIED = False


def _ensure_nest_asyncio():
    """Apply nest_asyncio if running in a notebook or existing event loop."""
    global _NEST_ASYNCIO_APPLIED
    if _NEST_ASYNCIO_APPLIED:
        return

    in_notebook = "ipykernel" in sys.modules
    in_colab = "google.colab" in sys.modules

    try:
        loop = asyncio.get_event_loop()
        loop_running = loop.is_running()
    except RuntimeError:
        loop_running = False

    if in_notebook or in_colab or loop_running:
        import nest_asyncio
        nest_asyncio.apply()
        _NEST_ASYNCIO_APPLIED = True
        logger.debug("nest_asyncio applied for nested event loop support")


def run_in_event_loop(coroutine):
    """Run an async coroutine from sync context.

    Handles Jupyter notebooks, Google Colab, and standard Python.
    """
    _ensure_nest_asyncio()
    return asyncio.run(coroutine)
