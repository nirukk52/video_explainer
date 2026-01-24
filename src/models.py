"""
Core data models used across the application.

Includes models for:
- Document parsing and content analysis
- Script generation (both long-form and short-form)
- Evidence investigation and capture (for Varun Mayya style shorts)
- Storyboard and animation
"""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# SOURCE DOCUMENT MODELS
# ============================================================================


class SourceType(str, Enum):
    """Type of source document."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    URL = "url"
    TEXT = "text"


# ============================================================================
# EVIDENCE MODELS (for short-form video production)
# ============================================================================


class Investigation(BaseModel):
    """
    Research results from the Investigator agent.

    Contains the verified primary source URL, fallback alternatives,
    and credibility assessment. Multiple URLs enable retry on capture failure.
    """

    status: Literal["found", "not_found", "error", "pending"] = "pending"
    verified_url: Optional[str] = None
    fallback_urls: list[str] = Field(default_factory=list)
    source_title: Optional[str] = None
    credibility_score: Optional[float] = None
    error_message: Optional[str] = None


class ScreenshotVariant(BaseModel):
    """Single screenshot variant with path and display title."""

    path: str = Field(description="File path to the screenshot image")
    title: str = Field(description="Human-readable title for display")


class ScreenshotBundle(BaseModel):
    """
    Bundle of 5 screenshot variants for a single evidence capture.

    Provides flexibility for video rendering - Editor can choose
    the most appropriate variant for each scene's visual needs.
    """

    element_padded: Optional[ScreenshotVariant] = Field(
        default=None,
        description="Element with 20px padding - borders visible"
    )
    element_tight: Optional[ScreenshotVariant] = Field(
        default=None,
        description="Element tight crop - no padding"
    )
    context: Optional[ScreenshotVariant] = Field(
        default=None,
        description="Parent container with padding"
    )
    viewport: Optional[ScreenshotVariant] = Field(
        default=None,
        description="Current viewport screenshot"
    )
    fullpage: Optional[ScreenshotVariant] = Field(
        default=None,
        description="Full page screenshot - ultimate fallback"
    )

    def get_best_path(self) -> Optional[str]:
        """Get the best available screenshot path."""
        if self.element_padded:
            return self.element_padded.path
        if self.context:
            return self.context.path
        if self.viewport:
            return self.viewport.path
        if self.fullpage:
            return self.fullpage.path
        return None

    def get_all_with_titles(self) -> list[ScreenshotVariant]:
        """Return all available screenshots as a list."""
        variants = []
        if self.element_padded:
            variants.append(self.element_padded)
        if self.element_tight:
            variants.append(self.element_tight)
        if self.context:
            variants.append(self.context)
        if self.viewport:
            variants.append(self.viewport)
        if self.fullpage:
            variants.append(self.fullpage)
        return variants


class EvidenceCapture(BaseModel):
    """
    Visual evidence captured by the Witness agent.

    Contains all metadata needed to use the asset in video rendering:
    multiple screenshot variants, selectors, dimensions, and capture status.
    """

    capture_status: Literal["success", "partial", "failed", "pending"] = "pending"
    asset_type: Literal["screenshot", "recording", "dom_crop"] = "screenshot"

    # Element identification
    css_selector: Optional[str] = Field(
        default=None,
        description="CSS selector used to find the element"
    )
    identifying_text: Optional[str] = Field(
        default=None,
        description="Anchor text that matched the element"
    )

    # Screenshot variants
    screenshots: Optional[ScreenshotBundle] = Field(
        default=None,
        description="Bundle of screenshot variants"
    )

    # Best available screenshot (for backward compatibility)
    screenshot_url: Optional[str] = Field(
        default=None,
        description="Recommended screenshot path"
    )

    # Recording for scroll animations
    recording_url: Optional[str] = Field(
        default=None,
        description="Video recording URL for scroll_highlight"
    )

    # Dimensions
    width: Optional[int] = None
    height: Optional[int] = None

    # Error handling
    error_message: Optional[str] = None
    timing_ms: int = 0


# ============================================================================
# DOCUMENT PARSING MODELS
# ============================================================================


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
    scene_type: str  # hook, context, explanation, insight, conclusion (or role for shorts)
    title: str
    voiceover: str
    visual_cue: VisualCue
    duration_seconds: float
    notes: str = ""

    # Evidence fields (for short-form video production)
    needs_evidence: bool = False
    investigation: Optional[Investigation] = None
    evidence_capture: Optional[EvidenceCapture] = None


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


class ShortsProject(BaseModel):
    """
    Project state for short-form video production (Varun Mayya style).

    Tracks the evidence-based video production pipeline:
    1. Script generation (with evidence requirements)
    2. URL investigation (Exa.ai search)
    3. Screenshot capture (Browserbase)
    4. Asset packaging (Editor)
    5. Remotion rendering
    """

    project_id: str
    topic: str
    style: str = "varun_mayya"  # varun_mayya, johnny_harris, generic
    duration_seconds: int = 45

    # Pipeline state
    status: Literal[
        "initialized",
        "scripted",
        "investigating",
        "capturing",
        "editing",
        "rendering",
        "complete",
        "error"
    ] = "initialized"
    current_stage: str = "init"
    error_message: Optional[str] = None

    # Core data
    script: Optional[Script] = None
    evidence_urls: list[str] = Field(default_factory=list)

    # Output
    render_manifest: Optional[dict[str, Any]] = None
    output_path: Optional[str] = None

    # Metadata
    resolution: str = "1080x1920"  # 9:16 vertical for shorts
    tone: str = "investigative_journalist"
