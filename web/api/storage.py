# Move storage-related functions here
from typing import Dict, Any
from starfish.data_factory.storage.models import Project
from starfish.data_factory.constants import (
    LOCAL_STORAGE_URI,
)
from starfish.data_factory.storage.local.local_storage import create_local_storage
from starfish.common.logger import get_logger

logger = get_logger(__name__)
# Create storage instance
storage = create_local_storage(LOCAL_STORAGE_URI)


async def setup_storage():
    """Setup storage - to be called during app startup"""
    await storage.setup()
    logger.info("Storage setup completed")


async def close_storage():
    """Close storage - to be called during app shutdown"""
    await storage.close()
    logger.info("Storage closed")


async def save_project(project: Project):
    # Implementation here
    await storage.save_project(project)


async def get_project(project_id: str):
    # Implementation here
    return await storage.get_project(project_id)


async def list_projects():
    # Implementation here
    return await storage.list_projects()


async def delete_project(project_id: str):
    # Implementation here
    await storage.delete_project(project_id)


async def save_dataset(project_name: str, dataset_name: str, dataset_data: Dict[str, Any]):
    # Implementation here
    await storage.save_dataset(project_name, dataset_name, dataset_data)


async def get_dataset(project_name: str, dataset_name: str):
    # Implementation here
    return await storage.get_dataset(project_name, dataset_name)


async def list_datasets(project_name: str):
    # Implementation here
    return await storage.list_datasets(project_name)


async def list_datasets_from_storage(project_id: str, dataset_type: str):
    # Implementation here
    if dataset_type == "factory":
        return []
    elif dataset_type == "template":
        return await storage.list_datasets(project_id)
    else:
        raise ValueError(f"Invalid dataset type: {dataset_type}")


async def get_dataset_from_storage(project_id: str, dataset_name: str):
    # Implementation here
    return await storage.get_dataset(project_id, dataset_name)
