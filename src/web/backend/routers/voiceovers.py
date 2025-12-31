"""Voiceover generation router."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ..dependencies import AudioServiceDep, ProjectServiceDep
from ..models.requests import GenerateVoiceoversRequest
from ..models.responses import JobStartedResponse, VoiceoverFile

router = APIRouter(prefix="/projects/{project_id}/voiceovers", tags=["voiceovers"])


@router.get("", response_model=list[VoiceoverFile])
def list_voiceovers(
    project_id: str,
    service: AudioServiceDep,
    project_service: ProjectServiceDep,
) -> list[VoiceoverFile]:
    """List voiceover files for a project."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    voiceovers = service.list_voiceovers(project_id)
    return [
        VoiceoverFile(
            scene_id=vo["scene_id"],
            path=vo["path"],
            exists=vo["exists"],
            duration_seconds=vo.get("duration_seconds"),
        )
        for vo in voiceovers
    ]


@router.post("/generate", response_model=JobStartedResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_voiceovers(
    project_id: str,
    request: GenerateVoiceoversRequest,
    service: AudioServiceDep,
    project_service: ProjectServiceDep,
) -> JobStartedResponse:
    """Start voiceover generation job."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    try:
        job_id = service.generate_voiceovers(
            project_id=project_id,
            provider=request.provider,
            mock=request.mock,
        )
        return JobStartedResponse(
            job_id=job_id,
            status="pending",
            message="Voiceover generation started",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{scene_id}/audio")
def get_voiceover_audio(
    project_id: str,
    scene_id: str,
    service: AudioServiceDep,
) -> FileResponse:
    """Stream voiceover audio file."""
    audio_path = service.get_voiceover_path(project_id, scene_id)
    if not audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voiceover not found: {scene_id}",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"{scene_id}.mp3",
    )
