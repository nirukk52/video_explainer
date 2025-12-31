"""Pydantic request models for API endpoints."""

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        min_length=1,
        max_length=50,
        description="Project ID (lowercase alphanumeric with hyphens)",
    )
    title: str = Field(..., min_length=1, max_length=200, description="Project title")
    description: str = Field(default="", description="Project description")


class UpdateNarrationRequest(BaseModel):
    """Request to update a narration."""

    narration: str = Field(..., min_length=1, description="Narration text")
    title: str | None = Field(default=None, description="Optional new title")
    duration_seconds: int | None = Field(default=None, description="Optional duration override")


class AddNarrationRequest(BaseModel):
    """Request to add a new narration."""

    scene_id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        description="Scene ID (lowercase alphanumeric with underscores)",
    )
    title: str = Field(..., min_length=1, description="Scene title")
    narration: str = Field(..., min_length=1, description="Narration text")
    duration_seconds: int = Field(default=15, ge=1, le=300, description="Duration in seconds")


class GenerateVoiceoversRequest(BaseModel):
    """Request to generate voiceovers."""

    provider: str = Field(default="edge", description="TTS provider (edge, elevenlabs, mock)")
    mock: bool = Field(default=False, description="Use mock provider for testing")


class RenderRequest(BaseModel):
    """Request to render a video."""

    resolution: str = Field(default="1080p", description="Output resolution")
    preview: bool = Field(default=False, description="Quick preview render")


class AddFeedbackRequest(BaseModel):
    """Request to add and process feedback."""

    feedback_text: str = Field(..., min_length=1, description="Feedback text")
    dry_run: bool = Field(default=False, description="Analyze without applying changes")
