# Data Factory Architecture Review

## Executive Summary

The Data Factory is a decorator-based system that transforms async Python functions into parallelized, durable, resumable data generation pipelines. It targets synthetic data workflows (primarily LLM-powered) and provides concurrency control, retry/dead-queue semantics, hook-based extensibility, and SQLite-backed persistence for checkpoint/resume.

This review covers **system design**, **component separation**, **abstraction layering**, **concrete bugs**, and **improvement recommendations**.

---

## 1. Component Map

```
                    User Code
                       │
                @data_factory()          ← decorator entry point (factory.py)
                       │
                 FactoryWrapper          ← public API surface (factory_wrapper.py)
                       │
            FactoryExecutorManager       ← event-loop bridge + routing (factory_executor_manager.py)
                       │
                    Factory              ← orchestration lifecycle (factory_.py)
                       │
              ┌────────┼────────┐
          JobManager  DryRun   Rerun     ← execution strategies (job_manager*.py)
              │
         TaskRunner                      ← single-task execution (task_runner.py)
              │
    ┌─────────┴──────────┐
  Storage(ABC)      MutableSharedState   ← persistence + state
    │
  LocalStorage / InMemoryStorage
    │
  ┌─┴──────────────┐
MetadataHandler   DataHandler            ← SQLite + filesystem
```

---

## 2. What Works Well

### 2.1 Decorator Ergonomics
The `@data_factory(...)` decorator gives users a genuinely clean API. A user writes an async function, decorates it, and gets `.run()`, `.dry_run()`, `.resume()` for free. The input conversion (broadcast vs parallel kwargs) is clever and covers the common use cases well.

### 2.2 Storage Abstraction
The `Storage` ABC is well-defined with a comprehensive contract. The two-tier local storage (SQLite for metadata, filesystem for data artifacts) is a sound architectural choice — it avoids SQLite blob bloat while keeping structured queries fast. The WAL mode, write locking, and retry-with-backoff for `database is locked` errors show thoughtful production hardening.

### 2.3 Resume from Checkpoint
The resume system — serializing function + config via cloudpickle, hashing input data for deduplication, replaying completed records from storage — is the most architecturally ambitious feature and it works. The separation between same-session and cross-session resume is correct.

### 2.4 Dead Queue
The dead-letter queue pattern (retry N times, then permanently fail) is the right pattern for this problem space. Users get `get_input_data_in_dead_queue()` to inspect what failed, which is good observability.

---

## 3. Architectural Concerns

### 3.1 CRITICAL: Filtered/Duplicate Records Get Requeued as Failures

**File:** `job_manager.py:200-201`

```python
if task_status != STATUS_COMPLETED:
    await self._requeue_task(input_data, input_data_idx)
```

This requeues **every non-completed record**, including `STATUS_DUPLICATE` and `STATUS_FILTERED`. These are intentional outcomes from hooks — they should NOT be retried. A record that a hook marks as "filtered" will be retried up to `dead_queue_threshold` times, then moved to the dead queue. This is a correctness bug.

**Fix:** Only requeue on `STATUS_FAILED`:
```python
if task_status == STATUS_FAILED:
    await self._requeue_task(input_data, input_data_idx)
```

### 3.2 CRITICAL: Exponential Backoff Is Broken

**File:** `task_runner.py:60`

```python
await asyncio.sleep(1**retries)  # exponential backoff
```

`1**retries` is always `1` for any value of `retries`. This is constant 1-second delay, not exponential backoff. Should be `2**retries` or similar.

### 3.3 The FactoryExecutorManager Is an Unnecessary Indirection Layer

**File:** `factory_executor_manager.py`

This class is a grab-bag of static methods organized into inner classes (`Filters`, `EventLoop`, `DeadQueue`, `Resume`). It's positioned between `FactoryWrapper` and `Factory` but doesn't add meaningful abstraction. It combines four unrelated concerns:

1. **Event loop management** — should be a standalone utility (it partially is in `event_loop.py` already, creating duplication)
2. **Filter conversion** — trivial mapping that could live on `FactoryWrapper` or as a simple dict lookup
3. **Dead queue access** — directly accesses `factory.job_manager.dead_queue._queue` internals
4. **Resume orchestration** — complex logic that mutates Factory state, creates storage connections, and deserializes cloudpickle — this is domain logic that belongs in `Factory`

The problem: `FactoryWrapper` delegates to `FactoryExecutorManager` which delegates to `Factory`. This three-hop chain makes the code harder to trace and debug. `FactoryWrapper → Factory` would be cleaner.

### 3.4 Factory Class Mixes Orchestration with Data Transformation

**File:** `factory_.py`

The `Factory` class handles:
- Input conversion (`_default_input_converter` — a module-level function, not even a method)
- ID generation
- Storage lifecycle (setup, close)
- Project creation (hardcoded "Test Project" name — `factory_.py:352`)
- Master job lifecycle
- Config serialization with cloudpickle
- Telemetry
- Output processing and caching
- Parameter validation

