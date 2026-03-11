import os
import sys
from pathlib import Path

# --- Record Status ---
RECORD_STATUS = "status"
STATUS_COMPLETED = "completed"
STATUS_DUPLICATE = "duplicate"
STATUS_FILTERED = "filtered"
STATUS_FAILED = "failed"

# --- Run Modes ---
RUN_MODE_NORMAL = "normal"
RUN_MODE_DRY_RUN = "dry_run"
RUN_MODE_RESUME = "resume_from_checkpoint"

# --- Storage Types ---
STORAGE_TYPE_LOCAL = "local"
STORAGE_TYPE_IN_MEMORY = "in_memory"

# --- Internal Keys ---
IDX = "idx_index"

# --- Defaults ---
DEFAULT_MAX_CONCURRENCY = 10
DEFAULT_BATCH_SIZE = 1
DEFAULT_TASK_TIMEOUT = 60
DEFAULT_DEAD_QUEUE_THRESHOLD = 3
DEFAULT_STOP_THRESHOLD = 3
DEFAULT_PROGRESS_INTERVAL = 3
DEFAULT_MAX_TASK_RETRIES = 1
DEFAULT_RATE_LIMIT = 0  # 0 = unlimited


def get_app_data_dir() -> str:
    r"""Platform-specific app data directory.

    - Linux: ~/.local/share/starfish
    - macOS: ~/Library/Application Support/starfish
    - Windows: %LOCALAPPDATA%\starfish

    Override via STARFISH_LOCAL_STORAGE_DIR env var.
    """
    env_dir = os.environ.get("STARFISH_LOCAL_STORAGE_DIR")
    if env_dir:
        return env_dir

    home = Path.home()
    if sys.platform == "win32":
        app_data = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        return os.path.join(app_data, "starfish")
    elif sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "starfish")
    else:
        xdg = os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        return os.path.join(xdg, "starfish")


APP_DATA_DIR = get_app_data_dir()
LOCAL_STORAGE_PATH = os.path.join(APP_DATA_DIR, "db")
LOCAL_STORAGE_URI = f"file://{LOCAL_STORAGE_PATH}"
