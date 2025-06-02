# synthetic_data_gen/storage/local/schema.py
import logging

import aiosqlite

logger = logging.getLogger(__name__)

# --- SQL Schema Definitions ---

CREATE_PROJECTS_SQL = """
CREATE TABLE IF NOT EXISTS Projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    template_name TEXT,
    description TEXT,
    created_when TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_when TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);"""

CREATE_MASTER_JOBS_SQL = """
CREATE TABLE IF NOT EXISTS GenerationMasterJob (
    master_job_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'generating', 'aggregating', 'completed', 'failed', 'completed_with_errors', 'cancelled')),
    request_config_ref TEXT NOT NULL,
    output_schema TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    metadata_storage_uri_override TEXT,
    data_storage_uri_override TEXT,
    target_record_count INTEGER NOT NULL,
    completed_record_count INTEGER NOT NULL DEFAULT 0,
    filtered_record_count INTEGER NOT NULL DEFAULT 0,
    duplicate_record_count INTEGER NOT NULL DEFAULT 0,
    failed_record_count INTEGER NOT NULL DEFAULT 0,
    creation_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    last_update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE SET NULL
);"""
# Add CHECK constraints text explicitly if desired

CREATE_EXECUTION_JOBS_SQL = """
CREATE TABLE IF NOT EXISTS GenerationJob (
    job_id TEXT PRIMARY KEY,
    master_job_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'duplicate', 'filtered', 'failed', 'cancelled')),
    run_config TEXT,
    run_config_hash TEXT NOT NULL,
    attempted_generations INTEGER NOT NULL DEFAULT 0,
    produced_outputs_count INTEGER NOT NULL DEFAULT 0,
    completed_record_count INTEGER NOT NULL DEFAULT 0,
    filtered_record_count INTEGER NOT NULL DEFAULT 0,
    duplicate_record_count INTEGER NOT NULL DEFAULT 0,
    failed_record_count INTEGER NOT NULL DEFAULT 0,
    creation_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    last_update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    worker_id TEXT,
    error_message TEXT,
    FOREIGN KEY (master_job_id) REFERENCES GenerationMasterJob(master_job_id) ON DELETE CASCADE
);"""
# Add CHECK constraints text explicitly if desired

CREATE_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS Records (
    record_uid TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    master_job_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'duplicate', 'filtered', 'failed', 'cancelled')),
    output_ref TEXT,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (job_id) REFERENCES GenerationJob(job_id) ON DELETE CASCADE,
    FOREIGN KEY (master_job_id) REFERENCES GenerationMasterJob(master_job_id) ON DELETE CASCADE
);"""
# Add CHECK constraints text explicitly if desired

# --- Indexes ---
# (Add CREATE INDEX IF NOT EXISTS statements for FKs and commonly queried fields)
CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_masterjobs_project_id ON GenerationMasterJob(project_id);
CREATE INDEX IF NOT EXISTS idx_masterjobs_status ON GenerationMasterJob(status);
CREATE INDEX IF NOT EXISTS idx_execjobs_master_id ON GenerationJob(master_job_id);
CREATE INDEX IF NOT EXISTS idx_execjobs_status ON GenerationJob(status);
CREATE INDEX IF NOT EXISTS idx_records_master_id ON Records(master_job_id);
CREATE INDEX IF NOT EXISTS idx_records_job_id ON Records(job_id);
CREATE INDEX IF NOT EXISTS idx_records_status ON Records(status);
"""


# --- Setup Function ---
async def initialize_db_schema(conn: aiosqlite.Connection):
    """Creates tables and indexes if they don't exist."""
    logger.info("Initializing SQLite database schema...")
    try:
        await conn.executescript(f"""
            {CREATE_PROJECTS_SQL}
            {CREATE_MASTER_JOBS_SQL}
            {CREATE_EXECUTION_JOBS_SQL}
            {CREATE_RECORDS_SQL}
            {CREATE_INDEXES_SQL}
        """)
        await conn.commit()
        logger.info("SQLite schema initialization complete.")
    except Exception as e:
        logger.error(f"Failed initializing SQLite schema: {e}", exc_info=True)
        # Attempt rollback? Connection might be closed by handler
        raise e from e
