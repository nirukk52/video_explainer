"""Sound effects library router."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ..dependencies import SoundServiceDep, ProjectServiceDep
from ..models.responses import JobStartedResponse, SoundInfo

router = APIRouter(prefix="/projects/{project_id}/sound", tags=["sound"])


@router.get("", response_model=list[SoundInfo])
def list_sounds(
    project_id: str,
    service: SoundServiceDep,
    project_service: ProjectServiceDep,
) -> list[SoundInfo]:
    """List all sounds with their status."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    return service.list_sounds(project_id)


@router.post("/generate", response_model=JobStartedResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_sounds(
    project_id: str,
    service: SoundServiceDep,
    project_service: ProjectServiceDep,
) -> JobStartedResponse:
    """Generate all sound effects."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    job_id = service.generate_sounds(project_id)

    return JobStartedResponse(
        job_id=job_id,
        status="pending",
        message="Sound effect generation started",
    )


@router.get("/{sound_name}/audio")
def get_sound_audio(
    project_id: str,
    sound_name: str,
    service: SoundServiceDep,
) -> FileResponse:
    """Stream sound effect audio file."""
    sound_path = service.get_sound_path(project_id, sound_name)
    if not sound_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sound not found: {sound_name}",
        )

    return FileResponse(
        path=sound_path,
        media_type="audio/wav",
        filename=f"{sound_name}.wav",
    )
