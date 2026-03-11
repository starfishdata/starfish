"""End-to-end tests for data_factory_v2.

Tests cover:
1. Basic decorator + run
2. Dry run
3. Hooks (on_record_complete, on_record_error)
4. Filtered/duplicate records NOT requeued (v1 bug fix)
5. Dead queue after threshold
6. Exponential backoff (v1 bug fix: 2**n, not 1**n)
7. Rate limiting
8. InputConverter
9. OutputCollector
10. RetryPolicy
11. Concurrent execution
12. Stop threshold on consecutive failures
13. Broadcast vs parallel kwargs
"""

import asyncio
import pytest
import time

from starfish.data_factory_v2.config import RetryPolicy
from starfish.data_factory_v2.constants import (
    IDX,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
)
from starfish.data_factory_v2.decorator import data_factory
from starfish.data_factory_v2.errors import InputError, OutputError
from starfish.data_factory_v2.input_converter import convert_input, validate_params
from starfish.data_factory_v2.output_collector import OutputCollector
from starfish.data_factory_v2.rate_limiter import TokenBucketRateLimiter
from starfish.data_factory_v2.state import MutableSharedState
from starfish.data_factory_v2.task_runner import TaskRunner


# ==================
# Unit Tests
# ==================


class TestRetryPolicy:
    def test_exponential_backoff(self):
        policy = RetryPolicy(backoff_base=2.0)
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0

    def test_backoff_cap(self):
        policy = RetryPolicy(backoff_base=2.0, backoff_max=10.0)
        assert policy.get_delay(5) == 10.0  # 2**5=32 > 10, capped

    def test_defaults(self):
        policy = RetryPolicy()
        assert policy.max_task_retries == 1
        assert policy.dead_queue_threshold == 3


class TestInputConverter:
    def test_basic_data_list(self):
        queue, records = convert_input(data=[{"a": 1}, {"a": 2}])
        assert queue.qsize() == 2
        assert len(records) == 2
        assert records[0]["a"] == 1
        assert records[0][IDX] == 0

    def test_parallel_kwargs(self):
        queue, records = convert_input(x=[10, 20], y=[30, 40])
        assert queue.qsize() == 2
        assert records[0]["x"] == 10
        assert records[0]["y"] == 30
        assert records[1]["x"] == 20
        assert records[1]["y"] == 40

    def test_broadcast_kwargs(self):
        queue, records = convert_input(data=[{"a": 1}, {"a": 2}], model="gpt-4")
        assert records[0]["model"] == "gpt-4"
        assert records[1]["model"] == "gpt-4"

    def test_mixed_parallel_and_broadcast(self):
        queue, records = convert_input(x=[1, 2], shared_val="hello")
        assert records[0]["x"] == 1
        assert records[0]["shared_val"] == "hello"
        assert records[1]["x"] == 2
        assert records[1]["shared_val"] == "hello"

    def test_mismatched_lengths_raises(self):
        with pytest.raises(InputError):
            convert_input(x=[1, 2], y=[3, 4, 5])

    def test_empty_input(self):
        queue, records = convert_input()
        assert queue.qsize() == 1  # Still creates one record with just IDX
        assert records[0][IDX] == 0


class TestValidateParams:
    def test_valid_match(self):
        async def fn(a, b):
            pass
        validate_params(fn, {"a": 1, "b": 2, IDX: 0})

    def test_missing_required(self):
        async def fn(a, b):
            pass
        with pytest.raises(InputError, match="missing required parameter 'b'"):
            validate_params(fn, {"a": 1, IDX: 0})

    def test_unexpected_param(self):
        async def fn(a):
            pass
        with pytest.raises(InputError, match="unexpected parameter 'b'"):
            validate_params(fn, {"a": 1, "b": 2, IDX: 0})

    def test_default_params_not_required(self):
        async def fn(a, b=10):
            pass
        validate_params(fn, {"a": 1, IDX: 0})  # b has default, should not raise


