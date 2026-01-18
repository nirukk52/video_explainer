"""Music generation module for creating background music using AI."""

from .generator import (
    MusicGenerator,
    MusicConfig,
    MusicGenerationResult,
    generate_for_project,
    generate_for_short,
    get_shorts_music_prompt,
    analyze_shorts_mood,
    SHORTS_STYLE_PRESETS,
)

__all__ = [
    "MusicGenerator",
    "MusicConfig",
    "MusicGenerationResult",
    "generate_for_project",
    "generate_for_short",
    "get_shorts_music_prompt",
    "analyze_shorts_mood",
    "SHORTS_STYLE_PRESETS",
]
