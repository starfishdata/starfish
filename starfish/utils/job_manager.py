
from datetime import datetime
from time import sleep
from functools import lru_cache
from typing import Callable
from starfish.utils.data_factory import DataFactory

# TODO: isit in the user process level or the service process level?
class JobManager:
    def __init__(self, data_factory: DataFactory, rate_limit: int = 10):
        self.data_factory = data_factory
        self.rate_limit = rate_limit  # requests per second
        self.job_stats = {
            'total': 0,
            'finished': 0,
            'failed': 0,
            'pending': 0,
            "retries": 0
        }
        self.batch_records = {}
        
        # Register callbacks
        self.data_factory.add_callback('on_start', self._on_start)
        self.data_factory.add_callback('on_batch_complete', self._on_batch_complete)
        self.data_factory.add_callback('on_error', self._on_error)

    def _on_start(self):
        """Initialize job statistics"""
        # self.job_stats = {
        #     'total': 0,
        #     'finished': 0,
        #     'failed': 0,
        #     'pending': 0
        # }

    def _on_batch_complete(self, batch_result, batch_id):
        """Update stats and cache successful batches"""
        self.job_stats['finished'] += 1
        self.job_stats['pending'] -= 1
        self._cache_batch(batch_result)

    def _on_error(self, error, batch_id):
        """Handle failed batches"""
        self.job_stats['failed'] += 1
        self.job_stats['pending'] -= 1
        self._cache_batch(error)

    @lru_cache(maxsize=1000)
    def _cache_batch(self, batch_result):
        """Cache successful batch results"""
        timestamp = datetime.now().isoformat()
        # need consider what to hash to avoid duplicate user case
        batch_id = hash(tuple(batch_result))
        self.batch_records[batch_id] = {
            'timestamp': timestamp,
            'data': batch_result
        }

    def execute_with_retry(self, func: Callable, max_retries: int = 3, *args, **kwargs):
        """Execute function with retry logic and rate limiting"""
        retries = 0
        # maybe better to use retries in a single request instead in the batch level.
        while retries <= max_retries:
            try:
                # Rate limiting
                if self.job_stats['pending'] >= self.rate_limit:
                    sleep(1)
                
                self.job_stats['total'] += self.data_factory.batch_size
                self.job_stats['pending'] += self.data_factory.batch_size
                if retries > 0:
                    self.job_stats['retries'] += self.data_factory.batch_size
                
                return self.data_factory(func)(*args, **kwargs)
                
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    raise e
                sleep(2 ** retries)  # exponential backoff

    def get_job_status(self):
        """Return current job statistics"""
        return self.job_stats

    def get_cached_batches(self):
        """Return all cached batch records"""
        return self.batch_records

    def clear_cache(self):
        """Clear cached batch records"""
        self.batch_records.clear()
        self._cache_batch.cache_clear()