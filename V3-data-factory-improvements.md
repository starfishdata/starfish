# Data Factory V3 — Improvement Specification

## Table of Contents

1. [Current State Summary](#1-current-state-summary)
2. [V3 Improvements Overview](#2-v3-improvements-overview)
3. [P0: Critical Bug Fixes](#3-p0-critical-bug-fixes)
4. [P1: Early Job ID Assignment & Accessibility](#4-p1-early-job-id-assignment--accessibility)
5. [P2: Sync/Async Auto-Detection](#5-p2-syncasync-auto-detection)
6. [P3: Unified Retry Policy & Rate Limiting](#6-p3-unified-retry-policy--rate-limiting)
7. [P4: Progress Visibility & Reporting](#7-p4-progress-visibility--reporting)
8. [P5: Graceful Shutdown & Checkpoint on Interrupt](#8-p5-graceful-shutdown--checkpoint-on-interrupt)
9. [P6: Architecture Cleanup](#9-p6-architecture-cleanup)
10. [P7: Storage & Metadata Fixes](#10-p7-storage--metadata-fixes)
11. [Deferred / Not in V3](#11-deferred--not-in-v3)
12. [Use Cases Enabled by V3](#12-use-cases-enabled-by-v3)
13. [Performance & Reliability Gains](#13-performance--reliability-gains)
14. [Migration & Backwards Compatibility](#14-migration--backwards-compatibility)
15. [Implementation Sequence](#15-implementation-sequence)

---

## 1. Current State Summary

### What We Have (V2)

The Data Factory is a decorator-based system that transforms async Python functions into parallelized, durable, resumable data generation pipelines.

**Architecture:**
```
User Code
  │
  @data_factory()              ← decorator (factory.py)
  │
  FactoryWrapper               ← public API: .run(), .dry_run(), .resume()
  │
  FactoryExecutorManager       ← event-loop bridge + routing (unnecessary layer)
  │
  Factory                      ← orchestration lifecycle (God Object, ~577 lines)
  │
  ┌────────┼────────┐
JobManager  DryRun   Rerun     ← execution strategies
  │
TaskRunner                     ← single-task execution with timeout
  │
  ┌─────────┴──────────┐
Storage(ABC)      MutableSharedState
  │
LocalStorage / InMemoryStorage
  │
┌─┴──────────────┐
MetadataHandler   DataHandler  ← SQLite + filesystem
```

**What Works Well:**
- Clean decorator API — users write one function, get `.run()`, `.dry_run()`, `.resume()` for free
- Input conversion — broadcast vs parallel kwargs handles common patterns elegantly
- Storage abstraction — SQLite for metadata, filesystem for data, WAL mode, write locking
- Resume from checkpoint — cloudpickle serialization, hash-based deduplication
- Dead-letter queue — retry N times, then permanently fail with inspection
- Hook system — `on_record_complete` / `on_record_error` with mutable shared state

**What's Broken or Missing:**
- Filtered/duplicate records requeued as failures (correctness bug)
- Exponential backoff broken: `1**retries` = always 1 second
- No rate limiting (only concurrency cap) — LLM APIs get hammered
- No progress callbacks — hardcoded logger.info only
- Hardcoded test values in production metadata
- No sync function support — users must write `async def`
- Job ID not accessible until after execution completes
- No graceful shutdown — interrupt loses all in-flight work
- Factory class is a God Object (15+ responsibilities)
- FactoryExecutorManager is an unnecessary indirection layer
- Direct access to `asyncio.Queue._queue` private internals

---

## 2. V3 Improvements Overview

| Priority | Improvement | Impact | Effort |
|----------|------------|--------|--------|
| **P0** | Fix requeue bug, backoff bug, telemetry tuples | Correctness | Small |
| **P1** | Early job ID assignment & accessibility | UX | Small |
| **P2** | Sync/async auto-detection | UX, Adoption | Medium |
| **P3** | Unified retry policy & rate limiting | Reliability | Medium |
| **P4** | Progress visibility & reporting | UX, Observability | Medium |
| **P5** | Graceful shutdown & checkpoint on interrupt | Reliability | Medium |
| **P6** | Architecture cleanup (eliminate indirection, decompose God Object) | Maintainability | Large |
| **P7** | Storage & metadata fixes | Correctness | Small |

---

## 3. P0: Critical Bug Fixes

### 3.1 Fix Requeue Logic — Only Retry Failures

**Bug:** `job_manager.py:200-201` requeues ALL non-completed records, including `STATUS_DUPLICATE` and `STATUS_FILTERED`.

```python
# CURRENT (broken)
if task_status != STATUS_COMPLETED:
    await self._requeue_task(input_data, input_data_idx)

# FIXED
if task_status == STATUS_FAILED:
    await self._requeue_task(input_data, input_data_idx)
```

**Impact:** Filtered and duplicate records are retried up to `dead_queue_threshold` times, then moved to the dead queue. Users see filtered records in the dead queue, corrupting their understanding of what actually failed.

### 3.2 Fix Exponential Backoff

**Bug:** `task_runner.py:60` — `1**retries` is always `1`.

```python
# CURRENT (broken)
await asyncio.sleep(1**retries)

# FIXED
await asyncio.sleep(2 ** retries)  # 2s, 4s, 8s, 16s...
```

**Impact:** Currently all retries happen after exactly 1 second, which doesn't help with transient rate limit errors.

### 3.3 Fix Telemetry Tuple Bug

**Bug:** `factory_.py:252-253` — trailing commas create tuples instead of scalars.

```python
# CURRENT (broken)
telemetry_data.num_inputs = (len(self.original_input_data),)      # tuple
telemetry_data.target_reached = ((self.job_manager.completed_count >= ...,))  # nested tuple

# FIXED
telemetry_data.num_inputs = len(self.original_input_data)
telemetry_data.target_reached = (self.job_manager.completed_count >= ...)
```

### 3.4 Fix Identity Comparison

**Bug:** `job_manager.py:190` — `== None` should be `is None`.

### 3.5 Fix Typo

**Bug:** `job_manager.py:359` — `fitered_num_records` → `filtered_num_records`.

### 3.6 Fix Docstring Placement

**Bug:** `factory_.py:199-200` — docstring appears after first statement.

### 3.7 Fix Duplicate Import

**Bug:** `factory_.py:2, 36` — `from copy import deepcopy` imported twice.

---

## 4. P1: Early Job ID Assignment & Accessibility

### Problem

Currently, the `master_job_id` is generated inside `Factory.__call__()` during `_initialize_job()`. It's not exposed to the user until after the run completes. Users need the job ID to:
- Log it alongside their own records
- Track the job in monitoring systems
- Save it for later resume
- Correlate across multiple runs

### Solution

Assign the `master_job_id` at **decoration time** or **at the start of `.run()`**, and expose it as a property on the `FactoryWrapper`.

```python
# User code — BEFORE
result = my_func.run(data=records)
# Can't get job_id until after this returns

# User code — AFTER (V3)
result = my_func.run(data=records)
job_id = my_func.job_id  # Available immediately after .run() starts
# Or even better, returned from run:
job_id = my_func.job_id  # Set as soon as .run() is called
```

### Implementation

1. Generate `master_job_id` in `FactoryWrapper.run()` before calling into `Factory`
2. Store it as `self._job_id` on the wrapper
3. Pass it down to `Factory.__call__()` as a parameter
4. Expose `FactoryWrapper.job_id` property

```python
class FactoryWrapper:
    @property
    def job_id(self) -> str:
        """The master job ID for the most recent run. Available immediately after .run() is called."""
        return self._job_id

    def run(self, *args, **kwargs):
        self._job_id = str(uuid.uuid4())
        # Pass job_id to Factory
        return self._execute(run_mode=RUN_MODE_NORMAL, job_id=self._job_id, *args, **kwargs)
```

**Use case enabled:**
```python
result = my_func.run(data=records)
db.save({"job_id": my_func.job_id, "result_count": len(result)})
# Later:
resumed = my_func.resume(master_job_id=my_func.job_id)
```

---

## 5. P2: Sync/Async Auto-Detection

### Problem

Currently, `@data_factory()` requires users to write `async def`. Many users, especially data scientists and ML engineers, work with synchronous code. Requiring them to learn asyncio just to use the decorator is a friction point.

### Solution

Auto-detect whether the decorated function is sync or async. If sync, wrap it transparently in an async executor.

```python
# Sync function — V3 accepts this
@data_factory(max_concurrency=10)
def generate_data(prompt, model="gpt-4"):
    response = openai.chat.completions.create(prompt=prompt, model=model)
    return [{"text": response.choices[0].message.content}]

# Async function — still works exactly as before
@data_factory(max_concurrency=10)
async def generate_data(prompt, model="gpt-4"):
    response = await openai_async.chat.completions.create(prompt=prompt, model=model)
    return [{"text": response.choices[0].message.content}]
```

### Implementation

In `factory.py` (the decorator), detect the function type and wrap if needed:

```python
import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor

def data_factory(**config):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            # Already async — use directly
            wrapped_func = func
        else:
            # Sync function — wrap in thread executor for true parallelism
            _executor = ThreadPoolExecutor(max_workers=config.get("max_concurrency", 10))

            async def wrapped_func(*args, **kwargs):
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(_executor, lambda: func(*args, **kwargs))

            # Preserve original function metadata
            wrapped_func.__name__ = func.__name__
            wrapped_func.__qualname__ = func.__qualname__
            wrapped_func.__module__ = func.__module__
            wrapped_func.__doc__ = func.__doc__
            # Preserve the original signature for parameter validation
            wrapped_func.__wrapped__ = func

        return FactoryWrapper(wrapped_func, config)
    return decorator
```

### Key Design Decisions

1. **ThreadPoolExecutor, not `asyncio.to_thread`** — We need a bounded pool. `to_thread` uses the default executor which has no concurrency control. The pool size should match `max_concurrency`.

2. **Signature preservation** — `_check_parameter_match()` inspects the function signature. We need `__wrapped__` so it inspects the original sync function's parameters, not the wrapper's `*args, **kwargs`.

3. **True parallelism for sync functions** — Sync I/O-bound functions (HTTP calls, database queries) genuinely benefit from threads. The GIL is released during I/O, so this gives real concurrency.

### Performance Characteristics

| Scenario | Sync (V3) | Async (V2/V3) |
|----------|-----------|---------------|
| I/O-bound (API calls) | Full concurrency via threads | Full concurrency via event loop |
| CPU-bound (data processing) | Limited by GIL | Limited by GIL |
| Memory overhead | Thread stack per worker (~8MB × max_concurrency) | Minimal coroutine overhead |
| Context switching | OS-level thread switching | Cooperative event-loop switching |

**Recommendation for users:** If your function is already async (uses `await`), keep it async. If it's sync I/O (HTTP libraries, database drivers), the decorator handles it. For CPU-bound work, neither approach parallelizes well — users should use `multiprocessing` outside the factory.

---

## 6. P3: Unified Retry Policy & Rate Limiting

### 6.1 Unified Retry Policy

### Problem

Retry logic is split across two layers with no unified configuration:

1. **TaskRunner** (`task_runner.py`) — within-task retries with broken backoff
2. **JobManager** (`job_manager.py`) — cross-task requeue with dead_queue_threshold

Users configure `dead_queue_threshold` (the requeue limit) but have no control over:
- Backoff strategy (fixed, exponential, jitter)
- Which exceptions should trigger retry vs immediate failure
- Per-exception retry limits
- Delay between retries

### Solution

Create a `RetryPolicy` as a first-class configuration object.

```python
@data_factory(
    retry=RetryPolicy(
        max_retries=3,                    # total attempts before dead queue
        backoff="exponential",            # "fixed", "exponential", "exponential_jitter"
        base_delay=2.0,                   # seconds
        max_delay=60.0,                   # cap for exponential backoff
        retryable_exceptions=[            # only retry these (default: all)
            ConnectionError,
            TimeoutError,
            RateLimitError,
        ],
        non_retryable_exceptions=[        # never retry these
            ValueError,
            AuthenticationError,
        ],
    ),
    max_concurrency=10,
)
async def my_func(prompt):
    ...
```

### Implementation

```python
from dataclasses import dataclass, field
from typing import List, Type, Optional
import random

@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff: str = "exponential"            # "fixed" | "exponential" | "exponential_jitter"
    base_delay: float = 2.0
    max_delay: float = 60.0
    retryable_exceptions: Optional[List[Type[Exception]]] = None     # None = retry all
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=list)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if this exception should be retried at this attempt count."""
        if attempt >= self.max_retries:
            return False
        if self.non_retryable_exceptions:
            if isinstance(exception, tuple(self.non_retryable_exceptions)):
                return False
        if self.retryable_exceptions is not None:
            return isinstance(exception, tuple(self.retryable_exceptions))
        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for this attempt number."""
        if self.backoff == "fixed":
            delay = self.base_delay
        elif self.backoff == "exponential":
            delay = self.base_delay * (2 ** attempt)
        elif self.backoff == "exponential_jitter":
            delay = self.base_delay * (2 ** attempt)
            delay = delay * (0.5 + random.random())  # jitter: 50%-150% of base
        else:
            delay = self.base_delay
        return min(delay, self.max_delay)
```

**Backwards compatibility:** If user doesn't pass `retry=`, construct a default `RetryPolicy(max_retries=dead_queue_threshold)` from the existing `dead_queue_threshold` parameter. This means existing code works unchanged.

### 6.2 Rate Limiting

### Problem

`max_concurrency` limits how many tasks run at once, but doesn't limit the **rate** at which new tasks start. If tasks complete quickly, you can start 100 tasks/second with `max_concurrency=100`. LLM APIs have rate limits (e.g., 60 requests/minute) that concurrency alone doesn't respect.

### Solution

Add a token-bucket rate limiter, configurable per-factory.

```python
@data_factory(
    max_concurrency=10,
    rate_limit=RateLimit(
        max_requests=60,       # requests per window
        window_seconds=60,     # sliding window
    ),
)
async def my_func(prompt):
    ...
```

### Implementation

```python
import asyncio
import time

class TokenBucketRateLimiter:
    def __init__(self, max_tokens: int, refill_seconds: float):
        self.max_tokens = max_tokens
        self.refill_rate = max_tokens / refill_seconds  # tokens per second
        self.tokens = max_tokens
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a token is available, then consume it."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
                self.last_refill = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

            # No token available — wait a bit
            await asyncio.sleep(1.0 / self.refill_rate)
```

**Integration point:** In `JobManager._process_tasks()`, acquire rate limiter before acquiring semaphore:

```python
async def _process_tasks(self):
    while not self._should_stop():
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        await self.semaphore.acquire()
        input_data = await self.job_input_queue.get()
        asyncio.create_task(self._run_single_task(input_data))
```

### Performance Impact

| Config | Without Rate Limit | With Rate Limit (60/min) |
|--------|-------------------|--------------------------|
| 100 fast tasks, concurrency=10 | ~10s (10 concurrent, fast completion) | ~100s (1/sec effective rate) |
| 1000 API calls, concurrency=50 | All 1000 fire ASAP → rate limit errors | Smooth 1/sec → no errors |
| Mixed fast/slow tasks | Unpredictable burst pattern | Steady throughput |

---

## 7. P4: Progress Visibility & Reporting

### Problem

Progress is reported via `logger.info` every 3 seconds with ANSI escape codes. This is:
- Not capturable by user code
- Not suitable for notebooks (Jupyter shows raw ANSI)
- Not extensible (can't send to Slack, dashboard, etc.)
- No ETA or throughput metrics

### Solution

Create a `ProgressReporter` interface with pluggable implementations.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ProgressSnapshot:
    """Immutable snapshot of job progress at a point in time."""
    total: int
    completed: int
    failed: int
    filtered: int
    duplicate: int
    in_dead_queue: int
    running: int                    # currently executing tasks
    elapsed_seconds: float
    records_per_second: float       # throughput
    estimated_remaining_seconds: float | None

    @property
    def percent_complete(self) -> float:
        return (self.completed / self.total * 100) if self.total > 0 else 0


class ProgressReporter(ABC):
    @abstractmethod
    def on_progress(self, snapshot: ProgressSnapshot) -> None:
        """Called periodically with current progress."""
        ...

    def on_complete(self, snapshot: ProgressSnapshot) -> None:
        """Called once when job finishes."""
        ...


class LogProgressReporter(ProgressReporter):
    """Default — current behavior, logs to logger.info."""
    def on_progress(self, snapshot: ProgressSnapshot):
        logger.info(f"[JOB PROGRESS] {snapshot.completed}/{snapshot.total} "
                     f"({snapshot.percent_complete:.1f}%) | "
                     f"ETA: {snapshot.estimated_remaining_seconds:.0f}s | "
                     f"{snapshot.records_per_second:.1f} rec/s")


class CallbackProgressReporter(ProgressReporter):
    """User-provided callback function."""
    def __init__(self, callback):
        self.callback = callback

    def on_progress(self, snapshot: ProgressSnapshot):
        self.callback(snapshot)


class TqdmProgressReporter(ProgressReporter):
    """tqdm progress bar integration for notebooks."""
    def __init__(self):
        from tqdm.auto import tqdm
        self._pbar = None

    def on_progress(self, snapshot: ProgressSnapshot):
        if self._pbar is None:
            self._pbar = tqdm(total=snapshot.total, desc="Processing")
        self._pbar.n = snapshot.completed
        self._pbar.set_postfix({
            "failed": snapshot.failed,
            "rate": f"{snapshot.records_per_second:.1f}/s"
        })
        self._pbar.refresh()

    def on_complete(self, snapshot: ProgressSnapshot):
        if self._pbar:
            self._pbar.close()
```

### User API

```python
# Default (current behavior — log-based)
@data_factory(show_progress=True)

# Custom callback
@data_factory(
    on_progress=lambda snap: print(f"{snap.percent_complete:.0f}% done")
)

# tqdm bar (auto-detects notebook vs terminal)
@data_factory(progress="tqdm")

# Full control
@data_factory(progress=MyCustomReporter())
```

### New Metrics

V3 progress includes metrics not currently tracked:

| Metric | Description | How Calculated |
|--------|-------------|----------------|
| `records_per_second` | Throughput | `completed / elapsed_seconds` |
| `estimated_remaining_seconds` | ETA | `(total - completed) / records_per_second` |
| `percent_complete` | Percentage | `completed / total * 100` |
| `running` | In-flight count | `max_concurrency - semaphore._value` |
| `elapsed_seconds` | Wall clock time | `time.monotonic() - start_time` |

---

## 8. P5: Graceful Shutdown & Checkpoint on Interrupt

### Problem

Currently, `KeyboardInterrupt` is caught in `Factory.__call__()` and logged, but:
- All in-flight tasks are lost (their results are never saved)
- The master job status is set to `failed`
- Resume requires re-executing all in-flight tasks from scratch
- No distinction between "user chose to stop" and "something crashed"

### Solution

On interrupt: let in-flight tasks complete (with a timeout), save their results, mark the job as `interrupted` (not `failed`), and exit cleanly.

```python
async def _handle_interrupt(self):
    """Graceful shutdown: wait for in-flight, save results, mark interrupted."""
    logger.info("[SHUTDOWN] Interrupt received. Waiting for in-flight tasks to complete...")

    # 1. Stop accepting new tasks
    self.job_manager.stop_accepting_new_tasks()

    # 2. Wait for in-flight tasks (with timeout)
    try:
        await asyncio.wait_for(
            self.job_manager.wait_for_in_flight(),
            timeout=30  # configurable
        )
        logger.info("[SHUTDOWN] All in-flight tasks completed.")
    except asyncio.TimeoutError:
        logger.warning("[SHUTDOWN] Timeout waiting for in-flight tasks. Some results may be lost.")

    # 3. Save all completed results to storage
    await self.job_manager.flush_results_to_storage()

    # 4. Mark job as interrupted (not failed) — resume can pick up from here
    await self._complete_master_job(status="interrupted")

    # 5. Save request config for resume
    await self._save_request_config()

    logger.info(f"[SHUTDOWN] Job {self.master_job_id} saved. "
                f"Completed {self.job_manager.completed_count}/{self.target_count}. "
                f"Resume with: my_func.resume(master_job_id='{self.master_job_id}')")
```

### User Experience

```
$ python my_pipeline.py
[JOB PROGRESS] Completed: 4523/10000 | Running: 10 | 45.2%
^C
[SHUTDOWN] Interrupt received. Waiting for in-flight tasks to complete...
[SHUTDOWN] All in-flight tasks completed. 4533 saved.
[SHUTDOWN] Job abc-123 saved. Resume with: my_func.resume(master_job_id='abc-123')

# Later:
result = my_func.resume(master_job_id="abc-123")
# Picks up from record 4534, not from scratch
```

### Job Status Model (Updated)

```
V2: completed | failed
V3: completed | failed | interrupted
```

`interrupted` means: user chose to stop, all saved results are valid, safe to resume. `failed` means: something broke unexpectedly. This distinction helps in monitoring and dashboards.

---

## 9. P6: Architecture Cleanup

### 9.1 Eliminate FactoryExecutorManager

**Current:** `FactoryWrapper → FactoryExecutorManager → Factory` (three-hop chain)

**V3:** `FactoryWrapper → Factory` (direct)

Move the useful parts:
- **Event loop management** → standalone utility (already partially exists in `event_loop.py`)
- **Filter conversion** → simple dict or method on `FactoryWrapper`
- **Resume orchestration** → method on `Factory`
- **Dead queue access** → proper drain method on `JobManager`

### 9.2 Decompose Factory God Object

Extract focused classes from the current `Factory` monolith:

```
Factory (current: ~577 lines, 15+ methods, 5+ responsibilities)
  │
  ├─→ InputConverter (new)
  │   - Parse args/kwargs into input records
  │   - Validate parameters match function signature
  │   - Build input queue
  │   - Store original input data
  │
  ├─→ OutputCollector (new)
  │   - Drain job_output queue (no more _queue access)
  │   - Filter by status
  │   - Cache results
  │   - Index extraction
  │
  ├─→ JobLifecycleManager (new)
  │   - Create project and master job records
  │   - Log job start/end
  │   - Handle status transitions
  │   - Save request config
  │
  └─→ Factory (simplified)
      - Wire components together
      - Single __call__ method that delegates
      - ~100 lines
```

### 9.3 Fix Queue Access

Replace all `queue._queue` access with proper patterns:

```python
# CURRENT (fragile)
results = list(self.job_manager.job_output._queue)

# V3 — OutputCollector maintains a parallel list
class OutputCollector:
    def __init__(self):
        self._results: list[tuple[dict, str]] = []  # (data, status)

    def add(self, data: dict, status: str):
        self._results.append((data, status))

    def get_by_status(self, status: str) -> list[dict]:
        return [d for d, s in self._results if s == status]
```

### 9.4 Use Storage Capabilities

Replace class name checks with capability queries:

```python
# CURRENT (fragile)
if self.storage.__class__.__name__ == "LocalStorage":
    await self.storage.save_record_data(...)

# V3
if self.storage.supports_persistence:
    await self.storage.save_record_data(...)
```

---

## 10. P7: Storage & Metadata Fixes

### 10.1 Fix Hardcoded Test Values

```python
# CURRENT
project = Project(name="Test Project", description="A test project for storage layer testing")
master_job = GenerationMasterJob(name="Test Master Job", target_record_count=10)

# V3 — derive from actual function and config
project = Project(
    name=self.user_func.__name__,           # e.g., "generate_reviews"
    description=f"Data factory project: {self.user_func.__module__}.{self.user_func.__name__}"
)
master_job = GenerationMasterJob(
    name=f"{self.user_func.__name__}_{self.master_job_id[:8]}",
    target_record_count=self.target_count,  # actual count from config
)
```

### 10.2 Fix Exception Handling

```python
# CURRENT (redundant)
except (InputError, OutputError, KeyboardInterrupt, Exception) as e:

# V3 — handle separately
except KeyboardInterrupt:
    await self._handle_interrupt()
except (InputError, OutputError) as e:
    # Known errors — report clearly
    raise
except Exception as e:
    # Unexpected errors — log and raise
    logger.error(f"Unexpected error: {e}")
    raise
```

---

## 11. Deferred / Not in V3

These items were discussed but explicitly deferred:

| Feature | Reason for Deferral |
|---------|-------------------|
| **Backpressure (bounded queue)** | Current approach (all inputs in memory) works for typical use cases. The persistence layer conflict (need all inputs in SQLite for resume) makes bounded queues tricky. The memory ceiling (~1-2GB for 1M small dicts) is acceptable for now. Revisit when users report memory issues or when file-based inputs (CSV/Excel) are added. |
| **Pause and Cancel** | Cancel + resume from checkpoint covers the same use case. Adding explicit pause/cancel state management adds complexity with little benefit over "Ctrl+C → resume." |
| **Pipeline Composition** | Chaining factories (output of one → input of next) adds significant complexity to the execution model, error propagation, and resume semantics. Users can compose manually with sequential `.run()` calls. |
| **Pluggable Serialization** | Cloudpickle works for 95% of cases. Alternative serialization strategies (dill, custom) can wait until users report issues with specific function types. |
| **Batch Processing** | Sending multiple inputs to the user function in a single call. Useful for batched API endpoints but changes the execution contract significantly. |

---

## 12. Use Cases Enabled by V3

### 12.1 Data Scientist with Sync Code (P2)

**Before V3:** Must learn asyncio, rewrite existing sync functions.

```python
# V2 — forced async, confusing for data scientists
@data_factory(max_concurrency=5)
async def classify(text):
    # They don't know what "await" means
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: model.predict(text))
    return [{"label": result}]
```

**After V3:** Just decorate their existing function.

```python
# V3 — works with their existing sync code
@data_factory(max_concurrency=5)
def classify(text):
    result = model.predict(text)
    return [{"label": result}]
```

### 12.2 LLM Pipeline with Rate Limits (P3)

**Before V3:** Users manually add `asyncio.sleep()` calls or get rate-limited.

```python
# V2 — user manages rate limiting themselves
@data_factory(max_concurrency=50)
async def generate(prompt):
    await asyncio.sleep(0.5)  # manual throttle, guess-and-check
    return await call_llm(prompt)
```

**After V3:** Declare the rate limit, factory handles it.

```python
# V3 — declarative rate limiting
@data_factory(
    max_concurrency=50,
    rate_limit=RateLimit(max_requests=100, window_seconds=60),
)
async def generate(prompt):
    return await call_llm(prompt)
```

### 12.3 Long-Running Job with Monitoring (P1 + P4)

**Before V3:** No way to track progress programmatically or get job ID for monitoring.

**After V3:**

```python
@data_factory(
    max_concurrency=20,
    on_progress=lambda snap: dashboard.update(
        job_id=snap.job_id,
        completed=snap.completed,
        eta=snap.estimated_remaining_seconds
    ),
)
async def process(record):
    return await transform(record)

result = process.run(data=records)
# job_id available immediately
slack.post(f"Job {process.job_id} started with {len(records)} records")
```

### 12.4 Robust Pipeline with Smart Retries (P3)

**Before V3:** All errors retried the same way. Auth errors waste retries.

**After V3:**

```python
@data_factory(
    retry=RetryPolicy(
        max_retries=5,
        backoff="exponential_jitter",
        base_delay=2.0,
        max_delay=120.0,
        non_retryable_exceptions=[AuthenticationError, ValueError],
    ),
)
async def call_api(params):
    return await api.request(params)
```

### 12.5 Interruptible Production Job (P5)

**Before V3:** Ctrl+C loses in-flight work. Resume re-processes in-flight tasks.

**After V3:**

```python
# Terminal output on Ctrl+C:
# [SHUTDOWN] Interrupt received. Waiting for in-flight tasks...
# [SHUTDOWN] 10 in-flight tasks completed and saved.
# [SHUTDOWN] Job abc-123 saved at 4533/10000.
# Resume: my_func.resume(master_job_id='abc-123')

# Later:
result = my_func.resume(master_job_id="abc-123")
# Starts at record 4534, not 4524
```

---

## 13. Performance & Reliability Gains

### Throughput

| Scenario | V2 | V3 | Improvement |
|----------|----|----|-------------|
| 10K LLM calls, rate-limited API | Frequent 429 errors → retries → cascading failures | Smooth rate-limited flow | 2-3x effective throughput (less wasted retries) |
| Sync function, 50 concurrent | N/A (must be async) | ThreadPoolExecutor with 50 workers | Enables entirely new use case |
| Job interrupted at 50% | Loses 10 in-flight tasks | Saves in-flight, resumes exactly | 0 wasted work on interrupt |

### Reliability

| Scenario | V2 | V3 | Impact |
|----------|----|----|--------|
| Filtered record | Retried 3x → dead queue | Correctly marked filtered | Correct behavior, no phantom failures |
| Transient network error | 1s fixed delay → retry | Exponential backoff with jitter | Better recovery, less API pressure |
| Auth error | Retried until dead queue | Immediately fails (non-retryable) | Fast feedback, no wasted retries |
| Rate limit error | Retried at full speed | Backoff + rate limiter adapts | Avoids compounding rate limit violations |

### Developer Experience

| Dimension | V2 | V3 |
|-----------|----|----|
| Learning curve | Must know asyncio | Sync or async — just works |
| Progress tracking | Parse log output | Callbacks, tqdm, custom reporters |
| Job management | No job ID access | `my_func.job_id` immediately available |
| Interrupt handling | Lose work, unclear state | Clean shutdown, clear resume instructions |
| Retry configuration | Two knobs (retries + threshold) | Full policy: backoff, exceptions, delays |

---

## 14. Migration & Backwards Compatibility

### Fully Backwards Compatible (No User Changes Required)

All V3 changes are additive or fix bugs. Existing code works unchanged:

| V2 API | V3 Behavior |
|--------|-------------|
| `@data_factory(dead_queue_threshold=3)` | Creates `RetryPolicy(max_retries=3)` internally |
| `@data_factory(show_progress=True)` | Uses `LogProgressReporter` (same output) |
| `async def my_func(...)` | Still works, async path unchanged |
| `my_func.resume(master_job_id=...)` | Same API, now handles `interrupted` status too |
| No `rate_limit` parameter | No rate limiting (same as V2) |

### New APIs (Opt-In)

| New API | Default |
|---------|---------|
| `my_func.job_id` | Available after `.run()` is called |
| `retry=RetryPolicy(...)` | Falls back to `dead_queue_threshold` |
| `rate_limit=RateLimit(...)` | No rate limiting |
| `progress="tqdm"` or `on_progress=callback` | `show_progress=True` (log-based) |
| Sync `def` functions | Auto-wrapped in executor |

### Deprecations

| Deprecated | Replacement | Timeline |
|------------|-------------|----------|
| `dead_queue_threshold` parameter | `retry=RetryPolicy(max_retries=N)` | Warn in V3, remove in V4 |
| `show_progress=True/False` | `progress="log"` / `progress=None` | Warn in V3, remove in V4 |

---

## 15. Implementation Sequence

Ordered by dependency and risk. Each phase can be shipped independently.

### Phase 1: Bug Fixes (P0) — Ship First
- Fix requeue logic (1 line)
- Fix exponential backoff (1 line)
- Fix telemetry tuples (2 lines)
- Fix `== None` → `is None`
- Fix typo, docstring, duplicate import

**Risk:** Minimal. These are correctness fixes.
**Test:** Existing tests should still pass. Add targeted tests for requeue behavior.

### Phase 2: Early Job ID (P1) + Storage Fixes (P7)
- Generate job ID in FactoryWrapper
- Expose `.job_id` property
- Fix hardcoded project/job names
- Fix exception handling structure

**Risk:** Low. Additive API, fixes metadata.
**Test:** Add test for `.job_id` availability.

### Phase 3: Sync/Async Auto-Detection (P2)
- Add `inspect.iscoroutinefunction` check in decorator
- ThreadPoolExecutor wrapping for sync functions
- Signature preservation for parameter validation

**Risk:** Medium. Need to verify parameter validation works with wrapped functions.
**Test:** New test suite for sync function support. Test that existing async functions are unaffected.

### Phase 4: Retry Policy & Rate Limiting (P3)
- Implement `RetryPolicy` dataclass
- Implement `TokenBucketRateLimiter`
- Integrate into TaskRunner and JobManager
- Backwards-compat bridge from `dead_queue_threshold`

**Risk:** Medium. Changes retry behavior. Need thorough testing.
**Test:** Test all backoff strategies. Test rate limiter under load. Test exception filtering.

### Phase 5: Progress Reporting (P4)
- Define `ProgressSnapshot` and `ProgressReporter` interface
- Implement `LogProgressReporter`, `CallbackProgressReporter`, `TqdmProgressReporter`
- Add ETA and throughput calculations
- Wire into JobManager progress ticker

**Risk:** Low. Additive, doesn't change execution behavior.
**Test:** Test snapshot calculations. Test callback invocation.

### Phase 6: Graceful Shutdown (P5)
- Implement interrupt handler
- Add `interrupted` job status
- Wait for in-flight tasks
- Flush results to storage
- Update resume to handle `interrupted` status

**Risk:** Medium-High. Signal handling and async shutdown are notoriously tricky.
**Test:** Test interrupt → resume cycle. Test timeout on in-flight wait.

### Phase 7: Architecture Cleanup (P6)
- Eliminate FactoryExecutorManager
- Extract InputConverter, OutputCollector, JobLifecycleManager
- Replace queue._queue access with proper patterns
- Use storage capabilities instead of class name checks

**Risk:** High (refactoring). No behavior change, but touches many files.
**Test:** Full regression suite. All existing tests must pass unchanged.
