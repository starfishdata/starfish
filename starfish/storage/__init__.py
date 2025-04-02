"""
Storage implementations for Starfish.

This module provides:
1. Base Storage interface and factory functions
2. Multiple storage backends (filesystem, database, S3)
3. Standardized metadata tracking for generated data
4. Project-based organization for related jobs and records
5. Association functionality for relationships between records
"""

from starfish.storage.base import (
    Storage, create_storage, get_available_storage_types, get_all_storage_input_models,
    RecordTypeRegistry, AssociationTypeRegistry
)

# Import data models for convenient access
from starfish.storage.models import (
    Project, JobMetadata, Record, RecordAssociation, 
    AssociationType, StorageCapabilities
)

# Import all storage implementations to register them
import starfish.storage.filesystem
import starfish.storage.prefixed_filesystem

# These will be added in future releases
# import starfish.core.storage.database
# import starfish.core.storage.s3

# Export the interfaces, models and factory functions
__all__ = [
    # Factory functions
    "Storage", 
    "create_storage",
    "get_available_storage_types",
    "get_all_storage_input_models",
    
    # Registries
    "RecordTypeRegistry",
    "AssociationTypeRegistry",
    
    # Data models
    "Project",
    "JobMetadata",
    "Record",
    "RecordAssociation",
    "AssociationType",
    "StorageCapabilities"
]

# Also expose BaseStorage for backward compatibility
from starfish.storage.base import BaseStorage
__all__.append("BaseStorage")