import os
import sys
from pathlib import Path

RECORD_STATUS = "status"

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
RUN_MODE_RE_RUN = "resume_from_checkpoint"
RUN_MODE_DRY_RUN = "dry_run"

STORAGE_TYPE_LOCAL = "local"
STORAGE_TYPE_IN_MEMORY = "in_memory"

IDX = "idx_index"


# Define the function directly in constants to avoid circular imports
def get_app_data_dir():
    r"""Returns a platform-specific directory for application data storage.

    Following platform conventions:
    - Linux: ~/.local/share/starfish
    - macOS: ~/Library/Application Support/starfish
    - Windows: %LOCALAPPDATA%\starfish

    Environment variable STARFISH_LOCAL_STORAGE_DIR can override this location.
    """
    # Allow override through environment variable
    env_dir = os.environ.get("STARFISH_LOCAL_STORAGE_DIR")
    if env_dir:
        return env_dir

    app_name = "starfish"

    # Get user's home directory
    home = Path.home()

    # Platform-specific paths
    if sys.platform == "win32":
        # Windows: Use %LOCALAPPDATA% if available, otherwise construct from home
        app_data = os.environ.get("LOCALAPPDATA")
        if not app_data:
            app_data = os.path.join(home, "AppData", "Local")
        base_dir = os.path.join(app_data, app_name)
    elif sys.platform == "darwin":
        # macOS
        base_dir = os.path.join(home, "Library", "Application Support", app_name)
    else:
        # Linux/Unix: follow XDG Base Directory Specification
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if not xdg_data_home:
            xdg_data_home = os.path.join(home, ".local", "share")
        base_dir = os.path.join(xdg_data_home, app_name)

    return base_dir


# Get application database directory
APP_DATA_DIR = get_app_data_dir()
LOCAL_STORAGE_PATH = os.path.join(APP_DATA_DIR, "db")
LOCAL_STORAGE_URI = f"file://{LOCAL_STORAGE_PATH}"
