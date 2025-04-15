import os
from starfish.core.common.logger import get_logger
logger = get_logger(__name__)


RECORD_STATUS = "status"
TEST_DB_DIR = os.environ.get("STARFISH_TEST_DB_DIR", "/Users/john/Documents/projects/aa/python/starfish/starfish/db")
TEST_DB_URI = f"file://{TEST_DB_DIR}"
# if os.path.exists(TEST_DB_DIR):
#     logger.info(f"Cleaning up existing test directory: {TEST_DB_DIR}")
#     shutil.rmtree(TEST_DB_DIR)

STATUS_TOTAL = "total"
STATUS_COMPLETED = "completed"
STATUS_DUPLICATE = "duplicate"
STATUS_FILTERED = "filtered"
STATUS_FAILED = "failed"

STATUS_MOJO_MAP = {
    STATUS_COMPLETED: "✅",
    STATUS_DUPLICATE: "🔁",
    STATUS_FILTERED: "🚫",
    STATUS_FAILED: "❌",
    STATUS_TOTAL: "📊",
}
RUN_MODE = "run_mode"
RUN_MODE_NORMAL = "normal"
RUN_MODE_RE_RUN = "re_run"
RUN_MODE_DRY_RUN = "dry_run"

STORAGE_TYPE_LOCAL = "local"
STORAGE_TYPE_IN_MEMORY = "in_memory"

PROGRESS_LOG_INTERVAL = 3

TASK_RUNNER_TIMEOUT = 30
