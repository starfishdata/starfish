from starfish.common.logger import get_logger

logger = get_logger(__name__)

import json
import logging
import os
from typing import Any, Dict

# synthetic_data_gen/storage/local/data.py
import aiofiles
import aiofiles.os as aio_os

from .utils import get_nested_path

logger = logging.getLogger(__name__)

CONFIGS_DIR = "configs"
DATA_DIR = "data"
ASSOCIATIONS_DIR = "associations"
DATASETS_DIR = "datasets"


class FileSystemDataHandler:
    """Manages interactions with data/config files on the local filesystem."""

    def __init__(self, data_base_path: str):
        """Args:
        data_base_path: The root directory where configs/, data/, etc. will live.
        """
        self.data_base_path = data_base_path
        self.config_path = os.path.join(self.data_base_path, CONFIGS_DIR)
        self.record_data_path = os.path.join(self.data_base_path, DATA_DIR)
        self.assoc_path = os.path.join(self.data_base_path, ASSOCIATIONS_DIR)
        self.datasets_path = os.path.join(self.data_base_path, DATASETS_DIR)
        # TODO: Consider locks if implementing JSONL appends for associations

    async def ensure_base_dirs(self):
        """Ensure all top-level data directories exist."""
        logger.debug("Ensuring base data directories exist...")
        await self._ensure_dir(self.config_path + os.sep)  # Trailing sep ensures dir
        await self._ensure_dir(self.record_data_path + os.sep)
        # TODO: Add associations directory back later
        # await self._ensure_dir(self.assoc_path + os.sep)

    async def _ensure_dir(self, path: str):
        """Asynchronously ensures a directory exists."""
        dir_path = os.path.dirname(path)
        if not await aio_os.path.isdir(dir_path):
            try:
                await aio_os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")
            except Exception as e:
                if not await aio_os.path.isdir(dir_path):
                    logger.error(f"Failed creating directory {dir_path}: {e}", exc_info=True)
                    raise e

    async def _save_json_file(self, path: str, data: Dict[str, Any]):
        await self._ensure_dir(path)
        try:
            async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=2))  # Pretty print for readability
            logger.debug(f"Saved JSON to: {path}")
        except Exception as e:
            logger.error(f"Failed writing JSON to {path}: {e}", exc_info=True)
            raise e

    async def _read_json_file(self, path: str) -> Dict[str, Any]:
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                logger.debug(f"Read JSON from: {path}")
                return json.loads(content)
        except FileNotFoundError as e:
            logger.warning(f"File not found: {path}")
            raise e
        except Exception as e:
            logger.error(f"Failed reading JSON from {path}: {e}", exc_info=True)
            raise e

    # --- Public methods corresponding to Storage interface data ops ---

    async def save_request_config_impl(self, config_ref: str, config_data: Dict[str, Any]):
        await self._save_json_file(config_ref, config_data)

    def generate_request_config_path_impl(self, master_job_id: str) -> str:
        path = os.path.join(self.config_path, f"{master_job_id}.request.json")
        return path  # Return absolute path as the reference

    async def save_dataset_impl(self, project_id: str, dataset_name: str, dataset_data: Dict[str, Any]):
        path = os.path.join(self.datasets_path, project_id, f"{dataset_name}.json")
        await self._save_json_file(path, dataset_data)
        return path

    async def get_dataset_impl(self, project_id: str, dataset_name: str) -> Dict[str, Any]:
        path = os.path.join(self.datasets_path, project_id, f"{dataset_name}.json")
        return await self._read_json_file(path)

    async def list_datasets_impl(self, project_id: str) -> list[Dict[str, Any]]:
        path = os.path.join(self.datasets_path, project_id)
        files = await aio_os.listdir(path)
        datasets = []

        for i in range(len(files)):
            file = files[i]
            if file.endswith(".json"):
                dataset = await self._read_json_file(os.path.join(path, file))

                datasets.append(
                    {"id": i, "name": file[:-5], "created_at": file.split("__")[1][:-5], "record_count": len(dataset), "data": dataset, "status": "completed"}
                )
        return datasets

    async def get_request_config_impl(self, config_ref: str) -> Dict[str, Any]:
        return await self._read_json_file(config_ref)  # Assumes ref is absolute path

    async def save_record_data_impl(self, record_uid: str, data: Dict[str, Any]) -> str:
        path = get_nested_path(self.record_data_path, record_uid, ".json")
        await self._save_json_file(path, data)
        return path  # Return absolute path as the output_ref

    async def get_record_data_impl(self, output_ref: str) -> Dict[str, Any]:
        return await self._read_json_file(output_ref)  # Assumes ref is absolute path
