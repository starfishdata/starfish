import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from starfish.utils.errors import DuplicateRecordError, FilterRecordError
from starfish.utils.event_loop import run_in_event_loop
from starfish.utils.task_runner import TaskRunner


class JobManager:
    def __init__(self, job_config: Dict[str, Any], storage, state):
        self.job_config = job_config
        # sqlite storage
        self.storage = storage
        # cache state
        self.state = state
        # not above a number every minute
        self.semaphore = asyncio.Semaphore(job_config.get("max_concurrency"))
        self.lock = asyncio.Lock()
        self.task_runner = TaskRunner()
        self.job_input_queue = None

        # Job counters
        self.completed_count = 0

        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0

    def run_orchestration(self) -> List[Any]:
        """Process batches with asyncio"""
        run_in_event_loop(self._async_run_orchestration())

    async def _async_run_orchestration(self):
        """Main orchestration loop for the job"""
        # await self.storage.setup()
        # await self.state.setup()

        # await self.storage.save_request_config(self.job_config)
        # await self.storage.log_master_job_start(self.master_job_id)
        self.job_input_queue = self.job_config["job_input_queue"]
        self.target_count = self.job_config.get("target_count")
        master_job_start_time = datetime.now()
        time_out_seconds = 60 * 1  # target_count : if length of input data or specific number
        # if completed count not changed for three times, then failed and break
        while self.completed_count < self.target_count:
            if not self.job_input_queue.empty():
                if datetime.now() - master_job_start_time > timedelta(seconds=time_out_seconds):
                    print(f"No more data to process after {datetime.now() - master_job_start_time} seconds")
                    break
                await self.semaphore.acquire()
                input_data = self.job_input_queue.get()
                task = asyncio.create_task(self._run_single_task(input_data))
                # task.add_done_callback(self._handle_task_completion)
                # Create a task to handle the completion
                asyncio.create_task(self._handle_task_completion(task))
            else:
                if datetime.now() - master_job_start_time > timedelta(seconds=time_out_seconds):
                    print(f"No more data to process after {datetime.now() - master_job_start_time} seconds")
                    break
                await asyncio.sleep(1)

    async def _run_single_task(self, input_data):
        """Run a single task with error handling and storage"""
        try:
            output = await self.task_runner.run_task(self.job_config["user_func"], input_data)

            # Process hooks
            for hook in self.job_config.get("on_record_complete", []):
                await hook(output, self.state)

            # Save record if successful
            # output_ref = await self.storage.save_record_data(output)
            output_ref = {}
            return {"status": "completed", "output_ref": output_ref}

        except (DuplicateRecordError, FilterRecordError) as e:
            return {"status": "duplicate" if isinstance(e, DuplicateRecordError) else "filtered"}
        except Exception as e:
            self.job_input_queue.put(input_data)
            return {"status": "failed", "error": str(e)}

    async def _handle_task_completion(self, task):
        """Handle task completion and update counters"""
        result = await task
        async with self.lock:
            if result["status"] == "completed":
                self.completed_count += 1
            elif result["status"] == "duplicate":
                self.duplicate_count += 1
            elif result["status"] == "filtered":
                self.filtered_count += 1
            else:
                self.failed_count += 1

            # await self.storage.log_record_metadata(
            #     self.master_job_id,
            #     result
            # )

            self.semaphore.release()

            if self.completed_count >= self.target_count:
                # how to get the job status
                await self._finalize_job()

    async def _finalize_job(self):
        """Clean up after job completion"""
        # await self.storage.log_master_job_end(self.master_job_id)
        # await self.storage.close()
        # await self.state.close()

    def _prepare_next_input(self):
        """Prepare input data for the next task"""
        # Implementation depends on specific use case
        pass

    def update_job_config(self, job_config: Dict[str, Any]):
        """Update job config by merging new values with existing config"""
        self.job_config = {**self.job_config, **job_config}
