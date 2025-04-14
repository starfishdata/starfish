import asyncio
import datetime
import hashlib
import json
from typing import Any, Dict, List
import uuid
from queue import Queue
from starfish.core.data_factory.errors import DuplicateRecordError, FilterRecordError, RecordError
from starfish.core.data_factory.constants import RECORD_STATUS, STATUS_MOJO_MAP, RUN_MODE, RUN_MODE_RE_RUN, RUN_MODE_DRY_RUN
from starfish.core.data_factory.event_loop import run_in_event_loop
from starfish.core.data_factory.task_runner import TaskRunner
from starfish.core.data_factory.constants import STATUS_COMPLETED, STATUS_DUPLICATE, STATUS_FILTERED, STATUS_FAILED
from starfish.core.data_factory.storage.models import (
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
)
from starfish.core.data_factory.state import MutableSharedState
from starfish.core.data_factory.storage.base import Storage    
from starfish.common.logger import get_logger

logger = get_logger(__name__)
# from starfish.common.logger_new import logger

class JobManager:
    def __init__(self, job_config: Dict[str, Any], storage: Storage):
        self.job_config = job_config
        self.storage = storage
        self.state = job_config.get("state", {})
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
        self.total_count = 0
        self.job_run_stop_threshold = 3

    async def create_execution_job(self, job_uuid: str, input_data: Dict[str, Any]):
        logger.debug("\n3. Creating execution job...")
        input_data_str = json.dumps(input_data)
        self.job = GenerationJob(job_id=job_uuid, master_job_id=self.job_config["master_job_id"], 
                                 status="running", worker_id="test-worker-1", 
                                 run_config=input_data_str,
                                 run_config_hash=hashlib.sha256(input_data_str.encode()).hexdigest())
        await self.storage.log_execution_job_start(self.job)
        logger.debug(f"  - Created execution job: {job_uuid}")

    # async def update_execution_job_status(self):
    #     now = datetime.datetime.now(datetime.timezone.utc)
    #     self.job.status = "running"
    #     self.job.start_time = now
    #     await self.storage.log_execution_job_start(self.job)
    #     logger.debug("  - Updated execution job status to: running")

    async def job_save_record_data(self, records, task_status:str, input_data: Dict[str, Any]) -> List[str]:
        
        output_ref_list = []
        if self.job_config.get(RUN_MODE) == RUN_MODE_DRY_RUN:
            return output_ref_list
        logger.debug("\n5. Saving record data...")
        storage_class_name = self.storage.__class__.__name__
        job_uuid = str(uuid.uuid4())
        await self.create_execution_job(job_uuid, input_data)
        if storage_class_name == "LocalStorage":
            for i, record in enumerate(records):
                record_uid = str(uuid.uuid4())
                output_ref = await self.storage.save_record_data(record_uid, self.job_config["master_job_id"], job_uuid, record)
                record["job_id"] = job_uuid
                record["master_job_id"] = self.job_config["master_job_id"]
                record["status"] = task_status
                record["output_ref"] = output_ref
                record["end_time"] = datetime.datetime.now(datetime.timezone.utc)
                record_model = Record(**record)
                await self.storage.log_record_metadata(record_model)
                logger.debug(f"  - Saved data for record {i}: {output_ref}")
                output_ref_list.append(output_ref) 
        await self.complete_execution_job(job_uuid)
        return output_ref_list

    async def complete_execution_job(self,job_uuid: str):
        logger.debug("\n6. Completing execution job...")
        now = datetime.datetime.now(datetime.timezone.utc)
        counts = {STATUS_COMPLETED: self.completed_count, 
                  STATUS_FILTERED: self.filtered_count, 
                  STATUS_DUPLICATE: self.duplicate_count, 
                  STATUS_FAILED: self.failed_count}
        await self.storage.log_execution_job_end(job_uuid, STATUS_COMPLETED, counts, now, now)
        logger.debug("  - Marked execution job as completed")
    
    def is_job_to_stop(self) -> bool:
        # items_check = list(self.job_output.queue)[-1*self.job_run_stop_threshold:]
        # consecutive_not_completed = len(items_check) == self.job_run_stop_threshold and all(
        #     item[RECORD_STATUS] != STATUS_COMPLETED for item in items_check)
        # #consecutive_not_completed and 
        total_tasks_reach_target = (self.completed_count >= self.target_count)
        return total_tasks_reach_target
    
    
    def run_orchestration(self):
        """Process batches with asyncio"""
        self.job_input_queue = self.job_config["job_input_queue"]
        self.target_count = self.job_config.get("target_count")
        run_mode = self.job_config.get(RUN_MODE)
        if run_mode == RUN_MODE_RE_RUN:
            self.job_input_queue = Queue()
            run_in_event_loop(self._async_run_orchestration_re_run())
        elif run_mode == RUN_MODE_DRY_RUN:
            run_in_event_loop(self._async_run_orchestration())
        else:
            run_in_event_loop(self._async_run_orchestration())

    async def _async_run_orchestration_re_run(self): 
            input_dict = self.job_config.get("input_dict", {})
            for input_data_hash, input_data in input_dict.items():
                
                runned_tasks = await self.storage.list_execution_jobs_by_master_id_and_config_hash(self.job_config["master_job_id"], 
                        input_data_hash, STATUS_COMPLETED)
                logger.debug(f"Task already runned, returning output from storage")
                # put the runned tasks output to the job output
                for task in runned_tasks:
                    records_metadata = await self.storage.list_record_metadata(self.job_config["master_job_id"], task.job_id)
                    for record in records_metadata:
                        record_data = await self.storage.get_record_data(record.output_ref)
                        self.job_output.put(record_data)
                        self.total_count += 1
                        self.completed_count += 1
                # run the rest of the tasks
                logger.debug(f"Task not runned, running task")
                for _ in range(input_data["count"] - len(runned_tasks)):
                    self.job_input_queue.put(input_data["data"])
                    #self._create_single_task(input_data["data"])
            await self._async_run_orchestration()

    async def _async_run_orchestration(self):
        """Main orchestration loop for the job"""
        
        while not self.is_job_to_stop():
            logger.debug(f"Job is not to stop, checking job input queue")
            if not self.job_input_queue.empty():
                logger.debug(f"Job input queue is not empty, acquiring semaphore")
                await self.semaphore.acquire()
                logger.debug(f"Semaphore acquired, waiting for task to complete")
                input_data = self.job_input_queue.get()
                self._create_single_task(input_data)
                
            else:
                logger.info(f"No task to run, waiting for task to complete")
                await asyncio.sleep(1)

    def _create_single_task(self, input_data):
        task = asyncio.create_task(self._run_single_task(input_data))
        asyncio.create_task(self._handle_task_completion(task))
        logger.debug(f"Task created, waiting for task to complete")

    async def _run_single_task(self, input_data) -> List[Dict[str, Any]]:
        """Run a single task with error handling and storage"""
        output = []
        output_ref = []
        task_status = STATUS_COMPLETED
        try:
            
            output = await self.task_runner.run_task(self.job_config["user_func"], input_data)
            hooks_output = []
            # class based hooks. use semaphore to ensure thread safe
            for hook in self.job_config.get("on_record_complete", []):
                hooks_output.append(await hook(output, self.state))
            if hooks_output.count(STATUS_DUPLICATE) > 0:
                # duplicate filtered need retry
                task_status = STATUS_DUPLICATE
            elif hooks_output.count(STATUS_FILTERED) > 0:
                task_status = STATUS_FILTERED 
            output_ref = await self.job_save_record_data(output,task_status,input_data)
        except Exception as e:
            logger.error(f"Error running task: {e}")
            for hook in self.job_config.get("on_record_error", []):
                await hook(str(e), self.state)
            task_status = STATUS_FAILED
        finally:
            # if task is not completed, put the input data back to the job input queue
            if task_status != STATUS_COMPLETED:
                logger.debug(f"Task is not completed as {task_status}, putting input data back to the job input queue")
                self.job_input_queue.put(input_data)
            return {RECORD_STATUS: task_status, "output_ref": output_ref,"output":output}

    async def _handle_task_completion(self, task):
        """Handle task completion and update counters"""
        result = await task
        async with self.lock:
            self.job_output.put(result)
            self.total_count += 1
            task_status = result[RECORD_STATUS]
            # Update counters based on task status
            if task_status == STATUS_COMPLETED:
                self.completed_count += 1
            elif task_status == STATUS_DUPLICATE:
                self.duplicate_count += 1
            elif task_status == STATUS_FILTERED:
                self.filtered_count += 1
            else:
                self.failed_count += 1
            #await self._update_progress(task_status, STATUS_MOJO_MAP[task_status])
            self.semaphore.release()


    def _prepare_next_input(self):
        """Prepare input data for the next task"""
        # Implementation depends on specific use case
        pass

    def update_job_config(self, job_config: Dict[str, Any]):
        """Update job config by merging new values with existing config"""
        self.job_config = {**self.job_config, **job_config}

    # async def _update_progress(self, counter_type: str, emoji: str):
    #     """Update counters without showing live progress"""
    #     if not self.show_progress:
    #         return
    #     # Update the internal counters
    #     async with self.progress_lock:
    #         self._counters[counter_type] = getattr(self, f"{counter_type}_count")
