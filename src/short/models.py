"""Data models for YouTube Shorts generation."""

from enum import Enum
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class ShortMode(str, Enum):
    """Mode for generating shorts."""

    HOOK = "hook"  # Select compelling scenes, deep dive with cliffhanger
    SUMMARY = "summary"  # Cover all scenes, rapid-fire teaser sweep


class VisualType(str, Enum):
    """Types of visuals that can be shown in shorts."""

    # Text-based visuals (simple, fast)
    BIG_NUMBER = "big_number"  # Large stat with label (e.g., "150,528 pixels")
    COMPARISON = "comparison"  # Two values side by side
    TEXT_HIGHLIGHT = "text_highlight"  # Key phrase with emphasis
    SIMPLE_FLOW = "simple_flow"  # A → B → C flow diagram
    ICON_STAT = "icon_stat"  # Icon with statistic
    KEY_POINT = "key_point"  # Bullet point or key insight
    QUESTION = "question"  # Hook question display

    # Scene component visuals (rich, animated)
    TOKEN_GRID = "token_grid"  # Animated token grid (prefill/decode)
    PROGRESS_BARS = "progress_bars"  # Animated progress/utilization bars
    CODE_BLOCK = "code_block"  # Syntax-highlighted code snippet
    DIAGRAM = "diagram"  # Simple diagram/flow
    FLOW_DIAGRAM = "flow_diagram"  # Flow diagram (same as diagram)
    EQUATION = "equation"  # Mathematical equation
    IMAGE = "image"  # Static image with animation
    PATCH_GRID = "patch_grid"  # Image divided into patches (ViT style)
    EMBEDDING_BARS = "embedding_bars"  # Animated embedding vector bars
    ATTENTION_VISUAL = "attention_visual"  # Attention pattern/heatmap
    MASKED_GRID = "masked_grid"  # Grid with masked/visible tokens (BERT/MAE style)


class SceneComponentConfig(BaseModel):
    """Configuration for a scene component visual."""

    component_type: str  # e.g., "token_grid", "progress_bars", "code_block"
    props: dict[str, Any] = Field(default_factory=dict)  # Component-specific props

    # For token grid
    tokens: list[str] = Field(default_factory=list)
    mode: str = "prefill"  # "prefill" or "decode"
    rows: int = 4
    cols: int = 4

    # For progress bars
    bars: list[dict[str, Any]] = Field(default_factory=list)  # [{label, value, color}]

    # For code block
    code: str = ""
    language: str = "python"
    highlight_lines: list[int] = Field(default_factory=list)

    # For image
    image_path: str = ""
    caption: str = ""

    # For patch grid
    highlight_indices: list[int] = Field(default_factory=list)

    # For embedding bars
    dimensions: int = 8
    values: list[float] = Field(default_factory=list)

    # For attention visual
    size: int = 6
    pattern: str = "self"  # "self", "cross", or "causal"

    # For masked grid
    masked_indices: list[int] = Field(default_factory=list)


class ShortsVisual(BaseModel):
    """A visual element to display in the shorts visual area."""

    type: VisualType
    primary_text: str  # Main text/number to display
    secondary_text: str = ""  # Supporting text (label, comparison value, etc.)
    tertiary_text: str = ""  # Additional context
    icon: str = ""  # Emoji or icon name
    color: str = "primary"  # Color theme: primary, secondary, success, warning, etc.

    # Scene component configuration (for rich visuals)
    scene_config: SceneComponentConfig | None = None

    # Reference to source scene (for extracting visuals from original video)
    source_scene_id: str = ""  # Which scene this visual was extracted from


class PhaseMarker(BaseModel):
    """A marker that defines a phase boundary in a scene.

    Phase markers link scene animation phases to specific words in the voiceover.
    When the voiceover timing changes, the timing generator uses these markers
    to recalculate frame numbers automatically.
    """

    id: str  # e.g., "phase1", "gptAppear", "claudeAppear"
    end_word: str  # Word that marks the end of this phase (e.g., "GPT,", "Claude")
    description: str = ""  # Optional human-readable description


class ShortsBeat(BaseModel):
    """A single beat/moment in the shorts storyboard."""

    id: str
    start_seconds: float
    end_seconds: float
    visual: ShortsVisual
    caption_text: str  # Text to show as caption
    word_timestamps: list[dict[str, Any]] = Field(default_factory=list)  # For sync

    # Custom scene generation fields
    visual_description: str = ""  # From source scene's visual_cue.description
    visual_elements: list[str] = Field(default_factory=list)  # From source scene's visual_cue.elements
    component_name: str = ""  # e.g., "Beat1Scene" - name of custom React component
    source_scene_file: str = ""  # e.g., "TokenizationScene.tsx" - source scene for inspiration

    # Phase markers for timing synchronization
    phase_markers: list[PhaseMarker] = Field(default_factory=list)  # For auto-syncing scene timing


class ShortsStoryboard(BaseModel):
    """Complete storyboard for a YouTube Short."""

    id: str
    title: str
    total_duration_seconds: float
    beats: list[ShortsBeat]
    hook_question: str = ""
    cta_text: str = "Full breakdown in description"
    voiceover_path: str = ""  # Path to combined voiceover audio


class ShortConfig(BaseModel):
    """Configuration for short generation."""

    width: int = 1080
    height: int = 1920
    fps: int = 30
    target_duration_seconds: int = 45
    include_cta: bool = True
    cta_duration_seconds: float = 5.0


class ShortScene(BaseModel):
    """A scene selected for the short.

    Note: The condensed_narration field is deprecated at the scene level.
    Use ShortScript.condensed_narration instead for the full narration.
    """

    source_scene_id: str
    condensed_narration: str = ""  # Deprecated: use ShortScript.condensed_narration
    duration_seconds: float


class ShortScript(BaseModel):
    """Complete short script."""

    source_project: str
    title: str
    condensed_narration: str = ""  # The full condensed narration for the short
    hook_question: str  # The cliffhanger question (or intrigue_close for summary mode)
    scenes: list[ShortScene]
    cta_text: str
    cta_narration: str  # Voiceover for CTA
    total_duration_seconds: float
    mode: ShortMode = ShortMode.HOOK  # Generation mode used


class HookAnalysis(BaseModel):
    """Result of analyzing script for best hook."""

    selected_scene_ids: list[str]
    hook_question: str
    reasoning: str


class SceneHighlight(BaseModel):
    """A highlight/teaser from a single scene for summary mode."""

    scene_id: str
    scene_title: str
    teaser_phrase: str  # 2-5 word hook for this layer
    key_number: str = ""  # Optional specific number to feature
    visual_hint: str = ""  # Hint for visual type (e.g., "grid", "flow", "number")


class SummaryAnalysis(BaseModel):
    """Result of analyzing script for summary mode."""

    scene_highlights: list[SceneHighlight]
    narrative_arc: str  # e.g., "descent", "journey", "transformation"
    hook_opening: str  # Opening line, e.g., "You press a key..."
    intrigue_close: str  # Closing hook before CTA
    total_scenes: int  # Number of scenes being summarized


class CondensedNarration(BaseModel):
    """Result of condensed narration generation."""

    condensed_narration: str
    cta_narration: str
    hook_question: str


class ShortResult(BaseModel):
    """Result of short generation pipeline."""

    success: bool
    variant: str
    short_script_path: Path | None = None
    scenes_dir: Path | None = None
    voiceover_dir: Path | None = None
    storyboard_path: Path | None = None
    output_path: Path | None = None
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True
