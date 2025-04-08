import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from starfish.utils.errors import DuplicateRecordError, FilterRecordError, RecordError
from starfish.utils.constants import RECORD_STATUS
from starfish.utils.event_loop import run_in_event_loop
from starfish.utils.task_runner import TaskRunner
from starfish.utils.enums import RecordStatus


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
        self.job_output = []

        # Job counters
        self.completed_count = 0

        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0
        self.total_task_run_count = 0
        self.job_run_stop_threshold = 3

    def run_orchestration(self) -> List[Any]:
        """Process batches with asyncio"""
        return run_in_event_loop(self._async_run_orchestration())

    async def _async_run_orchestration(self):
        """Main orchestration loop for the job"""
        # await self.storage.setup()
        # await self.state.setup()

        # await self.storage.save_request_config(self.job_config)
        # await self.storage.log_master_job_start(self.master_job_id)
        self.job_input_queue = self.job_config["job_input_queue"]
        self.target_count = self.job_config.get("target_count")
        # if completed count not changed for three times, then failed and break
        # this happens because of the retry mechanism when error occurs
        while self.completed_count < self.target_count and (self.total_task_run_count - self.target_count) < self.job_run_stop_threshold:
            if not self.job_input_queue.empty():
                await self.semaphore.acquire()
                input_data = self.job_input_queue.get()
                task = asyncio.create_task(self._run_single_task(input_data))
                # Create a task to handle the completion
                asyncio.create_task(self._handle_task_completion(task))
            else:
                await asyncio.sleep(1)
        return self.job_output

    async def _run_single_task(self, input_data):
        """Run a single task with error handling and storage"""
        try:
            output = await self.task_runner.run_task(self.job_config["user_func"], input_data)
           
            # Process hooks; hook return the status of the record : ENUM:  duplicate, filtered
            # gemina 2.5 slack channel; 
            # update state ensure thread safe and user-friendly
            hooks_output = []
            for hook in self.job_config.get("on_record_complete", []):
                hooks_output.append(await hook(output, self.state))
            if hooks_output.count(RecordStatus.DUPLICATE) > 0:
                raise DuplicateRecordError
            elif hooks_output.count(RecordStatus.FILTERED) > 0:
                raise FilterRecordError
            elif hooks_output.count(RecordStatus.FAILED) > 0:
                raise RecordError
            # Save record if successful
            # output_ref = await self.storage.save_record_data(output)
            output_ref = output
            return {RECORD_STATUS: RecordStatus.COMPLETED, "output_ref": output_ref}

        except (DuplicateRecordError, FilterRecordError) as e:
            return {RECORD_STATUS: RecordStatus.DUPLICATE if isinstance(e, DuplicateRecordError) else RecordStatus.FILTERED}
        except RecordError as e:
            return {RECORD_STATUS: RecordStatus.FAILED, "error": str(e)}
        except Exception as e:
            for hook in self.job_config.get("on_record_error", []):
                await hook(str(e), self.state)
            self.job_input_queue.put(input_data)
            return {RECORD_STATUS: RecordStatus.FAILED, "error": str(e)}

    async def _handle_task_completion(self, task):
        """Handle task completion and update counters"""
        result = await task
        async with self.lock:
            self.job_output.append(result)
            self.total_task_run_count += 1
            if result[RECORD_STATUS] == RecordStatus.COMPLETED:
                self.completed_count += 1
                # user can update the counter in the user-defined hook
            elif result[RECORD_STATUS] == RecordStatus.DUPLICATE:
                self.duplicate_count += 1
            elif result[RECORD_STATUS] == RecordStatus.FILTERED:
                self.filtered_count += 1
            elif result[RECORD_STATUS] == RecordStatus.FAILED:
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