This is a God Object. The single `__call__` method runs the entire pipeline. The class has ~15 methods across at least 5 distinct responsibilities.

**Suggested decomposition:**
- `InputConverter` — input parsing, validation, queue construction
- `JobLifecycleManager` — project/job creation, status updates, completion
- `OutputCollector` — output caching, filtering, index extraction
- `Factory` — thin orchestrator that wires the above together

### 3.5 Hardcoded Test Values in Production Code

**File:** `factory_.py:352, 398-404`

```python
project = Project(project_id=..., name="Test Project",
                  description="A test project for storage layer testing")
```

```python
master_job = GenerationMasterJob(
    ...
    name="Test Master Job",
    output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
    target_record_count=10,  # hardcoded, ignores actual target_count
    ...
)
```

Production code has hardcoded test names and a fixed `target_record_count=10` regardless of actual config. This means the metadata DB will always show the wrong target count.

### 3.6 Direct Access to Queue Internals

Multiple places access `queue._queue` directly:

- `factory_.py:287` — `self.job_manager.job_output._queue`
- `factory_executor_manager.py:110` — `factory.job_manager.dead_queue._queue`
- `job_manager.py:377` — `self.job_output._queue`

`_queue` is a private implementation detail of `asyncio.Queue`. It works, but it's fragile — any Python version change to Queue internals will break this. The proper pattern would be to drain the queue or maintain a parallel results list.

### 3.7 Storage Type Checked by Class Name String

**File:** `job_manager.py:336`

```python
storage_class_name = self.storage.__class__.__name__
if storage_class_name == "LocalStorage":
```

This defeats the purpose of the `Storage` ABC. The storage backend should have a capability flag or method that the job manager queries, rather than checking class names. The `capabilities` property exists on the ABC but isn't used here.

### 3.8 Concurrency Controls Recreated on Every Run

**File:** `job_manager.py:153-160`

```python
def _initialize_concurrency_controls(self):
    if hasattr(self, "semaphore"):
        del self.semaphore
    if hasattr(self, "lock"):
        del self.lock
    self.semaphore = asyncio.Semaphore(self.job_config.max_concurrency)
    self.lock = asyncio.Lock()
```

The delete-then-recreate pattern suggests the `JobManager` is being reused across runs in ways it wasn't designed for. A cleaner approach: create a fresh `JobManager` for each run (which the Factory already does via `_clean_up_in_same_session`).

### 3.9 `_initialize_job` Uses Lambdas Returning Tuples of Side Effects

**File:** `factory_.py:128-146`

```python
RUN_MODE_DRY_RUN: {
    "manager": JobManagerDryRun,
    "setup": lambda: (
        self._clean_up_in_same_session(),
        self._set_input_data(*args, **kwargs),
        self._check_parameter_match(),
        asyncio.create_task(self._storage_setup()),
    ),
},
```

These lambdas return tuples where some elements are `None` (from void methods) and some are `asyncio.Task`. The code then iterates and awaits tasks. This is clever but fragile — it relies on the assumption that void methods return `None` and not something accidentally truthy. Simple sequential `if/elif` blocks would be clearer and more maintainable.

---

## 4. Abstraction Layering Analysis

### Current Layers (bottom to top):

| Layer | Components | Verdict |
|-------|-----------|---------|
| **Infrastructure** | SQLiteMetadataHandler, FileSystemDataHandler, aiosqlite, aiofiles | Good — clean, focused |
| **Storage** | LocalStorage, InMemoryStorage, Storage ABC, Models | Good — well-abstracted |
| **Execution** | TaskRunner | Too thin — single retry, no backoff |
| **Orchestration** | JobManager, JobManagerDryRun, JobManagerRerun | Decent — strategy pattern works, but JobManager is too thick |
| **Coordination** | Factory | Too thick — God Object |
| **Bridge** | FactoryExecutorManager | Unnecessary layer — should be eliminated |
| **API** | FactoryWrapper, @data_factory decorator | Good — clean user-facing API |

### Missing Abstractions:

1. **No InputConverter interface** — Input parsing is a bare function (`_default_input_converter`) at module level. As input formats grow (DataFrames, CSV files, generators), this needs to be extensible.

2. **No OutputCollector** — Output processing is tangled into Factory with direct queue access and caching logic.

3. **No RetryPolicy** — Retry logic is split between `TaskRunner` (within-task retries) and `JobManager._requeue_task` (cross-task retries). There's no unified retry policy object. The dead queue threshold is a config int passed through multiple layers.

4. **No ProgressReporter interface** — Progress is hardcoded to logger.info with ANSI escape codes. Can't plug in a progress bar, webhook, or custom reporter.

### Over-Abstractions:

1. **FactoryExecutorManager** inner classes (`Filters`, `EventLoop`, `DeadQueue`, `Resume`) — These are not real abstractions, they're namespace buckets for static methods. The `Resume` inner class is particularly problematic because it contains complex domain logic that directly constructs and mutates `Factory` instances.

2. **Registry pattern for storage** (`storage/base.py:177-189`) — The registry exists but `Factory._storage_setup()` uses a hardcoded if/else to pick storage. The registry isn't used for its intended purpose.

