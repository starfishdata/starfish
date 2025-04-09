import os
import shutil
RECORD_STATUS = "status"
TEST_DB_DIR = os.environ.get("STARFISH_TEST_DB_DIR", "/tmp/starfish_test_db")
TEST_DB_URI = f"file://{TEST_DB_DIR}"
# if os.path.exists(TEST_DB_DIR):
#     print(f"Cleaning up existing test directory: {TEST_DB_DIR}")
#     shutil.rmtree(TEST_DB_DIR)