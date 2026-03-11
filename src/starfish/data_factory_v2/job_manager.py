"""Core job orchestration — manages concurrent task execution.

Fixes from v1:
- Only requeue STATUS_FAILED (not filtered/duplicate)
- Uses OutputCollector instead of direct queue._queue access
- Uses storage capabilities instead of class name checks
- Rate limiting support
- Clean concurrency controls (no delete-then-recreate)
"""
import asyncio
import copy
import datetime
import hashlib
import json
import traceback
import uuid
from asyncio import Queue
from typing import Any, Callable, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory_v2.config import FactoryConfig, RetryPolicy
from starfish.data_factory_v2.constants import (
    IDX,
    RECORD_STATUS,
    RUN_MODE_DRY_RUN,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
)
from starfish.data_factory_v2.errors import TaskTimeoutError
from starfish.data_factory_v2.output_collector import OutputCollector
from starfish.data_factory_v2.progress import (
    LogProgressReporter,
    NullProgressReporter,
    ProgressReporter,
    ProgressTicker,
)
from starfish.data_factory_v2.rate_limiter import TokenBucketRateLimiter
from starfish.data_factory_v2.state import MutableSharedState
from starfish.data_factory_v2.task_runner import TaskRunner
from starfish.data_factory.storage.base import Storage
from starfish.data_factory.storage.models import GenerationJob, Record

logger = get_logger(__name__)