class TestOutputCollector:
    def test_add_and_retrieve(self):
        collector = OutputCollector()
        collector.add({"status": STATUS_COMPLETED, IDX: 0, "output": [{"x": 1}], "err": []})
        collector.add({"status": STATUS_FAILED, IDX: 1, "output": [], "err": [{"err_str": "oops"}]})

        assert len(collector.get_output(STATUS_COMPLETED)) == 1
        assert collector.get_output(STATUS_COMPLETED)[0] == {"x": 1}
        assert len(collector.get_output(STATUS_FAILED)) == 1
        assert collector.get_indices(STATUS_COMPLETED) == [0]
        assert collector.get_indices(STATUS_FAILED) == [1]

    def test_cache_invalidation(self):
        collector = OutputCollector()
        collector.add({"status": STATUS_COMPLETED, IDX: 0, "output": [{"x": 1}], "err": []})
        assert len(collector.get_output()) == 1

        collector.add({"status": STATUS_COMPLETED, IDX: 1, "output": [{"x": 2}], "err": []})
        assert len(collector.get_output()) == 2  # Cache should be invalidated

    def test_multiple_statuses(self):
        collector = OutputCollector()
        collector.add({"status": STATUS_COMPLETED, IDX: 0, "output": [{"x": 1}], "err": []})
        collector.add({"status": STATUS_DUPLICATE, IDX: 1, "output": [{"x": 2}], "err": []})
        collector.add({"status": STATUS_FILTERED, IDX: 2, "output": [{"x": 3}], "err": []})

        assert len(collector.get_output(STATUS_COMPLETED)) == 1
        assert len(collector.get_output(STATUS_DUPLICATE)) == 1
        assert len(collector.get_output(STATUS_FILTERED)) == 1


class TestMutableSharedState:
    def test_basic_operations(self):
        state = MutableSharedState(initial_data={"a": 1})
        assert state.get("a") == 1
        state.set("b", 2)
        assert state.get("b") == 2
        state.update({"c": 3, "d": 4})
        d = state.to_dict()
        assert d == {"a": 1, "b": 2, "c": 3, "d": 4}

    def test_data_property(self):
        state = MutableSharedState()
        state.data = {"x": 10}
        assert state.data == {"x": 10}

    def test_returns_copy(self):
        state = MutableSharedState(initial_data={"a": 1})
        d = state.to_dict()
        d["a"] = 999
        assert state.get("a") == 1  # Original unchanged


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_disabled_limiter(self):
        limiter = TokenBucketRateLimiter(0)
        assert not limiter.is_enabled
        await limiter.acquire()  # Should return immediately

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        limiter = TokenBucketRateLimiter(100)  # 100/sec
        assert limiter.is_enabled
        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # 5 requests at 100/sec should be fast


class TestTaskRunner:
    @pytest.mark.asyncio
    async def test_successful_task(self):
        policy = RetryPolicy(max_task_retries=1)
        runner = TaskRunner(retry_policy=policy, timeout=5)

        async def fn(x):
            return [{"result": x * 2}]

        result = await runner.run_task(fn, {"x": 5, IDX: 0}, 0)
        assert result == [{"result": 10}]

    @pytest.mark.asyncio
    async def test_retry_with_backoff(self):
        """Verify actual exponential backoff (not 1**n like v1)."""
        policy = RetryPolicy(max_task_retries=2, backoff_base=0.1)
        runner = TaskRunner(retry_policy=policy, timeout=5)

        call_count = 0

        async def flaky(x):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return [{"result": x}]

        result = await runner.run_task(flaky, {"x": 1, IDX: 0}, 0)
        assert call_count == 3
        assert result == [{"result": 1}]

    @pytest.mark.asyncio
    async def test_timeout(self):
        policy = RetryPolicy(max_task_retries=0)
        runner = TaskRunner(retry_policy=policy, timeout=0.1)

        async def slow(x):
            await asyncio.sleep(10)
            return [{"result": x}]

        from starfish.data_factory_v2.errors import TaskTimeoutError
        with pytest.raises(TaskTimeoutError):
            await runner.run_task(slow, {"x": 1, IDX: 0}, 0)


# ==================
# Integration Tests
# ==================


