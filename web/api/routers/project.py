from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from starfish.common.logger import get_logger
from starfish.data_factory.storage.models import Project
from web.api.storage import save_project, get_project, list_projects, delete_project

logger = get_logger(__name__)

router = APIRouter(prefix="/project", tags=["project"])


class ProjectCreateRequest(BaseModel):
    name: str
    template_name: str
    description: Optional[str] = None


@router.post("/create")
async def create_project(request: ProjectCreateRequest):
    """
    Create a new project.

    This endpoint creates a new project with the given details and saves it using Local Storage.

    Args:
        request: Project creation request containing name, description, and metadata

    Returns:
        The created project details
    """
    try:
        logger.info(f"Creating project: {request.name}")

        # Create project instance
        project = Project(
            project_id=request.name,
            name=request.name,
            template_name=request.template_name,
            description=request.description,
        )

        # Save project using local storage
        await save_project(project)

        logger.info(f"Project created successfully: {project.project_id}")
        return {"id": project.project_id, "name": project.name, "description": project.description, "created_at": project.created_when}

    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")


@router.get("/get")
async def get_project_endpoint(id: str):
    """
    Get a project by ID.

    Args:
        project_id: The ID of the project to retrieve

    Returns:
        The project details
    """
    try:
        project = await get_project(id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "id": project.project_id,
            "name": project.name,
            "template_name": project.template_name,
            "description": project.description,
            "created_at": project.created_when,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving project: {str(e)}")


@router.delete("/delete")
async def delete_project_endpoint(id: str):
    """
    Delete a project by ID.

    Args:
        id: The ID of the project to delete

    Returns:
        The deleted project details
    """
    try:
        await delete_project(id)
        return {"message": "Project deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")


@router.post("/list")
async def list_projects_endpoint(request: dict):
    """
    List all projects.

    Returns:
        List of all projects
    """
    try:
        projects = await list_projects()

        return [
            {
                "id": project.project_id,
                "name": project.name,
                "template_name": project.template_name,
                "description": project.description,
                "created_at": project.created_when,
            }
            for project in projects
        ]

    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing projects: {str(e)}")
