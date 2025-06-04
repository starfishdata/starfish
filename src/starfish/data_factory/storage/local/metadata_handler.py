# synthetic_data_gen/storage/local/metadata.py
import asyncio  # For Lock
from contextlib import nullcontext
import datetime
import json
import logging
import os
import random
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import sqlite3

from starfish.data_factory.constants import (
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
)
from starfish.data_factory.storage.local.setup import (
    initialize_db_schema,  # Import setup function
)
from starfish.data_factory.storage.models import (  # Import Pydantic models
    GenerationJob,
    GenerationMasterJob,
    Project,
    Record,
    StatusRecord,
)

logger = logging.getLogger(__name__)


# --- Helper Functions ---
def _serialize_pydantic_for_db(model_instance) -> Dict[str, Any]:
    """Serializes Pydantic model, converting dicts/enums to storable types."""
    data = model_instance.model_dump(mode="json")  # Use model_dump in Pydantic v2
    for key, value in data.items():
        # Example: Serialize specific fields known to be dicts/lists to JSON strings
        if key in ["output_schema", "run_config", "summary", "source_filter_criteria", "source_request_ids"]:  # Add more as needed
            if value is not None:
                data[key] = json.dumps(value)
        # Enums are likely already strings due to Literal, but ensure dates are handled if needed
        # (aiosqlite handles standard datetime objects well)
    return data


def _row_to_pydantic(model_class, row: Optional[aiosqlite.Row]):
    """Converts an aiosqlite.Row to a Pydantic model instance."""
    if row is None:
        return None
    # Pass dict(row) to model_validate for automatic parsing (incl. JSON strings via validator)
    return model_class.model_validate(dict(row))  # Pydantic v2