---

## 5. Specific Code Smells

### 5.1 Duplicate Import
```python
# factory_.py:2 and factory_.py:36
from copy import deepcopy
from copy import deepcopy
```

### 5.2 Bare Exception Catching
```python
# factory_.py:113
except (InputError, OutputError, KeyboardInterrupt, Exception) as e:
```
Listing `InputError`, `OutputError`, and then `Exception` (which catches everything) is redundant. Also catches `KeyboardInterrupt` alongside `Exception` — `KeyboardInterrupt` is a `BaseException`, and this catch structure means it gets handled the same as any other error.

### 5.3 Identity Comparison with None
```python
# job_manager.py:190
if input_data_idx == None:
```
Should be `is None`.

### 5.4 Typo in Variable Name
```python
# job_manager.py:359
fitered_num_records = 0  # should be: filtered_num_records
```

### 5.5 Docstring Placement
```python
# factory_.py:199-200
async def _finalize_and_cleanup_job(self) -> None:
    result = await self._finalize_job()
    """Handle job cleanup and error reporting."""  # docstring after first statement
```

### 5.6 Telemetry Data Has Trailing Commas Creating Tuples
```python
# factory_.py:252-253
telemetry_data.num_inputs = (len(self.original_input_data),)  # tuple, not int
telemetry_data.target_reached = ((self.job_manager.completed_count >= ...,))  # nested tuple
```
The trailing commas make these single-element tuples instead of the intended scalar values.

---

## 6. Missing Capabilities

### 6.1 No Backpressure
If the user function produces output faster than storage can persist, the output queue grows unbounded. There's no mechanism to slow down task creation based on pending storage writes.

### 6.2 No Cancellation Propagation
`KeyboardInterrupt` is caught and logged, but there's no graceful shutdown that drains in-flight tasks, saves their results, and then stops. Currently, a keyboard interrupt loses all in-flight work.

### 6.3 No Batch Processing
`batch_size` is configured but the system always processes records one at a time through `TaskRunner`. The batch concept appears to be about grouping output records, not about sending multiple inputs to the user function in one call.

### 6.4 No Rate Limiting Beyond Concurrency
Concurrency limits how many tasks run simultaneously, but there's no rate limiter (e.g., max N requests per second). For LLM API calls, this is essential to avoid hitting rate limits.

### 6.5 No Pluggable Serialization
Resume depends on cloudpickle. If a function can't be pickled (lambdas with closures, C extensions), resume silently degrades. There's no fallback or alternative serialization strategy.

---

## 7. Recommendations (Prioritized)

### P0 — Bugs to Fix Now

1. **Fix requeue logic** — Only requeue `STATUS_FAILED`, not filtered/duplicate (`job_manager.py:200`)
2. **Fix exponential backoff** — `1**retries` → `2**retries` (`task_runner.py:60`)
3. **Fix telemetry tuples** — Remove trailing commas (`factory_.py:252-253`)
4. **Fix hardcoded metadata** — Use actual project/job names and target counts (`factory_.py:352, 398-404`)

### P1 — Architecture Improvements

5. **Eliminate FactoryExecutorManager** — Move event-loop bridging to a utility, move resume logic into Factory, inline filter conversion
6. **Extract OutputCollector** — Pull output caching and filtering out of Factory into its own class
7. **Create RetryPolicy** — Unified retry config (max retries, backoff strategy, dead queue threshold) as a first-class object
8. **Use Storage capabilities instead of class name checks** — Replace `isinstance` / class name checks with capability queries

### P2 — Feature Gaps

9. **Add rate limiting** — Token-bucket or sliding-window rate limiter, configurable per-factory
10. **Add graceful shutdown** — On interrupt, wait for in-flight tasks, persist results, then stop
11. **Add backpressure** — Bound the output queue or slow task creation when storage writes are falling behind
12. **Add ProgressReporter interface** — Decouple progress reporting from hardcoded logger calls

---

## 8. Summary Assessment

| Dimension | Grade | Notes |
|-----------|-------|-------|
| **User API** | A | Clean decorator, intuitive methods, good input flexibility |
| **Storage Layer** | A- | Well-abstracted, good SQLite hardening, minor: registry unused |
| **Concurrency Model** | B | Semaphore-based works, but missing rate limiting and backpressure |
| **Component Separation** | C+ | Factory is a God Object, FactoryExecutorManager adds unnecessary indirection |
| **Error Handling** | C | Requeue bug, broken backoff, bare exception catching |
| **Code Quality** | C+ | Hardcoded test values, queue internals access, typos, docstring placement |
| **Extensibility** | B- | Hooks work well, but no pluggable input/output/progress/retry |
| **Resumability** | B+ | Cross-session resume works, cloudpickle dependency is a risk |

**Overall: B-** — The user-facing API and storage layer are solid. The middle orchestration layer (Factory + FactoryExecutorManager + JobManager) needs refactoring to achieve clean separation of concerns. There are several correctness bugs that should be fixed before production use.
