# synthetic_data_gen/storage/local/utils.py
import os

from starfish.common.logger import get_logger

logger = get_logger(__name__)


def parse_uri_to_path(uri: str) -> str:
    """Parses a file:// URI into an absolute local path."""
    if not uri or not uri.startswith("file://"):
        raise ValueError(f"Invalid or missing file URI scheme: {uri}")
    path = uri[len("file://") :]
    # Handle Windows paths like file:///C:/... -> C:/...
    if os.name == "nt" and path.startswith("/") and len(path) > 1 and path[1] == ":":
        path = path[1:]
    # Handle standard POSIX paths like file:///path/ -> /path
    elif os.name != "nt" and not path.startswith("/"):
        raise ValueError(f"Invalid POSIX file URI path (must start with /): {uri}")

    return os.path.abspath(path)


def get_nested_path(base_dir: str, uid: str, filename_suffix: str = ".json") -> str:
    """Calculates the nested path based on UID prefix."""
    if not uid or len(uid) < 4:
        # Fallback or raise error - using XX for now
        prefix1, prefix2 = "XX", "XX"
        logger.warning(f"Using fallback prefix for potentially invalid UID: {uid}")
    else:
        prefix1 = uid[:2]
        prefix2 = uid[2:4]
    return os.path.join(base_dir, prefix1, prefix2, f"{uid}{filename_suffix}")
