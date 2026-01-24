"""
Pydantic models for Director MCP skills.

Defines input/output schemas for Varun Mayya-style short-form video planning.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VideoStyle(str, Enum):
    """Style presets for short-form video creation."""

    VARUN_MAYYA = "varun_mayya"  # Tech/AI, authority, proof-heavy
    JOHNNY_HARRIS = "johnny_harris"  # Explainer, visual essays
    GENERIC = "generic"  # Standard short-form


class VisualType(str, Enum):
    """Types of visual assets for scenes."""

    STATIC_HIGHLIGHT = "static_highlight"  # Screenshot with text highlight
    SCROLL_HIGHLIGHT = "scroll_highlight"  # Video of scrolling to content
    DOM_CROP = "dom_crop"  # Isolated element (chart, tweet)
    FULL_AVATAR = "full_avatar"  # Talking head, no evidence


class SceneRole(str, Enum):
    """Narrative role of each scene in the short."""

    HOOK = "hook"  # First 3 seconds, stop the scroll
    EVIDENCE = "evidence"  # Proof shot with visual
    ANALYSIS = "analysis"  # Avatar explaining implications
    CONCLUSION = "conclusion"  # CTA or final statement


class DropOffSeverity(str, Enum):
    """Severity of potential viewer drop-off."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- Input Models ---


class PlanShortInput(BaseModel):
    """Input for the plan_short skill - creates a full script from a topic."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic: str = Field(
        ...,
        description="The topic or claim to create a short about (e.g., 'DeepSeek pricing crash')",
        min_length=5,
        max_length=500,
    )
    style: VideoStyle = Field(
        default=VideoStyle.VARUN_MAYYA,
        description="Style preset: varun_mayya (tech/authority), johnny_harris (explainer), generic",
    )
    duration_seconds: int = Field(
        default=45,
        description="Target duration in seconds (15-60 for shorts)",
        ge=15,
        le=120,
    )
    evidence_urls: Optional[list[str]] = Field(
        default=None,
        description="Optional list of URLs to use as evidence sources",
        max_length=10,
    )
    num_scenes: int = Field(
        default=5,
        description="Number of scenes to generate (4-8 typical)",
        ge=3,
        le=10,
    )


class AnalyzeHookInput(BaseModel):
    """Input for the analyze_hook skill - evaluates first 3 seconds."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    script_json: str = Field(
        ...,
        description="The script.json content as a string, or path to script file",
    )
    scene_id: int = Field(
        default=1,
        description="Which scene to analyze (usually 1 for hook)",
        ge=1,
    )


class GenerateBeatSheetInput(BaseModel):
    """Input for the generate_beat_sheet skill - creates timing breakdown."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    script_json: str = Field(
        ...,
        description="The script.json content as a string, or path to script file",
    )
    beat_interval_seconds: int = Field(
        default=5,
        description="Target interval between beats (5-7 seconds typical)",
        ge=3,
        le=10,
    )


class ValidateRetentionInput(BaseModel):
    """Input for the validate_retention skill - scores retention potential."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    script_json: str = Field(
        ...,
        description="The script.json content as a string, or path to script file",
    )
    target_retention_pct: int = Field(
        default=70,
        description="Target average view percentage (50-90 typical)",
        ge=30,
        le=100,
    )


# --- Output Models ---


class VisualPlan(BaseModel):
    """Visual specification for a scene."""

    type: VisualType
    description: str = Field(description="What to show (search query for Investigator)")
    why: Optional[str] = Field(default=None, description="Reasoning for this visual choice")


class Scene(BaseModel):
    """A single scene in the script."""

    scene_id: int
    role: SceneRole
    voiceover_script: str = Field(description="Narrator text, max 20 words")
    visual_plan: VisualPlan
    needs_evidence: bool = Field(description="Whether this scene requires visual proof")
    duration_seconds: float = Field(default=5.0, description="Scene duration")


class ScriptOutput(BaseModel):
    """Complete script output from plan_short."""

    project_title: str
    style: VideoStyle
    total_duration_seconds: float
    scenes: list[Scene]
    evidence_needed: list[str] = Field(
        description="List of visual descriptions that need to be captured"
    )


class HookAnalysis(BaseModel):
    """Output from analyze_hook skill."""

    hook_score: int = Field(ge=1, le=10, description="Score from 1-10")
    pattern_interrupt: str = Field(description="Strength: weak, moderate, strong")
    scroll_stop_potential: str
    suggestions: list[str]
    improved_hook: Optional[str] = Field(
        default=None, description="Suggested improved hook text"
    )
    visual_match: bool = Field(description="Whether visual matches hook energy")


class Beat(BaseModel):
    """A single beat in the beat sheet."""

    time_range: str = Field(description="e.g., '0-3s', '3-8s'")
    beat_type: str = Field(description="hook, setup, proof, escalation, cta")
    stakes: str = Field(description="What's at stake: attention, credibility, consequence")
    visual: str = Field(description="Visual type for this beat")
    scene_id: int


class BeatSheet(BaseModel):
    """Output from generate_beat_sheet skill."""

    total_duration_seconds: float
    num_beats: int
    beats: list[Beat]
    stakes_curve: str = Field(description="ascending, flat, or descending")
    pacing_score: int = Field(ge=1, le=10)


class DropOffRisk(BaseModel):
    """A potential viewer drop-off point."""

    time_seconds: float
    reason: str
    severity: DropOffSeverity


class RetentionValidation(BaseModel):
    """Output from validate_retention skill."""

    retention_score: float = Field(ge=0, le=10)
    predicted_avg_view_pct: int = Field(ge=0, le=100)
    drop_off_risks: list[DropOffRisk]
    recommendations: list[str]
    visual_change_frequency: float = Field(
        description="Average seconds between visual changes"
    )
    stakes_escalation_valid: bool
    benchmark_comparison: str
