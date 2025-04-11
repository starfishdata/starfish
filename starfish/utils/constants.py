import os
import shutil
from starfish.common.logger import get_logger
logger = get_logger(__name__)


RECORD_STATUS = "status"
TEST_DB_DIR = os.environ.get("STARFISH_TEST_DB_DIR", "/tmp/starfish_test_db")
TEST_DB_URI = f"file://{TEST_DB_DIR}"
if os.path.exists(TEST_DB_DIR):
    logger.info(f"Cleaning up existing test directory: {TEST_DB_DIR}")
    shutil.rmtree(TEST_DB_DIR)

STATUS_COMPLETED = "completed"
STATUS_DUPLICATE = "duplicate"
STATUS_FILTERED = "filtered"
STATUS_FAILED = "failed"

STATUS_MOJO_MAP = {
    STATUS_COMPLETED: "✅",
    STATUS_DUPLICATE: "🔁",
    STATUS_FILTERED: "🚫",
    STATUS_FAILED: "❌",
}