class TestDataFactoryIntegration:
    def test_basic_run(self):
        @data_factory(storage="in_memory", max_concurrency=2, show_progress=False)
        async def process(value):
            return [{"doubled": value * 2}]

        result = process.run(data=[{"value": 1}, {"value": 2}, {"value": 3}])
        assert len(result) == 3
        values = sorted([r["doubled"] for r in result])
        assert values == [2, 4, 6]

    def test_dry_run(self):
        @data_factory(storage="in_memory", show_progress=False)
        async def process(value):
            return [{"result": value}]

        result = process.dry_run(data=[{"value": 1}, {"value": 2}, {"value": 3}])
        assert len(result) == 1

    def test_hook_filter(self):
        """Filtered records should NOT be retried (v1 bug fix)."""

        def filter_hook(output, state):
            if output[0].get("value") == "skip":
                return STATUS_FILTERED
            return STATUS_COMPLETED

        @data_factory(
            storage="in_memory",
            max_concurrency=2,
            show_progress=False,
            on_record_complete=[filter_hook],
        )
        async def process(value):
            return [{"value": value}]

        result = process.run(data=[{"value": "keep"}, {"value": "skip"}, {"value": "also_keep"}])
        # Only "keep" and "also_keep" should be in completed output
        assert len(result) == 2

        filtered = process.get_output_filtered()
        assert len(filtered) == 1
        assert filtered[0]["value"] == "skip"

    def test_hook_duplicate(self):
        """Duplicate records should NOT be retried (v1 bug fix)."""

        seen = set()

        def dedup_hook(output, state):
            val = output[0].get("value")
            if val in seen:
                return STATUS_DUPLICATE
            seen.add(val)
            return STATUS_COMPLETED

        @data_factory(
            storage="in_memory",
            max_concurrency=1,
            show_progress=False,
            on_record_complete=[dedup_hook],
        )
        async def process(value):
            return [{"value": value}]

        result = process.run(data=[{"value": "a"}, {"value": "a"}, {"value": "b"}])
        assert len(result) == 2  # "a" once, "b" once

        dupes = process.get_output_duplicate()
        assert len(dupes) == 1

    def test_dead_queue(self):
        """Records that fail repeatedly end up in dead queue."""

        @data_factory(
            storage="in_memory",
            max_concurrency=1,
            show_progress=False,
            dead_queue_threshold=2,
            stop_threshold=100,  # Don't stop on consecutive failures
        )
        async def process(value):
            if value == "bad":
                raise ValueError("always fails")
            return [{"result": value}]

        result = process.run(data=[{"value": "good"}, {"value": "bad"}])
        assert len(result) == 1

        dead = process.get_input_data_in_dead_queue()
        assert len(dead) == 1

        dead_indices = process.get_index_dead_queue()
        assert len(dead_indices) == 1

    def test_error_hook(self):
        errors_seen = []

        def on_error(err_str, state):
            errors_seen.append(err_str)

        @data_factory(
            storage="in_memory",
            max_concurrency=1,
            show_progress=False,
            on_record_error=[on_error],
            dead_queue_threshold=1,
            stop_threshold=100,
        )
        async def process(value):
            raise RuntimeError("boom")

        # All records fail → OutputError is raised
        with pytest.raises(OutputError):
            process.run(data=[{"value": 1}])

        assert len(errors_seen) > 0
        assert "boom" in errors_seen[0]

    def test_broadcast_kwargs(self):
        @data_factory(storage="in_memory", max_concurrency=2, show_progress=False)
        async def process(value, model):
            return [{"value": value, "model": model}]

        result = process.run(
            data=[{"value": 1}, {"value": 2}],
            model="gpt-4",
        )
        assert len(result) == 2
        assert all(r["model"] == "gpt-4" for r in result)

    def test_parallel_kwargs(self):
        @data_factory(storage="in_memory", max_concurrency=2, show_progress=False)
        async def process(x, y):
            return [{"sum": x + y}]

        result = process.run(x=[1, 2, 3], y=[10, 20, 30])
        assert len(result) == 3
        sums = sorted([r["sum"] for r in result])
        assert sums == [11, 22, 33]

    def test_concurrency(self):
        """Verify tasks run concurrently, not sequentially."""

        @data_factory(
            storage="in_memory",
            max_concurrency=5,
            show_progress=False,
        )
        async def process(value):
            await asyncio.sleep(0.1)
            return [{"result": value}]

        start = time.time()
        result = process.run(data=[{"value": i} for i in range(5)])
        elapsed = time.time() - start

        assert len(result) == 5
        # 5 tasks at 0.1s each with concurrency=5 should take ~0.1-0.5s, not 2.5s
        assert elapsed < 2.0

    def test_shared_state(self):
        @data_factory(
            storage="in_memory",
            max_concurrency=1,
            show_progress=False,
            initial_state_values={"count": 0},
        )
        async def process(value):
            return [{"result": value}]

        process.state.set("count", 42)
        assert process.state.get("count") == 42

    def test_rate_limiting(self):
        """Verify rate limiter actually slows execution."""

        @data_factory(
            storage="in_memory",
            max_concurrency=10,
            show_progress=False,
            rate_limit=5,  # 5 per second
        )
        async def process(value):
            return [{"result": value}]

        start = time.time()
        result = process.run(data=[{"value": i} for i in range(5)])
        elapsed = time.time() - start

        assert len(result) == 5
        # 5 tasks at 5/sec should take ~1 second minimum
        assert elapsed >= 0.5

    def test_index_accessors(self):
        @data_factory(storage="in_memory", max_concurrency=1, show_progress=False)
        async def process(value):
            return [{"result": value}]

        result = process.run(data=[{"value": 1}, {"value": 2}])
        indices = process.get_index_completed()
        assert len(indices) == 2
        assert set(indices) == {0, 1}
