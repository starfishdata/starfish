import asyncio
import datetime
from typing import Any, Dict, List
import uuid
from queue import Queue
from starfish.utils.errors import DuplicateRecordError, FilterRecordError, RecordError
from starfish.utils.constants import RECORD_STATUS, STATUS_MOJO_MAP
from starfish.utils.event_loop import run_in_event_loop
from starfish.utils.task_runner import TaskRunner
from starfish.utils.constants import RECORD_STATUS_COMPLETED, RECORD_STATUS_DUPLICATE, RECORD_STATUS_FILTERED, RECORD_STATUS_FAILED
from starfish.new_storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)
from starfish.utils.state import MutableSharedState
from starfish.new_storage.base import Storage    


class JobManager:
    def __init__(self, master_job_id: str, job_config: Dict[str, Any], storage: Storage, state: MutableSharedState):
        self.master_job_id = master_job_id
        self.job_config = job_config
        self.storage = storage
        self.state = state
        self.semaphore = asyncio.Semaphore(job_config.get("max_concurrency"))
        self.lock = asyncio.Lock()
        self.task_runner = TaskRunner()
        self.job_input_queue = Queue()
        # it shall be a thread safe queue
        self.job_output = Queue()
        # Job counters
        self.completed_count = 0
        self.duplicate_count = 0
        self.filtered_count = 0
        self.failed_count = 0
        self.total_task_run_count = 0
        self.job_run_stop_threshold = 3
        self.job_id = str(uuid.uuid4())
        self.show_progress = job_config.get("show_progress") 
        
        self.progress_lock = asyncio.Lock()

    async def create_execution_job(self):
        print("\n3. Creating execution job...")
       
        self.job = GenerationJob(job_id=self.job_id, master_job_id=self.master_job_id, status="running", worker_id="test-worker-1")
        await self.storage.log_execution_job_start(self.job)
        print(f"  - Created execution job: {self.job.job_id}")

    async def update_execution_job_status(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        self.job.status = "running"
        self.job.start_time = now
        await self.storage.log_execution_job_start(self.job)
        print("  - Updated execution job status to: running")

    async def job_save_record_data(self, records, task_status:str) -> List[str]:
        print("\n5. Saving record data...")
        output_ref_list = []
        storage_class_name = self.storage.__class__.__name__
        if storage_class_name == "LocalStorage":
            for i, record in enumerate(records):
            
                record["record_uid"] = str(uuid.uuid4())
                output_ref = await self.storage.save_record_data(record["record_uid"], self.master_job_id, self.job_id, record)
                record["job_id"] = self.job_id
                # Update the record with the output reference
                record["master_job_id"] = self.master_job_id
                record["status"] = task_status
                record["output_ref"] = output_ref
                record["end_time"] = datetime.datetime.now(datetime.timezone.utc)
                # Convert dict to Pydantic model
                record_model = Record(**record)
                await self.storage.log_record_metadata(record_model)
                print(f"  - Saved data for record {i}: {output_ref}")
                output_ref_list.append(output_ref)     
        return output_ref_list

    async def complete_execution_job(self):
        print("\n6. Completing execution job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        counts = {"completed": self.completed_count, 
                  "filtered": self.filtered_count, 
                  "duplicate": self.duplicate_count, 
                  "failed": self.failed_count}
        await self.storage.log_execution_job_end(self.job_id, "completed", counts, now, now)
        print("  - Marked execution job as completed")
    
    def is_job_to_stop(self) -> bool:
        # self.completed_count < self.target_count and not self.is_job_to_stop()
        #or if no failed status, then no task added into the job_input_queue
        #item[RECORD_STATUS] != RECORD_STATUS_FAILED 
        #(self.total_task_run_count-self.failed_count) >= self.target_count
        items_check = list(self.job_output.queue)[-1*self.job_run_stop_threshold:]
        consecutive_not_completed = len(items_check) == self.job_run_stop_threshold and all(
            item[RECORD_STATUS] != RECORD_STATUS_COMPLETED for item in items_check)
        total_tasks_reach_target = (self.total_task_run_count >= self.target_count)
        return consecutive_not_completed and total_tasks_reach_target
    
    def is_consecutive_not_errors(self) -> bool:
        items_check = list(self.job_output.queue)[-1*self.job_run_stop_threshold:]
        consecutive_not_completed = len(items_check) == self.job_run_stop_threshold and all(
            item[RECORD_STATUS] != RECORD_STATUS_FAILED for item in items_check)
        total_tasks_reach_target = (self.total_task_run_count >= self.target_count)
        return consecutive_not_completed and total_tasks_reach_target
    
    def run_orchestration(self) -> List[Any]:
        """Process batches with asyncio"""
        return run_in_event_loop(self._async_run_orchestration())

    async def _async_run_orchestration(self) -> List[Any]:
        """Main orchestration loop for the job"""
        await self.create_execution_job()
        self.job_input_queue = self.job_config["job_input_queue"]
        self.target_count = self.job_config.get("target_count")
        
        if self.show_progress:
            self.progress = self.job_config.get("progress")
            self.progress_tasks = self.job_config.get("progress_tasks")
            self.progress.start()
        while not self.is_job_to_stop():
            if not self.job_input_queue.empty():
                await self.semaphore.acquire()
                input_data = self.job_input_queue.get()
                task = asyncio.create_task(self._run_single_task(input_data))
                asyncio.create_task(self._handle_task_completion(task))
            else:
                if self.is_consecutive_not_errors():
                    break
                await asyncio.sleep(1)
        return list(self.job_output.queue)

    async def _run_single_task(self, input_data) -> List[Dict[str, Any]]:
        """Run a single task with error handling and storage"""
        output = []
        output_ref = []
        task_status = RECORD_STATUS_COMPLETED
        try:
            output = await self.task_runner.run_task(self.job_config["user_func"], input_data)
            # Save record all status except failed (not user-defined hook returns failed); 
            # if user-defined hook returns failed, still save the record
            # Process hooks; hook return the status of the record : ENUM:  duplicate, filtered
            # gemina 2.5 slack channel; 
            # update state ensure thread safe and user-friendly
            hooks_output = []
            # class based hooks. use semaphore to ensure thread safe
            for hook in self.job_config.get("on_record_complete", []):
                hooks_output.append(await hook(output, self.state))
            if hooks_output.count(RECORD_STATUS_DUPLICATE) > 0:
                task_status = RECORD_STATUS_DUPLICATE
            elif hooks_output.count(RECORD_STATUS_FILTERED) > 0:
                task_status = RECORD_STATUS_FILTERED 
            output_ref = await self.job_save_record_data(output,task_status)

        except Exception as e:
            for hook in self.job_config.get("on_record_error", []):
                await hook(str(e), self.state)
            self.job_input_queue.put(input_data)
            task_status = RECORD_STATUS_FAILED
        finally:
            return {RECORD_STATUS: task_status, "output_ref": output_ref,"output":output}

    async def _handle_task_completion(self, task):
        """Handle task completion and update counters"""
        result = await task
        async with self.lock:
            self.job_output.put(result)
            self.total_task_run_count += 1
            task_status = result[RECORD_STATUS]
            # Update counters based on task status
            if task_status == RECORD_STATUS_COMPLETED:
                self.completed_count += 1
            elif task_status == RECORD_STATUS_DUPLICATE:
                self.duplicate_count += 1
            elif task_status == RECORD_STATUS_FILTERED:
                self.filtered_count += 1
            else:
                self.failed_count += 1
            await self._update_progress(task_status, STATUS_MOJO_MAP[task_status])
            self.semaphore.release()
            if self.completed_count >= self.target_count:
                await self._finalize_job()

    async def _finalize_job(self):
        """Clean up after job completion"""
        await self.complete_execution_job()

    def _prepare_next_input(self):
        """Prepare input data for the next task"""
        # Implementation depends on specific use case
        pass

    def update_job_config(self, job_config: Dict[str, Any]):
        """Update job config by merging new values with existing config"""
        self.job_config = {**self.job_config, **job_config}

    async def _update_progress(self, counter_type: str, emoji: str):
        """Thread-safe progress bar update"""
        if not self.show_progress:
            return
        async with self.progress_lock:
            task_id = self.progress_tasks[counter_type]
            if task_id is not None:
                count = getattr(self, f"{counter_type}_count")
                self.progress.update(task_id, advance=1, status=f"{emoji} {count}")
                # Force refresh the progress display
                self.progress.refresh()