# --- Metadata Handler Class ---
class SQLiteMetadataHandler:
    """Manages interactions with the SQLite metadata database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._conn_lock = asyncio.Lock()  # Protects connection initialization
        self._write_lock = asyncio.Lock()  # Protects write operations to ensure single-writer access

    async def connect(self) -> aiosqlite.Connection:
        """Gets the connection, creating it and setting PRAGMAs if necessary."""
        # Use lock to prevent race conditions during initial connect/setup
        async with self._conn_lock:
            if self._conn is None or self._conn._conn is None:
                logger.debug(f"Connecting to SQLite DB: {self.db_path}")
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                    # Increase timeout to handle higher concurrency (60 seconds instead of 30)
                    self._conn = await aiosqlite.connect(self.db_path, timeout=60.0)
                    self._conn.row_factory = aiosqlite.Row
                    # Set PRAGMAs every time connection is potentially new
                    await self._conn.execute("PRAGMA journal_mode=WAL;")
                    await self._conn.execute("PRAGMA synchronous=NORMAL;")
                    await self._conn.execute("PRAGMA foreign_keys=ON;")
                    await self._conn.execute("PRAGMA cache_size=-2000;")  # Increase cache size (2MB)
                    # Set a longer busy timeout (60 seconds instead of 30)
                    await self._conn.execute("PRAGMA busy_timeout=60000;")
                    await self._conn.commit()
                    logger.info(f"SQLite connection established/verified: {self.db_path}")
                except Exception as e:
                    logger.error(f"Failed to connect/setup SQLite DB: {e}", exc_info=True)
                    raise e
            return self._conn

    async def close(self):
        """Closes the connection if open."""
        async with self._conn_lock:  # Ensure no operations happen during close
            if self._conn:
                await self._conn.close()
                self._conn = None
                logger.info("SQLite connection closed.")

    async def initialize_schema(self):
        """Initializes the database schema using definitions from schema.py."""
        conn = await self.connect()  # Ensure connection exists
        await initialize_db_schema(conn)  # Call the setup function

    async def _execute_sql(self, sql: str, params: tuple = ()):
        """Helper to execute write SQL with transactions."""
        async with self._write_lock:
            conn = await self.connect()
            max_retries = 5  # Increased from 3
            base_retry_delay = 0.1  # Start with shorter delay
            jitter = 0.05  # Add jitter to avoid thundering herd

            for attempt in range(max_retries):
                try:
                    # Only start a new transaction if one isn't already active
                    if not conn.in_transaction:
                        await conn.execute("BEGIN IMMEDIATE")

                    await conn.execute(sql, params)
                    await conn.commit()
                    logger.debug(f"Executed write SQL: {sql[:50]}... Params: {params}")
                    break  # Success, exit retry loop
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = base_retry_delay * (2**attempt) + (jitter * (1 - 2 * random.random()))
                        logger.warning(f"Database locked, retrying in {delay:.2f}s ({attempt + 1}/{max_retries})...")
                        await asyncio.sleep(delay)
                        continue
                    elif "cannot start a transaction within a transaction" in str(e):
                        logger.warning(f"Transaction already active, continuing: {e}")
                        break
                    else:
                        try:
                            await conn.rollback()
                        except Exception:
                            pass
                        logger.error(f"SQL write execution failed: {sql[:50]}... Error: {e}", exc_info=True)
                        raise e
                except Exception as e:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                    logger.error(f"SQL write execution failed: {sql[:50]}... Error: {e}", exc_info=True)
                    raise e

    async def _execute_batch_sql(self, statements: List[Tuple[str, tuple]]):
        """Execute multiple SQL statements in a single transaction."""
        async with self._write_lock:
            conn = await self.connect()
            try:
                # Remove explicit BEGIN IMMEDIATE
                for sql, params in statements:
                    await conn.execute(sql, params)
                await conn.commit()
                logger.debug(f"Executed batch SQL: {len(statements)} statements")
            except Exception as e:
                try:
                    await conn.rollback()
                except Exception:
                    pass
                logger.error(f"Batch SQL execution failed: Error: {e}", exc_info=True)
                raise e

    async def _fetchone_sql(self, sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """Helper to fetch one row."""
        conn = await self.connect()
        try:
            async with conn.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                logger.debug(f"Executed fetchone SQL: {sql[:50]}... Params: {params}")
                return row
        except Exception as e:
            logger.error(f"SQL fetchone failed: {sql[:50]}... Error: {e}", exc_info=True)
            raise e

    async def _fetchall_sql(self, sql: str, params: tuple = ()) -> List[aiosqlite.Row]:
        """Helper to fetch all rows."""
        conn = await self.connect()
        try:
            async with conn.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                logger.debug(f"Executed fetchall SQL: {sql[:50]}... Params: {params}")
                return rows
        except Exception as e:
            logger.error(f"SQL fetchall failed: {sql[:50]}... Error: {e}", exc_info=True)
            raise e

    # --- Batch operation methods for improved performance ---

    async def batch_save_records(self, records: List[Record]):
        """Save multiple record metadata entries in a single transaction."""
        if not records:
            return

        statements = []
        for record in records:
            data_dict = _serialize_pydantic_for_db(record)
            cols = ", ".join(data_dict.keys())
            placeholders = ", ".join("?" * len(data_dict))
            sql = f"INSERT OR REPLACE INTO Records ({cols}) VALUES ({placeholders});"
            params = tuple(data_dict.values())
            statements.append((sql, params))

        await self._execute_batch_sql(statements)

    async def batch_save_execution_jobs(self, jobs: List[GenerationJob]):
        """Save multiple execution jobs in a single transaction."""
        if not jobs:
            return

        statements = []
        for job in jobs:
            data_dict = _serialize_pydantic_for_db(job)
            cols = ", ".join(data_dict.keys())
            placeholders = ", ".join("?" * len(data_dict))
            sql = f"INSERT OR REPLACE INTO GenerationJob ({cols}) VALUES ({placeholders});"
            params = tuple(data_dict.values())
            statements.append((sql, params))

        await self._execute_batch_sql(statements)

    # --- Public methods corresponding to Storage interface metadata ops ---

    async def save_project_impl(self, project_data: Project):
        sql = """
            INSERT OR REPLACE INTO Projects (project_id, name, template_name, description, created_when, updated_when)
            VALUES (?, ?, ?, ?, ?,?);
        """
        params = (
            project_data.project_id,
            project_data.name,
            project_data.template_name,
            project_data.description,
            project_data.created_when,
            project_data.updated_when,
        )
        await self._execute_sql(sql, params)

    async def get_project_impl(self, project_id: str) -> Optional[Project]:
        sql = "SELECT * FROM Projects WHERE project_id = ?"
        row = await self._fetchone_sql(sql, (project_id,))
        return _row_to_pydantic(Project, row)

    async def delete_project_impl(self, project_id: str) -> None:
        sql = "DELETE FROM Projects WHERE project_id = ?"
        await self._execute_sql(sql, (project_id,))

    async def list_projects_impl(self, limit: Optional[int], offset: Optional[int]) -> List[Project]:
        sql = "SELECT * FROM Projects ORDER BY name"
        params: List[Any] = []

        # SQLite requires LIMIT when using OFFSET
        if offset is not None:
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                # If no explicit limit but with offset, use a high limit
                sql += " LIMIT 1000 OFFSET ?"
                params.append(offset)
        elif limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = await self._fetchall_sql(sql, tuple(params))
        return [_row_to_pydantic(Project, row) for row in rows]

    async def list_projects_impl_data_template(self, limit: Optional[int], offset: Optional[int]) -> List[Project]:
        sql = "SELECT * FROM Projects WHERE template_name IS NOT NULL ORDER BY name"
        params: List[Any] = []

        # SQLite requires LIMIT when using OFFSET
        if offset is not None:
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                # If no explicit limit but with offset, use a high limit
                sql += " LIMIT 1000 OFFSET ?"
                params.append(offset)
        elif limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = await self._fetchall_sql(sql, tuple(params))
        return [_row_to_pydantic(Project, row) for row in rows]

    async def log_master_job_start_impl(self, job_data: GenerationMasterJob):
        data_dict = _serialize_pydantic_for_db(job_data)
        cols = ", ".join(data_dict.keys())
        placeholders = ", ".join("?" * len(data_dict))
        sql = f"INSERT INTO GenerationMasterJob ({cols}) VALUES ({placeholders});"
        params = tuple(data_dict.values())
        await self._execute_sql(sql, params)

    async def log_master_job_end_impl(
        self, master_job_id: str, final_status: str, summary: Optional[Dict[str, Any]], end_time: datetime.datetime, update_time: datetime.datetime
    ):
        summary_str = json.dumps(summary) if summary else None
        # Update status, end_time, update_time, summary, and final counts from summary
        sql = """
            UPDATE GenerationMasterJob
            SET status = ?, end_time = ?, last_update_time = ?, summary = ?,
                completed_record_count = ?, filtered_record_count = ?,
                duplicate_record_count = ?, failed_record_count = ?
            WHERE master_job_id = ?;
        """
        params = (
            final_status,
            end_time,
            update_time,
            summary_str,
            summary.get(STATUS_COMPLETED, 0) if summary else 0,
            summary.get(STATUS_FILTERED, 0) if summary else 0,
            summary.get(STATUS_DUPLICATE, 0) if summary else 0,
            summary.get(STATUS_FAILED, 0) if summary else 0,
            master_job_id,
        )
        await self._execute_sql(sql, params)

    async def update_master_job_status_impl(self, master_job_id: str, status: str, update_time: datetime.datetime):
        sql = "UPDATE GenerationMasterJob SET status = ?, last_update_time = ? WHERE master_job_id = ?"
        await self._execute_sql(sql, (status, update_time, master_job_id))

    async def get_master_job_impl(self, master_job_id: str) -> Optional[GenerationMasterJob]:
        sql = "SELECT * FROM GenerationMasterJob WHERE master_job_id = ?"
        row = await self._fetchone_sql(sql, (master_job_id,))
        return _row_to_pydantic(GenerationMasterJob, row)

    async def list_master_jobs_impl(
        self, project_id: Optional[str], status_filter: Optional[List[str]], limit: Optional[int], offset: Optional[int]
    ) -> List[GenerationMasterJob]:
        sql = "SELECT * FROM GenerationMasterJob"
        params = []
        conditions = []
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if status_filter:
            placeholders = ",".join("?" * len(status_filter))
            conditions.append(f"status IN ({placeholders})")
            params.extend(status_filter)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY creation_time DESC"  # Example ordering

        # SQLite requires LIMIT when using OFFSET
        if offset is not None:
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                # If no explicit limit but with offset, use a high limit
                sql += " LIMIT 1000 OFFSET ?"
                params.append(offset)
        elif limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = await self._fetchall_sql(sql, tuple(params))
        return [_row_to_pydantic(GenerationMasterJob, row) for row in rows]

    # --- Implement methods for ExecutionJob and Records similarly ---
    async def log_execution_job_start_impl(self, job_data: GenerationJob):
        data_dict = _serialize_pydantic_for_db(job_data)
        cols = ", ".join(data_dict.keys())
        placeholders = ", ".join("?" * len(data_dict))
        sql = f"INSERT OR REPLACE INTO GenerationJob ({cols}) VALUES ({placeholders});"
        params = tuple(data_dict.values())
        await self._execute_sql(sql, params)

    async def log_execution_job_end_impl(
        self,
        job_id: str,
        final_status: str,
        counts: Dict[str, int],
        end_time: datetime.datetime,
        update_time: datetime.datetime,
        error_message: Optional[str] = None,
    ):
        sql = """
            UPDATE GenerationJob
            SET status = ?, end_time = ?, last_update_time = ?, error_message = ?,
                completed_record_count = ?, filtered_record_count = ?,
                duplicate_record_count = ?, failed_record_count = ?
            WHERE job_id = ?;
        """
        params = (
            final_status,
            end_time,
            update_time,
            error_message,
            counts.get(STATUS_COMPLETED, 0),
            counts.get(STATUS_FILTERED, 0),
            counts.get(STATUS_DUPLICATE, 0),
            counts.get(STATUS_FAILED, 0),
            job_id,
        )
        await self._execute_sql(sql, params)

    async def get_execution_job_impl(self, job_id: str) -> Optional[GenerationJob]:
        sql = "SELECT * FROM GenerationJob WHERE job_id = ?"
        row = await self._fetchone_sql(sql, (job_id,))
        return _row_to_pydantic(GenerationJob, row)

    async def list_execution_jobs_by_master_id_and_config_hash_impl(self, master_job_id: str, config_hash: str, job_status: str) -> List[GenerationJob]:
        sql = "SELECT * FROM GenerationJob WHERE master_job_id = ? AND run_config_hash = ? AND status = ?"
        rows = await self._fetchall_sql(sql, (master_job_id, config_hash, job_status))
        return [_row_to_pydantic(GenerationJob, row) for row in rows] if rows else []

    async def list_execution_jobs_impl(
        self, master_job_id: str, status_filter: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[GenerationJob]:
        sql = "SELECT * FROM GenerationJob WHERE master_job_id = ?"
        params = [master_job_id]

        if status_filter:
            placeholders = ",".join("?" * len(status_filter))
            sql += f" AND status IN ({placeholders})"
            params.extend(status_filter)

        sql += " ORDER BY creation_time DESC"

        # SQLite requires LIMIT when using OFFSET
        if offset is not None:
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                # If no explicit limit but with offset, use a high limit
                sql += " LIMIT 1000 OFFSET ?"
                params.append(offset)
        elif limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = await self._fetchall_sql(sql, tuple(params))
        return [_row_to_pydantic(GenerationJob, row) for row in rows]

    async def log_record_metadata_impl(self, record_data: Record):
        data_dict = _serialize_pydantic_for_db(record_data)
        cols = ", ".join(data_dict.keys())
        placeholders = ", ".join("?" * len(data_dict))
        sql = f"INSERT OR REPLACE INTO Records ({cols}) VALUES ({placeholders});"
        params = tuple(data_dict.values())
        await self._execute_sql(sql, params)

    async def get_record_metadata_impl(self, record_uid: str) -> Optional[Record]:
        sql = "SELECT * FROM Records WHERE record_uid = ?"
        row = await self._fetchone_sql(sql, (record_uid,))
        return _row_to_pydantic(Record, row)

    async def list_record_metadata_impl(self, master_job_uuid: str, job_uuid: str) -> List[Record]:
        sql = "SELECT * FROM Records WHERE master_job_id = ? AND job_id = ?"
        rows = await self._fetchall_sql(sql, (master_job_uuid, job_uuid))
        return [_row_to_pydantic(Record, row) for row in rows]

    async def get_records_for_master_job_impl(
        self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Record]:
        sql = "SELECT * FROM Records WHERE master_job_id = ?"
        params = [master_job_id]

        if status_filter:
            placeholders = ",".join("?" * len(status_filter))
            sql += f" AND status IN ({placeholders})"
            params.extend(status_filter)

        sql += " ORDER BY start_time DESC"

        # SQLite requires LIMIT when using OFFSET
        if offset is not None:
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                # If no explicit limit but with offset, use a high limit
                sql += " LIMIT 1000 OFFSET ?"
                params.append(offset)
        elif limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = await self._fetchall_sql(sql, tuple(params))
        return [_row_to_pydantic(Record, row) for row in rows]

    async def count_records_for_master_job_impl(self, master_job_id: str, status_filter: Optional[List[StatusRecord]] = None) -> Dict[str, int]:
        status_clause = ""
        params = [master_job_id]

        if status_filter:
            placeholders = ",".join("?" * len(status_filter))
            status_clause = f" AND status IN ({placeholders})"
            params.extend(status_filter)

        sql = f"""
            SELECT status, COUNT(*) as count
            FROM Records
            WHERE master_job_id = ?{status_clause}
            GROUP BY status
        """

        rows = await self._fetchall_sql(sql, tuple(params))
        result = {}
        for row in rows:
            result[row["status"]] = row["count"]

        return result

    async def list_execution_jobs_by_master_id_and_config_hash_impl(self, master_job_id: str, config_hash: str, job_status: str) -> List[GenerationJob]:
        sql = "SELECT * FROM GenerationJob WHERE master_job_id = ? AND run_config_hash = ? AND status = ?"
        rows = await self._fetchall_sql(sql, (master_job_id, config_hash, job_status))
        return [_row_to_pydantic(GenerationJob, row) for row in rows] if rows else []

    async def list_record_metadata_impl(self, master_job_uuid: str, job_uuid: str) -> List[Record]:
        sql = "SELECT * FROM Records WHERE master_job_id = ? AND job_id = ?"
        rows = await self._fetchall_sql(sql, (master_job_uuid, job_uuid))
        return [_row_to_pydantic(Record, row) for row in rows]
