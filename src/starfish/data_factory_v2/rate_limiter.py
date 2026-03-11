import asyncio
import time


class TokenBucketRateLimiter:
    """Token-bucket rate limiter for controlling requests per second.

    When rate is 0 or None, no rate limiting is applied.
    """

    def __init__(self, rate: float = 0):
        """
        Args:
            rate: Maximum requests per second. 0 = unlimited.
        """
        self.rate = rate
        self._tokens = rate if rate > 0 else 0
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def is_enabled(self) -> bool:
        return self.rate > 0

    async def acquire(self) -> None:
        """Wait until a token is available."""
        if not self.is_enabled:
            return

        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self.rate, self._tokens + elapsed * self.rate)
                self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # Wait for enough time to get one token
                wait_time = (1.0 - self._tokens) / self.rate
                await asyncio.sleep(wait_time)
