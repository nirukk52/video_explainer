"""Storyboard management router."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from ..dependencies import ProjectServiceDep

router = APIRouter(prefix="/projects/{project_id}/storyboard", tags=["storyboard"])


@router.get("", response_model=dict[str, Any])
def get_storyboard(
    project_id: str,
    service: ProjectServiceDep,
) -> dict[str, Any]:
    """Get the storyboard for a project."""
    try:
        return service.get_storyboard(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storyboard not found for project: {project_id}",
        )


@router.put("", response_model=dict[str, Any])
def update_storyboard(
    project_id: str,
    storyboard: dict[str, Any],
    service: ProjectServiceDep,
) -> dict[str, Any]:
    """Update the storyboard."""
    try:
        return service.update_storyboard(project_id, storyboard)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
