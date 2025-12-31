"""Pydantic models for API requests and responses."""

from .requests import (
    CreateProjectRequest,
    UpdateNarrationRequest,
    AddNarrationRequest,
    GenerateVoiceoversRequest,
    RenderRequest,
    AddFeedbackRequest,
)
from .responses import (
    ProjectSummary,
    ProjectDetail,
    FileStatus,
    VideoSettings,
    TTSSettings,
    StyleSettings,
    Narration,
    VoiceoverFile,
    JobResponse,
    FeedbackItemResponse,
    SoundInfo,
)

__all__ = [
    # Requests
    "CreateProjectRequest",
    "UpdateNarrationRequest",
    "AddNarrationRequest",
    "GenerateVoiceoversRequest",
    "RenderRequest",
    "AddFeedbackRequest",
    # Responses
    "ProjectSummary",
    "ProjectDetail",
    "FileStatus",
    "VideoSettings",
    "TTSSettings",
    "StyleSettings",
    "Narration",
    "VoiceoverFile",
    "JobResponse",
    "FeedbackItemResponse",
    "SoundInfo",
]
