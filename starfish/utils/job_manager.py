
from datetime import datetime
from time import sleep
from functools import lru_cache
from typing import Callable
from starfish.utils.task_runner import TaskRunner
# TODO: isit in the user process level or the service process level?
class JobManager:
    def __init__(self, rate_limit: int = 10, batch_size: int = 10):
        self.task_runner = TaskRunner()   
        self.rate_limit = rate_limit  # requests per second
        self.batch_size = batch_size
        self.job_stats = {
            'total': 0,
            'finished': 0,
            'failed': 0,
            'pending': 0,
            "retries": 0
        }
        self.callbacks = {
            'on_start': None,
            'on_job_complete': None,
            'on_job_error': None,
        }
        self.batch_records = {}
        
        # Register callbacks
        self.task_runner.add_callback('on_task_start', self._on_start)
        self.task_runner.add_callback('on_task_complete', self._on_batch_complete)
        self.task_runner.add_callback('on_task_error', self._on_error)

    def _on_start(self):
        """Initialize job statistics"""
        pass

    def _on_batch_complete(self, batch_result):
        """Update stats and cache successful batches"""
        self.job_stats['finished'] += 1
        self.job_stats['pending'] -= 1
        self._cache_batch(str(batch_result))
        self._execute_callbacks('on_job_complete', batch_result)

    def _on_error(self, error :str):
        """Handle failed batches"""
        self.job_stats['failed'] += 1
        self.job_stats['pending'] -= 1
        self._cache_batch(str(error))
        self._execute_callbacks('on_job_error', error)
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
    # task_runner
    def execute_with_retry(self, func: Callable, batches= None, max_retries: int = 3):
        """Execute function with retry logic and rate limiting"""
        retries = 0
        # maybe better to use retries in a single request instead in the batch level.
        while retries <= max_retries:
            try:
                # Rate limiting
                if self.job_stats['pending'] >= self.rate_limit:
                    sleep(1)
                
                self.job_stats['total'] += self.batch_size
                self.job_stats['pending'] += self.batch_size
                if retries > 0:
                    self.job_stats['retries'] += self.batch_size
                
                return self.task_runner.run_batches(func,batches)
                
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

    def add_callback(self, event: str, callback: Callable):
        """Register callback functions"""
        if event in self.callbacks:
            self.callbacks[event] = callback

    def _execute_callbacks(self, event: str, *args):
        """Trigger registered callbacks"""
        if callback := self.callbacks.get(event):
            callback(*args)