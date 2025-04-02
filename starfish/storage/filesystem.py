import os
import json
import csv
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import uuid
from datetime import datetime

from starfish.storage.base import Storage, register_storage
from starfish.storage.models import (
    FileSystemStorageConfig, Project, JobMetadata, Record, RecordAssociation,
    StorageCapabilities
)
from starfish.common.logger import get_logger

logger = get_logger(__name__)
logger.debug(f"🔍 MODULE LOADED: {__name__}")


class FileSystemStorage(Storage):
    """
    File system storage implementation with project-based organization.
    
    This storage implementation:
    1. Organizes data by project_id and job_id in nested directory structure
    2. Stores projects, jobs, records, and associations as structured files
    3. Supports multiple data formats (JSON, JSONL, CSV)
    4. Provides consistent file naming conventions
    """
    
    capabilities = StorageCapabilities(
        supports_queries=False,
        supports_projects=True,
        supports_associations=True,
        supports_paging=True,
        max_batch_size=10000
    )
    
    def __init__(self, config: FileSystemStorageConfig):
        """
        Initialize file system storage with configuration.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.base_path = Path(config.base_path)
        self.data_format = config.data_format  # Always "jsonl" from config
        
        # Ensure base path exists
        os.makedirs(self.base_path, exist_ok=True)
    
    # ==================================================================================
    # Path Management
    # ==================================================================================
    
    def _get_project_path(self, project_id: str) -> Path:
        """
        Get the directory path for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Path for the project directory
        """
        # Always create project subfolder
        project_path = self.base_path / project_id
        os.makedirs(project_path, exist_ok=True)
        return project_path
    
    # ==================================================================================
    # Path Management - Helper Methods
    # ==================================================================================
    
    def _get_path_for_step_job_with_parent(self, job_id: str, project_path: Path, parent_job_id: str) -> Path:
        """
        Get path for a step job under a parent job.
        
        Args:
            job_id: Job identifier
            project_path: Path to the project directory
            parent_job_id: Parent job identifier
            
        Returns:
            Path for the step job directory
        """
        # Create parent job directory if it doesn't exist
        parent_job_path = project_path / parent_job_id
        os.makedirs(parent_job_path, exist_ok=True)
        
        # Create job directory under parent
        job_path = parent_job_path / job_id
        os.makedirs(job_path, exist_ok=True)
        return job_path
    
    def _get_path_for_master_job(self, job_id: str, project_path: Path) -> Path:
        """
        Get path for a master/parent job.
        
        Args:
            job_id: Job identifier
            project_path: Path to the project directory
            
        Returns:
            Path for the master job directory
        """
        job_path = project_path / job_id
        os.makedirs(job_path, exist_ok=True)
        return job_path
    
    def _search_for_existing_job(self, job_id: str) -> Optional[Path]:
        """
        Search for an existing job path in all projects.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path to the job directory if found, None otherwise
        """
        # Try to find which project this job belongs to
        for project_dir in self.base_path.glob("*/"):
            # Look for this job under any parent job directory
            for parent_dir in project_dir.glob("*/"):
                potential_job_path = parent_dir / job_id
                if potential_job_path.exists():
                    return potential_job_path
                
                # Check if metadata exists
                metadata_path = parent_dir / job_id / f"metadata_{job_id}.json"
                if metadata_path.exists():
                    return parent_dir / job_id
            
            # If not found as a child job, check if it's a parent/master job
            potential_job_path = project_dir / job_id
            if potential_job_path.exists():
                return potential_job_path
            
            # Check if metadata exists directly under project
            metadata_path = project_dir / job_id / f"metadata_{job_id}.json"
            if metadata_path.exists():
                return project_dir / job_id
        
        return None
    
    def _create_path_in_default_project(self, job_id: str) -> Path:
        """
        Create a path in a default project for an orphaned job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path for the job directory
        """
        # Create a default project
        default_project_id = f"auto_project_{uuid.uuid4().hex[:8]}"
        project_path = self._get_project_path(default_project_id)
        
        # Create a default project if it doesn't exist
        if not self.load_project(default_project_id):
            project = Project(
                project_id=default_project_id,
                name="Auto-created Project",
                description="Project automatically created for orphaned jobs",
                created_by="system"
            )
            self.save_project(project)
        
        # For master/parent jobs, create directly under project
        if not job_id.startswith("job_"):
            job_path = project_path / job_id
            os.makedirs(job_path, exist_ok=True)
            return job_path
        
        # For step jobs, look for a master job to place it under
        # or create a placeholder master job
        master_jobs = list(project_path.glob("master_*"))
        if master_jobs:
            # Use the first available master job
            master_job_path = master_jobs[0]
            job_path = master_job_path / job_id
        else:
            # Create a placeholder master job
            placeholder_master = f"master_placeholder_{uuid.uuid4().hex[:8]}"
            master_job_path = project_path / placeholder_master
            os.makedirs(master_job_path, exist_ok=True)
            job_path = master_job_path / job_id
            
        os.makedirs(job_path, exist_ok=True)
        return job_path
    
    def _get_job_path(self, job_id: str, project_id: Optional[str] = None, parent_job_id: Optional[str] = None) -> Path:
        """
        Get the directory path for a job.
        
        Args:
            job_id: Job identifier
            project_id: Optional project identifier
            parent_job_id: Optional parent job identifier (for nested job structure)
            
        Returns:
            Path for the job directory
        """
        # Case 1: Both project_id and parent_job_id are provided
        if project_id and parent_job_id:
            project_path = self._get_project_path(project_id)
            return self._get_path_for_step_job_with_parent(job_id, project_path, parent_job_id)
        
        # Case 2: Only project_id is provided
        elif project_id:
            project_path = self._get_project_path(project_id)
            
            # Only create job directly under project if it's a master/parent job
            if not job_id.startswith("job_"):  # Master/parent jobs don't start with "job_"
                return self._get_path_for_master_job(job_id, project_path)
            else:
                # This is a step job but no parent_job_id was provided
                # Search for an existing location in this project
                for potential_parent in project_path.glob("*/"):
                    potential_path = potential_parent / job_id
                    if potential_path.exists():
                        return potential_path
                
                # If not found, just return the path (don't create directories yet)
                # This will be handled by save_job_metadata
                logger.warning(f"Step job {job_id} has no parent_job_id specified")
                return project_path / job_id
        
        # Case 3: Neither project_id nor parent_job_id is provided
        else:
            # Try to find an existing job path
            existing_path = self._search_for_existing_job(job_id)
            if existing_path:
                return existing_path
            
            # Create in default project if not found
            logger.warning(f"Job {job_id} not found in any project. Creating in a default project.")
            return self._create_path_in_default_project(job_id)
    
    # ==================================================================================
    # File Path Getters
    # ==================================================================================
    
    def _get_project_metadata_path(self, project_id: str) -> Path:
        """Get path for project metadata."""
        # Store project JSON inside the project folder
        return self._get_project_path(project_id) / f"project_{project_id}.json"
    
    def _get_job_metadata_path(self, job_id: str, project_id: Optional[str] = None, parent_job_id: Optional[str] = None) -> Path:
        """Get path for job metadata."""
        return self._get_job_path(job_id, project_id, parent_job_id) / f"metadata_{job_id}.json"
    
    def _get_records_path(self, job_id: str, project_id: Optional[str] = None, parent_job_id: Optional[str] = None) -> Path:
        """Get path for job records."""
        ext = self._get_file_extension()
        return self._get_job_path(job_id, project_id, parent_job_id) / f"data_{job_id}.{ext}"
    
    def _get_associations_path(self, job_id: str, project_id: Optional[str] = None, parent_job_id: Optional[str] = None) -> Path:
        """Get path for record associations."""
        return self._get_job_path(job_id, project_id, parent_job_id) / f"associations_{job_id}.jsonl"
    
    # ==================================================================================
    # Project Operations
    # ==================================================================================
    
    def save_project(self, project: Project) -> Dict[str, Any]:
        """Save a project."""
        path = self._get_project_metadata_path(project.project_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(project.model_dump_json(indent=2))
        
        logger.info(f"Saved project {project.project_id} to {path}")
        
        return {
            "project_id": project.project_id,
            "path": str(path)
        }
    
    def load_project(self, project_id: str, project_name: Optional[str] = None) -> Optional[Project]:
        """
        Load a project by ID and optionally verify name.
        
        Args:
            project_id: Project identifier
            project_name: Optional project name to verify
            
        Returns:
            Project if found and name matches (if provided), None otherwise
        """
        path = self._get_project_metadata_path(project_id)
        if not path.exists():
            logger.warning(f"Project file not found: {path}")
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                project = Project.model_validate_json(f.read())
                
                # If project_name provided, verify it matches
                if project_name and project.name != project_name:
                    logger.warning(f"Project {project_id} exists but name '{project.name}' doesn't match requested '{project_name}'")
                    return None
                    
                return project
        except Exception as e:
            logger.error(f"Error loading project from {path}: {e}")
            raise
    
    def list_projects(self, project_name: Optional[str] = None) -> List[Project]:
        """
        List all projects, optionally filtered by name.
        
        Args:
            project_name: Optional name to filter projects by
            
        Returns:
            List of matching projects
        """
        projects = []
        
        # Look for project files in either base dir or project subdirs
        project_patterns = [
            self.base_path.glob("project_*.json"),  # Direct project files
            self.base_path.glob("*/project_*.json")  # Project files in subdirectories
        ]
        
        for pattern in project_patterns:
            for path in pattern:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        project = Project.model_validate_json(f.read())
                        
                        # Filter by name if specified
                        if project_name and project.name != project_name:
                            continue
                            
                        projects.append(project)
                except Exception as e:
                    logger.warning(f"Error loading project from {path}: {e}")
        
        return projects
        
    def find_project_by_name(self, project_name: str) -> List[Project]:
        """
        Find projects matching a specific name.
        
        Args:
            project_name: Project name to search for
            
        Returns:
            List of matching projects (empty if none found)
        """
        return self.list_projects(project_name=project_name)
    
    def update_project(self, project: Project) -> Dict[str, Any]:
        """Update an existing project."""
        # Simply overwrites the existing project file
        return self.save_project(project)
    
    # ==================================================================================
    # Job Operations
    # ==================================================================================
    
    def save_job_metadata(self, metadata: JobMetadata) -> Dict[str, Any]:
        """
        Save job metadata, ensuring correct hierarchy.
        
        This method:
        1. Gets parent_job_id from metadata if available
        2. Ensures step jobs (starting with 'job_') are always placed under their parent
        3. Saves metadata in the correct location
        
        Args:
            metadata: Job metadata to save
            
        Returns:
            Result dictionary with job info
        """
        # Get parent_job_id from metadata if available
        parent_job_id = metadata.parent_job_id
        
        # Ensure step jobs are always placed under a parent
        job_id = metadata.job_id
        if job_id.startswith("job_") and not parent_job_id:
            logger.warning(f"Step job {job_id} has no parent_job_id. Jobs should be properly hierarchical.")
            
            # Try to find a master job in this project to use as parent
            if metadata.project_id:
                project_path = self._get_project_path(metadata.project_id)
                master_jobs = list(project_path.glob("master_*"))
                if master_jobs:
                    # Extract master job ID from path
                    parent_job_id = master_jobs[0].name
                    logger.info(f"Using {parent_job_id} as parent for orphaned step job {job_id}")
                    
                    # Update metadata with this parent
                    metadata.parent_job_id = parent_job_id
        
        # Get path for metadata file
        path = self._get_job_metadata_path(job_id, metadata.project_id, parent_job_id)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))
        
        logger.info(f"Saved job metadata {job_id} to {path}")
        
        return {
            "job_id": job_id,
            "project_id": metadata.project_id,
            "parent_job_id": parent_job_id,
            "path": str(path)
        }
    
    def load_job_metadata(self, job_id: str) -> Optional[JobMetadata]:
        """Load job metadata by ID."""
        # First try to find the job in any project
        for project in self.list_projects():
            # Try first without parent (might be a master job)
            path = self._get_job_metadata_path(job_id, project.project_id)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return JobMetadata.model_validate_json(f.read())
                except Exception as e:
                    logger.warning(f"Error loading job metadata from {path}: {e}")
            
            # If not found, check under all possible parent jobs
            # Look for all job folders in this project (potential parent jobs)
            project_path = self._get_project_path(project.project_id)
            for parent_dir in project_path.glob("*/"):
                # Skip non-directories and non-job directories
                if not parent_dir.is_dir():
                    continue
                
                # Check if this job exists under this parent
                child_path = self._get_job_metadata_path(job_id, project.project_id, parent_dir.name)
                if child_path.exists():
                    try:
                        with open(child_path, "r", encoding="utf-8") as f:
                            return JobMetadata.model_validate_json(f.read())
                    except Exception as e:
                        logger.warning(f"Error loading job metadata from {child_path}: {e}")
        
        # Fallback to searching without project
        path = self._get_job_metadata_path(job_id)
        if not path.exists():
            logger.warning(f"Job metadata file not found: {path}")
            
            # Try searching in all possible job subdirectories
            job_paths = []
            # Look for job under parent job folders (three levels: project/parent/job)
            job_paths.extend(self.base_path.glob(f"*/*/*/metadata_{job_id}.json"))
            # Look for job directly under project (two levels: project/job)
            job_paths.extend(self.base_path.glob(f"*/*/metadata_{job_id}.json"))
            
            if job_paths:
                # Use the first match found
                path = job_paths[0]
                logger.info(f"Found job metadata at alternative path: {path}")
            else:
                return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return JobMetadata.model_validate_json(f.read())
        except Exception as e:
            logger.error(f"Error loading job metadata from {path}: {e}")
            raise
    
    def list_jobs(self, project_id: Optional[str] = None, job_type: Optional[str] = None, 
                  parent_job_id: Optional[str] = None) -> List[JobMetadata]:
        """List all jobs, optionally filtered by project, type, and parent."""
        jobs = []
        
        if project_id:
            # Get project path
            project_path = self._get_project_path(project_id)
            if not project_path.exists():
                logger.warning(f"Project directory not found: {project_path}")
                return []
            
            if parent_job_id:
                # Look for job metadata files under the specific parent job
                parent_path = project_path / parent_job_id
                if parent_path.exists():
                    metadata_pattern = parent_path.glob("*/metadata_*.json")
                else:
                    logger.warning(f"Parent job directory not found: {parent_path}")
                    return []
            else:
                # Look for all job metadata files, both direct children and under parent jobs
                metadata_pattern = []
                # Look for jobs directly under project (master jobs)
                metadata_pattern.extend(project_path.glob("*/metadata_*.json"))
                # Look for jobs under parent jobs (step jobs)
                metadata_pattern.extend(project_path.glob("*/*/metadata_*.json"))
        else:
            # Look in all projects
            metadata_pattern = []
            # Look for jobs directly under projects (master jobs)
            metadata_pattern.extend(self.base_path.glob("*/*/metadata_*.json"))
            # Look for jobs under parent jobs (step jobs)
            metadata_pattern.extend(self.base_path.glob("*/*/*/metadata_*.json"))
        
        # Process all matching files
        for path in metadata_pattern:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    job = JobMetadata.model_validate_json(f.read())
                    
                    # Filter by job_type if specified
                    if job_type and job.job_type != job_type:
                        continue
                    
                    # Filter by project_id if specified
                    if project_id and job.project_id != project_id:
                        continue
                    
                    # Filter by parent_job_id if specified
                    if parent_job_id and job.parent_job_id != parent_job_id:
                        continue
                    
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Error loading job metadata from {path}: {e}")
        
        return jobs
    
    def update_job_metadata(self, metadata: JobMetadata) -> Dict[str, Any]:
        """Update job metadata."""
        # Simply overwrites the existing job metadata file
        return self.save_job_metadata(metadata)
    
    # ==================================================================================
    # Record Operations
    # ==================================================================================
    
    def save_records(self, records: List[Record], job_id: str) -> Dict[str, Any]:
        """Save records for a job."""
        # Get project_id from the first record or fallback to None
        project_id = None
        parent_job_id = None
        
        # Try to find job metadata to get the project_id and parent_job_id
        job_metadata = self.load_job_metadata(job_id)
        if job_metadata:
            project_id = job_metadata.project_id
            parent_job_id = job_metadata.parent_job_id
        
        # Get path for records file
        path = self._get_records_path(job_id, project_id, parent_job_id)
        
        # Ensure all records have the correct job_id
        for record in records:
            if record.job_id != job_id:
                record.job_id = job_id
        
        # Save records in the specified format
        num_records = len(records)
        
        if self.data_format == "json":
            self._save_json_records(records, path)
        elif self.data_format == "jsonl":
            self._save_jsonl_records(records, path)
        elif self.data_format == "csv":
            self._save_csv_records(records, path)
        else:
            raise ValueError(f"Unsupported data format: {self.data_format}")
        
        logger.info(f"Saved {num_records} records to {path}")
        
        return {
            "job_id": job_id,
            "project_id": project_id,
            "parent_job_id": parent_job_id,
            "filepath": str(path),
            "format": self.data_format,
            "record_count": num_records
        }
    
    def load_records(self, job_id: str) -> List[Record]:
        """Load all records for a job."""
        # First try to find the job metadata to get project_id and parent_job_id
        job_metadata = self.load_job_metadata(job_id)
        project_id = job_metadata.project_id if job_metadata else None
        parent_job_id = job_metadata.parent_job_id if job_metadata else None
        
        # Get path for records file
        path = self._get_records_path(job_id, project_id, parent_job_id)
        
        if not path.exists():
            logger.warning(f"Records file not found: {path}")
            return []
        
        try:
            if self.data_format == "json":
                return self._load_json_records(path)
            elif self.data_format == "jsonl":
                return self._load_jsonl_records(path)
            elif self.data_format == "csv":
                return self._load_csv_records(path)
            else:
                raise ValueError(f"Unsupported data format: {self.data_format}")
        except Exception as e:
            logger.error(f"Error loading records from {path}: {e}")
            raise
    
    def load_records_by_project(self, project_id: str, job_type: Optional[str] = None) -> List[Record]:
        """Load all records in a project, optionally filtered by job type."""
        # Get all jobs in the project
        jobs = self.list_jobs(project_id=project_id, job_type=job_type)
        
        # If no jobs found with proper metadata, try searching by directory structure
        if not jobs:
            project_path = self._get_project_path(project_id)
            if project_path.exists():
                # Look for record files directly
                record_paths = []
                
                # Look in both job directories and parent/child hierarchy
                record_patterns = [
                    f"*/data_*.{self._get_file_extension()}",  # Direct job directories
                    f"*/*/data_*.{self._get_file_extension()}"  # Nested job directories
                ]
                
                # Find all matching record files
                for pattern in record_patterns:
                    record_paths.extend(project_path.glob(pattern))
                
                # Get job IDs from record files
                job_ids = set()
                for path in record_paths:
                    # Extract job_id from filename (format: data_JOB_ID.ext)
                    filename = path.name
                    if filename.startswith("data_") and "." in filename:
                        job_id = filename[5:filename.rindex(".")]
                        job_ids.add(job_id)
                
                # Create records for each job
                all_records = []
                for job_id in job_ids:
                    try:
                        records = self.load_records(job_id)
                        all_records.extend(records)
                    except Exception as e:
                        logger.warning(f"Error loading records for job {job_id}: {e}")
                
                return all_records
        
        # Load records for each job
        all_records = []
        for job in jobs:
            records = self.load_records(job.job_id)
            all_records.extend(records)
        
        return all_records
    
    def load_record(self, record_id: str) -> Optional[Record]:
        """Load a single record by ID."""
        # For performance, we need a more direct way to find a record by ID
        # First, try to find it by searching in all projects and jobs
        
        # Search in all projects
        for project in self.list_projects():
            project_path = self._get_project_path(project.project_id)
            
            # Search patterns for record files - both direct and nested jobs
            record_patterns = [
                f"*/data_*.{self._get_file_extension()}", 
                f"*/*/data_*.{self._get_file_extension()}"
            ]
            
            # Try all patterns
            for pattern in record_patterns:
                for file_path in project_path.glob(pattern):
                    try:
                        # Determine the format from the file extension
                        if file_path.suffix == ".json":
                            records = self._load_json_records(str(file_path))
                        elif file_path.suffix == ".jsonl":
                            records = self._load_jsonl_records(str(file_path))
                        elif file_path.suffix == ".csv":
                            raise NotImplementedError("CSV support not yet implemented")
                        else:
                            logger.warning(f"Unsupported file format: {file_path}")
                            continue
                        
                        # Check if the record is in this file
                        for record in records:
                            if record.record_id == record_id:
                                return record
                    except Exception as e:
                        logger.warning(f"Error loading records from {file_path}: {e}")
        
        # If not found, return None
        return None
    
    # ==================================================================================
    # Association Operations
    # ==================================================================================
    
    def save_associations(self, associations: List[RecordAssociation], job_id: str) -> Dict[str, Any]:
        """Save associations for a job."""
        # Get project_id and parent_job_id from job metadata
        project_id = None
        parent_job_id = None
        
        # Try to find job metadata to get the project_id
        job_metadata = self.load_job_metadata(job_id)
        if job_metadata:
            project_id = job_metadata.project_id
            parent_job_id = job_metadata.parent_job_id
        
        # Get path for associations file
        path = self._get_associations_path(job_id, project_id, parent_job_id)
        
        # Ensure all associations have the correct job_id
        for association in associations:
            if association.job_id != job_id:
                association.job_id = job_id
        
        # Save associations as JSONL (one per line)
        with open(path, "w", encoding="utf-8") as f:
            for association in associations:
                f.write(association.model_dump_json() + "\n")
        
        logger.info(f"Saved {len(associations)} associations to {path}")
        
        return {
            "job_id": job_id,
            "project_id": project_id,
            "parent_job_id": parent_job_id,
            "filepath": str(path),
            "association_count": len(associations)
        }
    
    def load_associations(self, job_id: str) -> List[RecordAssociation]:
        """Load all associations for a job."""
        # First try to find the job metadata to get project_id
        job_metadata = self.load_job_metadata(job_id)
        project_id = job_metadata.project_id if job_metadata else None
        parent_job_id = job_metadata.parent_job_id if job_metadata else None
        
        # Get path for associations file
        path = self._get_associations_path(job_id, project_id, parent_job_id)
        
        if not path.exists():
            logger.warning(f"Associations file not found: {path}")
            return []
        
        associations = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        associations.append(RecordAssociation.model_validate_json(line))
        except Exception as e:
            logger.error(f"Error loading associations from {path}: {e}")
            raise
        
        return associations
    
    def find_associations(self, source_record_id: Optional[str] = None, 
                        target_record_id: Optional[str] = None,
                        association_type: Optional[str] = None) -> List[RecordAssociation]:
        """Find associations by source, target, or type."""
        all_associations = []
        
        # Find all association files in the storage directory
        association_patterns = [
            # Look for associations in the root directory
            self.base_path.glob("associations_*.jsonl"),
            # Look for associations in job subdirectories
            self.base_path.glob("*/associations_*.jsonl"),
            # Look for associations in project/job subdirectories
            self.base_path.glob("*/*/associations_*.jsonl"),
            # Look for associations in project/parent/job subdirectories
            self.base_path.glob("*/*/*/associations_*.jsonl")
        ]
        
        # Load associations from all matching files
        for pattern in association_patterns:
            for path in pattern:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                association = RecordAssociation.model_validate_json(line)
                                
                                # Pre-filter as we load to avoid loading everything into memory
                                if (source_record_id is None or association.source_record_id == source_record_id) and \
                                   (target_record_id is None or association.target_record_id == target_record_id) and \
                                   (association_type is None or association.association_type == association_type):
                                    all_associations.append(association)
                except Exception as e:
                    logger.warning(f"Error loading associations from {path}: {e}")
        
        # If we have a specific job_id from find_association parameters
        # we could optimize further by only looking in that job's directory
        
        return all_associations
    
    # ==================================================================================
    # Helper Methods for File Operations
    # ==================================================================================
    
    def _get_file_extension(self) -> str:
        """Get file extension based on data format."""
        if self.data_format == "csv":
            return "csv"
        return self.data_format  # json or jsonl
    
    def _save_json_records(self, records: List[Record], filepath: str) -> None:
        """Save records as a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            # Convert records to dictionaries
            records_data = [record.model_dump() for record in records]
            json.dump(records_data, f, indent=2)
    
    def _save_jsonl_records(self, records: List[Record], filepath: str) -> None:
        """Save records as a JSONL file (one JSON object per line)."""
        with open(filepath, "w", encoding="utf-8") as f:
            for record in records:
                f.write(record.model_dump_json() + "\n")
    
    def _load_json_records(self, filepath: str) -> List[Record]:
        """Load records from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            # Ensure we have a list
            if not isinstance(data, list):
                data = [data]
            
            return [Record.model_validate(item) for item in data]
    
    def _load_jsonl_records(self, filepath: str) -> List[Record]:
        """Load records from a JSONL file."""
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(Record.model_validate_json(line))
        return records


@register_storage("filesystem", input_model=FileSystemStorageConfig)
def create_filesystem_storage(config: FileSystemStorageConfig) -> Storage:
    """Create a filesystem storage instance."""
    logger.debug(f"📁 STORAGE INITIALIZED: filesystem")
    return FileSystemStorage(config=config)
