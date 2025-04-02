import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from starfish.storage.base import Storage, register_storage
from starfish.storage.models import PrefixedFileStorageConfig, Project, JobMetadata, Record, RecordAssociation
from starfish.storage.filesystem import FileSystemStorage
from starfish.common.logger import get_logger

logger = get_logger(__name__)
logger.debug(f"🔍 MODULE LOADED: {__name__}")


class PrefixedFileStorage(FileSystemStorage):
    """
    File system storage with filename prefixing.
    
    This class extends FileSystemStorage to add configurable prefixes and
    suffixes to all filenames, which can be useful for organizing files
    when working with multiple storage instances.
    """
    
    def __init__(self, config: PrefixedFileStorageConfig):
        """
        Initialize prefixed filesystem storage.
        
        Args:
            config: Storage configuration with prefix/suffix options
        """
        super().__init__(config)
        self.prefix = config.prefix
        self.suffix = config.suffix
    
    # ==================================================================================
    # Override File Path Getters
    # ==================================================================================
    
    def _get_project_metadata_path(self, project_id: str) -> Path:
        """Get path for project metadata with prefix/suffix."""
        path = super()._get_project_metadata_path(project_id)
        return self._modify_path(path)
    
    def _get_job_metadata_path(self, job_id: str, project_id: Optional[str] = None) -> Path:
        """Get path for job metadata with prefix/suffix."""
        path = super()._get_job_metadata_path(job_id, project_id)
        return self._modify_path(path)
    
    def _get_records_path(self, job_id: str, project_id: Optional[str] = None) -> Path:
        """Get path for record data with prefix/suffix."""
        path = super()._get_records_path(job_id, project_id)
        return self._modify_path(path)
    
    def _get_associations_path(self, job_id: str, project_id: Optional[str] = None) -> Path:
        """Get path for associations with prefix/suffix."""
        path = super()._get_associations_path(job_id, project_id)
        return self._modify_path(path)
    
    def _modify_path(self, path: Path) -> Path:
        """Add prefix and suffix to a file path."""
        parent = path.parent
        name = path.name
        
        # Split filename and extension
        if '.' in name:
            base, ext = name.rsplit('.', 1)
            new_name = f"{self.prefix}{base}{self.suffix}.{ext}"
        else:
            new_name = f"{self.prefix}{name}{self.suffix}"
        
        return parent / new_name


@register_storage("prefixed_filesystem", input_model=PrefixedFileStorageConfig)
def create_prefixed_filesystem_storage(config: PrefixedFileStorageConfig) -> Storage:
    """Create a prefixed filesystem storage instance."""
    logger.debug(f"📁 STORAGE INITIALIZED: prefixed_filesystem")
    return PrefixedFileStorage(config=config)