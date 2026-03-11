import asyncio
from abc import ABC, abstractmethod
from typing import Dict

from starfish.common.logger import get_logger
from starfish.data_factory_v2.constants import DEFAULT_PROGRESS_INTERVAL

logger = get_logger(__name__)


class ProgressReporter(ABC):
    """Interface for reporting job progress."""

    @abstractmethod
    def report(self, stats: Dict[str, int], target: int, max_concurrency: int, running: int) -> None:
        """Report current progress.

        Args:
            stats: Dict with keys: completed, failed, filtered, duplicate, dead_queue, total
            target: Target record count
            max_concurrency: Max concurrent tasks
            running: Currently running task count
        """

    @abstractmethod
    def report_final(self, stats: Dict[str, int], target: int) -> None:
        """Report final job statistics."""

    @abstractmethod
    def report_dead_queue(self, count: int, threshold: int) -> None:
        """Report dead queue information."""


class LogProgressReporter(ProgressReporter):
    """Reports progress via logger."""

    def report(self, stats: Dict[str, int], target: int, max_concurrency: int, running: int) -> None:
        logger.info(
            f"[JOB PROGRESS] "
            f"Completed: {stats['completed']}/{target} | "
            f"Running: {running} | "
            f"Attempted: {stats['total']}"
            f"    (Completed: {stats['completed']}, "
            f"Failed: {stats['failed']}, "
            f"Filtered: {stats['filtered']}, "
            f"Duplicate: {stats['duplicate']}, "
            f"InDeadQueue: {stats['dead_queue']})"
        )

    def report_final(self, stats: Dict[str, int], target: int) -> None:
        logger.info(
            f"[JOB FINISHED] "
            f"Final Status: "
            f"Completed: {stats['completed']}/{target} | "
            f"Attempted: {stats['total']} "
            f"(Failed: {stats['failed']}, "
            f"Filtered: {stats['filtered']}, "
            f"Duplicate: {stats['duplicate']}, "
            f"InDeadQueue: {stats['dead_queue']})"
        )

    def report_dead_queue(self, count: int, threshold: int) -> None:
        logger.warning(
            f"[DLQ] {count} items failed after {threshold} retries. "
            f"Retrieve with: function_name.get_index_dead_queue()"
        )


class NullProgressReporter(ProgressReporter):
    """No-op reporter for when progress display is disabled."""

    def report(self, stats: Dict[str, int], target: int, max_concurrency: int, running: int) -> None:
        pass

    def report_final(self, stats: Dict[str, int], target: int) -> None:
        pass

    def report_dead_queue(self, count: int, threshold: int) -> None:
        pass


class ProgressTicker:
    """Manages periodic progress reporting as an async task."""

    def __init__(self, reporter: ProgressReporter, interval: float = DEFAULT_PROGRESS_INTERVAL):
        self._reporter = reporter
        self._interval = interval
        self._task = None

    def start(self, get_stats, get_target, get_max_concurrency, get_running, is_stopped):
        """Start the ticker as an async task.

        All arguments are callables that return current values.
        """
        async def _tick():
            while not is_stopped():
                self._reporter.report(
                    get_stats(), get_target(), get_max_concurrency(), get_running()
                )
                await asyncio.sleep(self._interval)

        self._task = asyncio.create_task(_tick())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
