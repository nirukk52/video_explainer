"""Dependency injection for FastAPI."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from .config import WebConfig
from .services.job_manager import JobManager
from .services.project_service import ProjectService
from .services.audio_service import AudioService
from .services.render_service import RenderService
from .services.feedback_service import FeedbackService
from .services.sound_service import SoundService
from .websocket.manager import WebSocketManager


@lru_cache
def get_config() -> WebConfig:
    """Get the web configuration (cached)."""
    return WebConfig()


@lru_cache
def get_websocket_manager() -> WebSocketManager:
    """Get the WebSocket manager (cached singleton)."""
    return WebSocketManager()


@lru_cache
def get_job_manager() -> JobManager:
    """Get the job manager (cached singleton)."""
    job_manager = JobManager()
    return job_manager


def get_projects_dir(config: Annotated[WebConfig, Depends(get_config)]) -> Path:
    """Get the projects directory from config."""
    return config.projects_dir


def get_project_service(
    projects_dir: Annotated[Path, Depends(get_projects_dir)],
) -> ProjectService:
    """Get the project service."""
    return ProjectService(projects_dir=projects_dir)


def get_audio_service(
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
    projects_dir: Annotated[Path, Depends(get_projects_dir)],
) -> AudioService:
    """Get the audio service."""
    return AudioService(job_manager=job_manager, projects_dir=projects_dir)


def get_render_service(
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
    projects_dir: Annotated[Path, Depends(get_projects_dir)],
) -> RenderService:
    """Get the render service."""
    return RenderService(job_manager=job_manager, projects_dir=projects_dir)


def get_feedback_service(
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
    projects_dir: Annotated[Path, Depends(get_projects_dir)],
) -> FeedbackService:
    """Get the feedback service."""
    return FeedbackService(job_manager=job_manager, projects_dir=projects_dir)


def get_sound_service(
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
    projects_dir: Annotated[Path, Depends(get_projects_dir)],
) -> SoundService:
    """Get the sound service."""
    return SoundService(job_manager=job_manager, projects_dir=projects_dir)


# Type aliases for cleaner router signatures
ConfigDep = Annotated[WebConfig, Depends(get_config)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
WebSocketManagerDep = Annotated[WebSocketManager, Depends(get_websocket_manager)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
AudioServiceDep = Annotated[AudioService, Depends(get_audio_service)]
RenderServiceDep = Annotated[RenderService, Depends(get_render_service)]
FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
SoundServiceDep = Annotated[SoundService, Depends(get_sound_service)]
