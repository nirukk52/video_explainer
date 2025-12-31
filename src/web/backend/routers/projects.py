"""Project CRUD router."""

from fastapi import APIRouter, HTTPException, status

from ..dependencies import ProjectServiceDep
from ..models.requests import CreateProjectRequest
from ..models.responses import ProjectSummary, ProjectDetail

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
def list_projects(service: ProjectServiceDep) -> list[ProjectSummary]:
    """List all projects with summary info."""
    return service.list_projects()


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    request: CreateProjectRequest,
    service: ProjectServiceDep,
) -> ProjectDetail:
    """Create a new project."""
    try:
        return service.create_project(
            project_id=request.id,
            title=request.title,
            description=request.description or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, service: ProjectServiceDep) -> ProjectDetail:
    """Get detailed project information."""
    try:
        return service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, service: ProjectServiceDep) -> None:
    """Delete a project."""
    try:
        service.delete_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
