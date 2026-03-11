"""Resume job manager — replays completed tasks from storage, queues remaining."""
import asyncio
import hashlib
import json
from typing import Any, Dict, List

from starfish.common.logger import get_logger
from starfish.data_factory_v2.constants import IDX, RECORD_STATUS, STATUS_COMPLETED
from starfish.data_factory_v2.job_manager import JobManager

logger = get_logger(__name__)


class JobManagerRerun(JobManager):
    """Resumes a job from checkpoint by replaying completed work from storage."""

    async def setup_input_output_queue(self):
        """Load completed tasks from storage, queue remaining for execution."""
        prev = self.config.prev_job
        input_data = prev["input_data"]
        master_job = prev["master_job"]

        # Log resume status
        logger.info(
            f"[JOB RESUME] Picking up from checkpoint. "
            f"Previously completed: {master_job['completed_count']}/{len(input_data)}"
        )

        # Restore counters
        self.total_count = master_job["total_count"]
        self.failed_count = master_job["failed_count"]
        self.duplicate_count = master_job["duplicate_count"]
        self.filtered_count = master_job["filtered_count"]
        self.completed_count = master_job["completed_count"]
        self.config.target_count = len(input_data)

        # Hash all inputs for deduplication lookup
        hashed_items = []
        for item in input_data:
            item_str = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
            item_hash = hashlib.sha256(item_str.encode()).hexdigest()
            hashed_items.append({"data": item, "hash": item_hash})

        # Check which are already completed
        remaining = []
        replay_tasks = []

        for item in hashed_items:
            completed_jobs = await self.storage.list_execution_jobs_by_master_id_and_config_hash(
                self.config.master_job_id, item["hash"], STATUS_COMPLETED
            )
            if completed_jobs:
                for job in completed_jobs:
                    replay_tasks.append(
                        asyncio.create_task(
                            self._replay_completed(job, item["data"].get(IDX))
                        )
                    )
            else:
                remaining.append(item)

        if replay_tasks:
            await asyncio.gather(*replay_tasks)

        # Fix counter if DB disagrees
        db_completed = len(self.output)
        if self.completed_count != db_completed:
            logger.warning(
                f"Completed count mismatch: counter={self.completed_count}, "
                f"from_db={db_completed}. Using DB count."
            )
            self.completed_count = db_completed

        # Queue remaining for execution
        for item in remaining:
            await self.input_queue.put(item["data"])

    async def _replay_completed(self, job, input_idx):
        """Replay a single completed job from storage into output."""
        records = await self.storage.list_record_metadata(
            self.config.master_job_id, job.job_id
        )
        record_data = []
        for record in records:
            data = await self.storage.get_record_data(record.output_ref)
            record_data.append(data)

        result = {
            IDX: input_idx,
            RECORD_STATUS: STATUS_COMPLETED,
            "output": record_data,
        }

        # Avoid duplicates
        if result not in self.output.results:
            self.output.add(result)
