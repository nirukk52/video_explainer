"""Pydantic response models for API endpoints."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class VideoSettings(BaseModel):
    """Video configuration settings."""

    width: int
    height: int
    fps: int
    target_duration_seconds: int


class TTSSettings(BaseModel):
    """TTS configuration settings."""

    provider: str
    voice_id: str


class StyleSettings(BaseModel):
    """Visual style settings."""

    background_color: str
    primary_color: str
    secondary_color: str
    font_family: str


class FileStatus(BaseModel):
    """Status of project files."""

    narrations_count: int = Field(description="Number of narration scenes")
    voiceover_count: int = Field(description="Number of voiceover files")
    has_storyboard: bool = Field(description="Whether storyboard exists")
    rendered_videos: list[str] = Field(description="List of rendered video filenames")
    has_sfx: bool = Field(description="Whether SFX library is generated")


class ProjectSummary(BaseModel):
    """Summary of a project for listing."""

    id: str
    title: str
    description: str
    has_narrations: bool
    has_voiceovers: bool
    has_storyboard: bool
    has_render: bool


class ProjectDetail(BaseModel):
    """Detailed project information."""

    id: str
    title: str
    description: str
    version: str
    video: VideoSettings
    tts: TTSSettings
    style: StyleSettings
    files: FileStatus


class Narration(BaseModel):
    """A single scene narration."""

    scene_id: str
    title: str
    duration_seconds: int
    narration: str


class VoiceoverFile(BaseModel):
    """Information about a voiceover file."""

    scene_id: str
    path: str
    exists: bool
    duration_seconds: float | None = None


class JobStartedResponse(BaseModel):
    """Response when a job is started."""

    job_id: str
    status: Literal["pending", "running"] = "pending"
    message: str


class JobResponse(BaseModel):
    """Full job status response."""

    job_id: str
    type: str
    project_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: float = Field(ge=0.0, le=1.0, description="Progress from 0.0 to 1.0")
    message: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class FeedbackItemResponse(BaseModel):
    """Response for a feedback item."""

    id: str
    feedback_text: str
    status: str
    scope: str | None
    affected_scenes: list[str]
    interpretation: str | None
    files_modified: list[str]
    error_message: str | None
    timestamp: datetime


class SoundInfo(BaseModel):
    """Information about a sound effect."""

    name: str
    description: str
    exists: bool
