"""Video rendering router."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ..dependencies import RenderServiceDep, ProjectServiceDep
from ..models.requests import RenderRequest
from ..models.responses import JobStartedResponse

router = APIRouter(prefix="/projects/{project_id}/render", tags=["render"])


@router.get("", response_model=list[dict[str, Any]])
def list_renders(
    project_id: str,
    service: RenderServiceDep,
    project_service: ProjectServiceDep,
) -> list[dict[str, Any]]:
    """List rendered videos for a project."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    return service.list_renders(project_id)


@router.post("", response_model=JobStartedResponse, status_code=status.HTTP_202_ACCEPTED)
def start_render(
    project_id: str,
    request: RenderRequest,
    service: RenderServiceDep,
    project_service: ProjectServiceDep,
) -> JobStartedResponse:
    """Start video render job."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    try:
        job_id = service.start_render(
            project_id=project_id,
            resolution=request.resolution,
            preview=request.preview,
        )
        return JobStartedResponse(
            job_id=job_id,
            status="pending",
            message=f"Render started at {request.resolution}",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/video/{filename}")
def get_video(
    project_id: str,
    filename: str,
    service: RenderServiceDep,
) -> FileResponse:
    """Stream rendered video file."""
    video_path = service.get_video_path(project_id, filename)
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {filename}",
        )

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename,
    )
