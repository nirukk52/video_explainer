"""Core data models used across the application."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Type of source document."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    URL = "url"
    TEXT = "text"


class Section(BaseModel):
    """A section of the source document."""

    heading: str
    level: int = 1
    content: str
    code_blocks: list[str] = Field(default_factory=list)
    equations: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    """A parsed source document."""

    title: str
    source_type: SourceType
    source_path: str
    sections: list[Section]
    raw_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Concept(BaseModel):
    """A key concept extracted from the document."""

    name: str
    explanation: str
    complexity: int = Field(ge=1, le=10)
    prerequisites: list[str] = Field(default_factory=list)
    analogies: list[str] = Field(default_factory=list)
    visual_potential: str = "medium"  # high, medium, low


class ContentAnalysis(BaseModel):
    """Analysis of the document content."""

    core_thesis: str
    key_concepts: list[Concept]
    target_audience: str
    suggested_duration_seconds: int
    complexity_score: int = Field(ge=1, le=10)


class VisualCue(BaseModel):
    """A visual cue annotation in the script."""

    description: str
    visual_type: str  # animation, diagram, code, equation, image
    elements: list[str] = Field(default_factory=list)
    duration_seconds: float = 5.0


class ScriptScene(BaseModel):
    """A scene in the video script."""

    scene_id: str  # Slug-based ID like "the_impossible_leap"
    scene_type: str  # hook, context, explanation, insight, conclusion
    title: str
    voiceover: str
    visual_cue: VisualCue
    duration_seconds: float
    notes: str = ""


class Script(BaseModel):
    """The complete video script."""

    title: str
    total_duration_seconds: float
    scenes: list[ScriptScene]
    source_document: str


class AnimationElement(BaseModel):
    """An element in an animation."""

    id: str
    element_type: str  # shape, text, code, equation, image
    properties: dict[str, Any] = Field(default_factory=dict)
    appear_at: float = 0.0
    animation: str = "fade_in"


class StoryboardScene(BaseModel):
    """A scene in the storyboard with detailed visual specs."""

    scene_id: str  # Slug-based ID like "the_impossible_leap"
    timestamp_start: float
    timestamp_end: float
    voiceover_text: str
    visual_type: str
    visual_description: str
    elements: list[AnimationElement] = Field(default_factory=list)
    transitions: dict[str, str] = Field(default_factory=dict)
    audio_path: str | None = None


class Storyboard(BaseModel):
    """The complete storyboard."""

    title: str
    scenes: list[StoryboardScene]
    style_guide: dict[str, Any] = Field(default_factory=dict)
    total_duration_seconds: float


class GeneratedAssets(BaseModel):
    """Generated assets for a video."""

    audio_paths: dict[str, str] = Field(default_factory=dict)  # scene_id -> path
    animation_paths: dict[str, str] = Field(default_factory=dict)
    image_paths: dict[str, str] = Field(default_factory=dict)


class VideoProject(BaseModel):
    """Complete video project state."""

    project_id: str
    source_path: str
    parsed_document: ParsedDocument | None = None
    content_analysis: ContentAnalysis | None = None
    script: Script | None = None
    storyboard: Storyboard | None = None
    assets: GeneratedAssets = Field(default_factory=GeneratedAssets)
    output_path: str | None = None
    status: str = "initialized"  # initialized, parsed, analyzed, scripted, storyboarded, rendered


class PlannedScene(BaseModel):
    """A planned scene in the video plan."""

    scene_number: int
    scene_type: str  # hook, context, explanation, insight, conclusion
    title: str
    concept_to_cover: str
    visual_approach: str
    ascii_visual: str  # ASCII art representation of the scene layout
    estimated_duration_seconds: float
    key_points: list[str] = Field(default_factory=list)


class VideoPlan(BaseModel):
    """A video plan for user review and approval before script generation."""

    status: str = "draft"  # draft, approved
    created_at: str
    approved_at: str | None = None

    title: str
    central_question: str
    target_audience: str
    estimated_total_duration_seconds: float

    core_thesis: str
    key_concepts: list[str]
    complexity_score: int = Field(ge=1, le=10)

    scenes: list[PlannedScene]
    visual_style: str

    source_document: str
    user_notes: str = ""
