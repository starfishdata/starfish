from asyncio import Queue

from starfish.common.logger import get_logger
from starfish.data_factory_v2.job_manager import JobManager

logger = get_logger(__name__)


class JobManagerDryRun(JobManager):
    """Dry-run variant: processes exactly 1 record, no persistence."""

    async def setup_input_output_queue(self):
        first_item = await self.input_queue.get()
        self.input_queue = Queue()
        await self.input_queue.put(first_item)
        self.config.target_count = 1
