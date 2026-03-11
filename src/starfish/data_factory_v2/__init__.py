"""Data Factory v2 — Clean architecture rewrite.

Usage:
    from starfish.data_factory_v2 import data_factory

    @data_factory(max_concurrency=5, rate_limit=10)
    async def generate(prompt: str):
        return [{"text": f"Generated from: {prompt}"}]

    result = generate.run(data=[{"prompt": "hello"}, {"prompt": "world"}])
"""

from starfish.data_factory_v2.decorator import data_factory, resume_from_checkpoint, FactoryWrapper
from starfish.data_factory_v2.config import FactoryConfig, RetryPolicy
from starfish.data_factory_v2.state import MutableSharedState
from starfish.data_factory_v2.progress import ProgressReporter, LogProgressReporter, NullProgressReporter
from starfish.data_factory_v2.rate_limiter import TokenBucketRateLimiter
from starfish.data_factory_v2.errors import InputError, OutputError, TaskTimeoutError, NoResumeSupportError
from starfish.data_factory_v2.constants import (
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FILTERED,
    STATUS_FAILED,
)

__all__ = [
    # Main API
    "data_factory",
    "resume_from_checkpoint",
    "FactoryWrapper",
    # Config
    "FactoryConfig",
    "RetryPolicy",
    # State
    "MutableSharedState",
    # Progress
    "ProgressReporter",
    "LogProgressReporter",
    "NullProgressReporter",
    # Rate limiting
    "TokenBucketRateLimiter",
    # Errors
    "InputError",
    "OutputError",
    "TaskTimeoutError",
    "NoResumeSupportError",
    # Constants
    "STATUS_COMPLETED",
    "STATUS_DUPLICATE",
    "STATUS_FILTERED",
    "STATUS_FAILED",
]
