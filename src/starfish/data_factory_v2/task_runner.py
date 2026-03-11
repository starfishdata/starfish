import asyncio
import time
from copy import deepcopy
from typing import Any, Callable, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory_v2.config import RetryPolicy
from starfish.data_factory_v2.constants import IDX
from starfish.data_factory_v2.errors import TaskTimeoutError
from starfish.data_factory_v2.rate_limiter import TokenBucketRateLimiter

logger = get_logger(__name__)


class TaskRunner:
    """Executes a single user task with timeout, retry, and rate limiting.

    Fixes from v1:
    - Exponential backoff uses 2**retries instead of 1**retries
    - Rate limiting support via TokenBucketRateLimiter
    """

    def __init__(
        self,
        retry_policy: RetryPolicy,
        timeout: int = 60,
        rate_limiter: TokenBucketRateLimiter = None,
    ):
        self.retry_policy = retry_policy
        self.timeout = timeout
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(0)

    async def run_task(self, func: Callable, input_data: Dict, input_data_idx: Any) -> List[Any]:
        """Execute the user function with retry and timeout."""
        retries = 0
        start_time = time.time()

        # Strip internal index key before passing to user function
        clean_input = deepcopy({k: v for k, v in input_data.items() if k != IDX})

        while retries <= self.retry_policy.max_task_retries:
            # Rate limit before execution
            await self.rate_limiter.acquire()

            try:
                result = await asyncio.wait_for(func(**clean_input), timeout=self.timeout)
                logger.debug(f"Task completed in {time.time() - start_time:.2f}s")
                return result

            except asyncio.TimeoutError as e:
                logger.error(
                    f"Task timed out after {self.timeout}s. "
                    f"Adjust via task_timeout parameter."
                )
                raise TaskTimeoutError(f"Task timed out after {self.timeout}s") from e

            except Exception as e:
                retries += 1
                if retries > self.retry_policy.max_task_retries:
                    raise

                delay = self.retry_policy.get_delay(retries)
                logger.debug(
                    f"Retry {retries}/{self.retry_policy.max_task_retries} "
                    f"for idx {input_data_idx}, backoff {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        raise RuntimeError("Task runner exhausted retries without result")