class JobManager:
    """Orchestrates concurrent task execution with progress tracking."""

    def __init__(
        self,
        config: FactoryConfig,
        state: MutableSharedState,
        storage: Storage,
        user_func: Callable,
        input_queue: Queue,
        output_collector: OutputCollector,
        progress_reporter: ProgressReporter = None,
    ):
        self.config = config
        self.storage = storage
        self.state = state
        self.user_func = user_func
        self.input_queue = input_queue
        self.output = output_collector

        # Progress
        if progress_reporter is None:
            self._reporter = LogProgressReporter() if config.show_progress else NullProgressReporter()
        else:
            self._reporter = progress_reporter

        # Task runner
        self.rate_limiter = TokenBucketRateLimiter(config.rate_limit)
        self.task_runner = TaskRunner(
            retry_policy=config.retry_policy,
            timeout=config.task_timeout,
            rate_limiter=self.rate_limiter,
        )

        # Counters
        self.completed_count = 0
        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.dead_queue_count = 0

        # Dead queue
        self.dead_queue = Queue()
        self._task_failure_count: Dict[str, int] = {}

        # Execution state
        self._running_tasks = set()
        self._active_ops = set()
        self._ticker = None
        self.execution_time = 0
        self.err_type_counter: Dict[str, int] = {}

    def get_stats(self) -> Dict[str, int]:
        return {
            "completed": self.completed_count,
            "failed": self.failed_count,
            "filtered": self.filtered_count,
            "duplicate": self.duplicate_count,
            "dead_queue": self.dead_queue_count,
            "total": self.total_count,
        }

    async def setup_input_output_queue(self):
        """Override point for DryRun/Rerun to modify queues before execution."""
        pass

    # ==================
    # Main Orchestration
    # ==================

    def run_orchestration(self):
        """Entry point — runs the async orchestration in an event loop."""
        from starfish.data_factory_v2.event_loop import run_in_event_loop
        start = datetime.datetime.now(datetime.timezone.utc)
        run_in_event_loop(self._orchestrate())
        self.execution_time = int(
            (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds()
        )

    async def _orchestrate(self):
        """Main async orchestration loop."""
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        lock = asyncio.Lock()

        # Start progress ticker
        if self.config.show_progress:
            self._ticker = ProgressTicker(self._reporter)
            self._ticker.start(
                get_stats=self.get_stats,
                get_target=lambda: self.config.target_count,
                get_max_concurrency=lambda: self.config.max_concurrency,
                get_running=lambda: self.config.max_concurrency - semaphore._value,
                is_stopped=self._is_stop_condition,
            )

        try:
            if not self.input_queue.empty():
                await self._process_tasks(semaphore, lock)
        finally:
            await self._cleanup()

    async def _process_tasks(self, semaphore: asyncio.Semaphore, lock: asyncio.Lock):
        """Process tasks from input queue until stop condition."""
        while not self._is_stop_condition():
            if not self.input_queue.empty():
                await semaphore.acquire()
                input_data = await self.input_queue.get()
                task = asyncio.create_task(
                    self._run_and_handle(input_data, semaphore, lock)
                )
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)
            else:
                await asyncio.sleep(0.5)

    # ==================
    # Task Execution
    # ==================

    async def _run_and_handle(
        self,
        input_data: Dict,
        semaphore: asyncio.Semaphore,
        lock: asyncio.Lock,
    ):
        """Run a single task and handle its result."""
        output = []
        output_ref = []
        task_status = STATUS_COMPLETED
        err_output = {}
        input_data_idx = input_data.get(IDX)

        if input_data_idx is None:
            logger.warning("Found input_data without index")

        try:
            output = await self.task_runner.run_task(
                self.user_func, input_data, input_data_idx
            )
            task_status = self._evaluate_hooks(output)
            output_ref = await self._save_record_data(
                copy.deepcopy(output), task_status, input_data
            )
        except (Exception, TaskTimeoutError) as e:
            task_status, err_output = self._handle_error(e)

        # FIX: Only requeue on FAILED status, not filtered/duplicate
        if task_status == STATUS_FAILED:
            await self._requeue_task(input_data, input_data_idx, lock)

        # Build result and update counters
        result = {
            IDX: input_data_idx,
            RECORD_STATUS: task_status,
            "output_ref": output_ref,
            "output": output,
            "err": [err_output],
        }

        async with lock:
            self.output.add(result)
            self.total_count += 1
            self._update_counter(task_status, result)
            semaphore.release()

    def _evaluate_hooks(self, output) -> str:
        """Run on_record_complete hooks and determine status."""
        hooks_output = [
            hook(output, self.state) for hook in self.config.on_record_complete
        ]
        if STATUS_DUPLICATE in hooks_output:
            return STATUS_DUPLICATE
        if STATUS_FILTERED in hooks_output:
            return STATUS_FILTERED
        return STATUS_COMPLETED

    def _handle_error(self, error: Exception):
        """Handle task error, call error hooks."""
        err_str = str(error)
        err_trace = traceback.format_exc().splitlines()
        logger.error(f"Error running task: {err_str}")

        for hook in self.config.on_record_error:
            hook(err_str, self.state)

        return STATUS_FAILED, {"err_str": err_str, "err_trace": err_trace}

    def _update_counter(self, status: str, result: Dict):
        """Update status counters."""
        if status == STATUS_COMPLETED:
            self.completed_count += 1
        elif status == STATUS_DUPLICATE:
            self.duplicate_count += 1
        elif status == STATUS_FILTERED:
            self.filtered_count += 1
        elif status == STATUS_FAILED:
            self.failed_count += 1
            err_output = result.get("err", [{}])[0]
            err_str = err_output.get("err_str", "Unknown error").strip().lower()
            self.err_type_counter[err_str] = self.err_type_counter.get(err_str, 0) + 1

    # ==================
    # Retry / Dead Queue
    # ==================

    async def _requeue_task(self, input_data: Dict, idx: Any, lock: asyncio.Lock):
        """Requeue failed task or move to dead queue after threshold."""
        task_key = str(idx)
        async with lock:
            self._task_failure_count[task_key] = self._task_failure_count.get(task_key, 0) + 1
            count = self._task_failure_count[task_key]

            if count >= self.config.retry_policy.dead_queue_threshold:
                await self.dead_queue.put(input_data)
                self.dead_queue_count += 1
                logger.warning(
                    f"Task {task_key} failed {count} times, moved to dead queue"
                )
            else:
                await self.input_queue.put(input_data)
                logger.debug(f"Requeued task {task_key} (failure {count})")

    # ==================
    # Stop Condition
    # ==================

    def _is_stop_condition(self) -> bool:
        """Check if the job should stop.

        A record is "done" if it completed, was filtered, or was duplicated.
        Only failed records (that aren't in dead queue) are still in-flight.
        """
        if self.total_count == 0:
            return False

        # Count all "done" records (completed + filtered + duplicate)
        done_count = self.completed_count + self.filtered_count + self.duplicate_count

        # Target reached (all inputs processed to a terminal state)
        remaining = self.config.target_count - done_count
        if remaining <= 0:
            return True

        # All remaining are in dead queue (permanently failed)
        if remaining > 0 and remaining <= self.dead_queue_count:
            logger.warning(f"{remaining} items stuck in dead queue, stopping")
            return True

        # Consecutive failures — check last N results for only FAILED status
        results = self.output.results
        n = self.config.stop_threshold
        if len(results) >= n:
            last_n = results[-n:]
            if all(r[RECORD_STATUS] == STATUS_FAILED for r in last_n):
                logger.error(
                    f"Last {n} records all failed, stopping. "
                    f"Adjust config and resume."
                )
                return True

        return False

    # ==================
    # Storage Persistence
    # ==================

    async def _save_record_data(
        self, records, task_status: str, input_data: Dict
    ) -> List[str]:
        """Save record data to storage if it supports it."""
        output_refs = []

        if self.config.run_mode == RUN_MODE_DRY_RUN:
            return output_refs

        # Use capabilities instead of class name check
        if not (hasattr(self.storage, 'capabilities') and "QUERY_METADATA" in self.storage.capabilities):
            return output_refs

        job_uuid = str(uuid.uuid4())
        await self._create_execution_job(job_uuid, input_data)

        for record_data in records:
            record_uid = str(uuid.uuid4())
            output_ref = await self.storage.save_record_data(
                record_uid, self.config.master_job_id, job_uuid, record_data
            )
            record_model = Record(
                record_uid=record_uid,
                job_id=job_uuid,
                master_job_id=self.config.master_job_id,
                status=task_status,
                output_ref=output_ref,
                end_time=datetime.datetime.now(datetime.timezone.utc),
            )
            await self.storage.log_record_metadata(record_model)
            output_refs.append(output_ref)

        await self._complete_execution_job(job_uuid, task_status, len(records))
        return output_refs

    async def _create_execution_job(self, job_uuid: str, input_data: Dict):
        input_str = json.dumps(input_data, sort_keys=True) if isinstance(input_data, dict) else str(input_data)
        job = GenerationJob(
            job_id=job_uuid,
            master_job_id=self.config.master_job_id,
            status="pending",
            worker_id="data-factory-v2",
            run_config=input_str,
            run_config_hash=hashlib.sha256(input_str.encode()).hexdigest(),
        )
        await self.storage.log_execution_job_start(job)

    async def _complete_execution_job(self, job_uuid: str, status: str, count: int):
        now = datetime.datetime.now(datetime.timezone.utc)
        counts = {
            STATUS_COMPLETED: count if status == STATUS_COMPLETED else 0,
            STATUS_FILTERED: count if status == STATUS_FILTERED else 0,
            STATUS_DUPLICATE: count if status == STATUS_DUPLICATE else 0,
        }
        await self.storage.log_execution_job_end(job_uuid, status, counts, now, now)

    # ==================
    # Cleanup
    # ==================

    async def _cleanup(self):
        """Cancel running tasks and stop ticker."""
        if self._ticker:
            await self._ticker.stop()

        for task in self._running_tasks:
            task.cancel()
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)

        for task in self._active_ops:
            task.cancel()
        if self._active_ops:
            await asyncio.gather(*self._active_ops, return_exceptions=True)

    def get_dead_queue_data(self) -> List[Dict]:
        """Get all items in the dead queue without removing them."""
        items = []
        # Safe iteration: dead_queue is only read after job completion
        while not self.dead_queue.empty():
            try:
                items.append(self.dead_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        # Put them back
        for item in items:
            self.dead_queue.put_nowait(item)
        return items
