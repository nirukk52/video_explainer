"""Narration management router."""

from fastapi import APIRouter, HTTPException, status

from ..dependencies import ProjectServiceDep
from ..models.requests import UpdateNarrationRequest, AddNarrationRequest
from ..models.responses import Narration

router = APIRouter(prefix="/projects/{project_id}/narrations", tags=["narrations"])


@router.get("", response_model=list[Narration])
def list_narrations(project_id: str, service: ProjectServiceDep) -> list[Narration]:
    """List all narrations for a project."""
    try:
        return service.get_narrations(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )


@router.post("", response_model=Narration, status_code=status.HTTP_201_CREATED)
def add_narration(
    project_id: str,
    request: AddNarrationRequest,
    service: ProjectServiceDep,
) -> Narration:
    """Add a new narration."""
    try:
        return service.add_narration(
            project_id=project_id,
            scene_id=request.scene_id,
            title=request.title,
            narration=request.narration,
            duration_seconds=request.duration_seconds,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{scene_id}", response_model=Narration)
def get_narration(
    project_id: str,
    scene_id: str,
    service: ProjectServiceDep,
) -> Narration:
    """Get a specific narration."""
    try:
        narrations = service.get_narrations(project_id)
        for narration in narrations:
            if narration.scene_id == scene_id:
                return narration
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene not found: {scene_id}",
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )


@router.put("/{scene_id}", response_model=Narration)
def update_narration(
    project_id: str,
    scene_id: str,
    request: UpdateNarrationRequest,
    service: ProjectServiceDep,
) -> Narration:
    """Update a narration."""
    try:
        return service.update_narration(
            project_id=project_id,
            scene_id=scene_id,
            narration=request.narration,
            title=request.title,
            duration_seconds=request.duration_seconds,
        )
    except FileNotFoundError as e:
        if "Scene not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene not found: {scene_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_narration(
    project_id: str,
    scene_id: str,
    service: ProjectServiceDep,
) -> None:
    """Delete a narration."""
    try:
        service.delete_narration(project_id, scene_id)
    except FileNotFoundError as e:
        if "Scene not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene not found: {scene_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
