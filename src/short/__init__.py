"""YouTube Shorts generator module.

This module provides functionality to generate YouTube Shorts (vertical, 30-60 seconds)
from existing full-length video projects. The short hooks viewers with intriguing content
and drives them to watch the full video.

Pipeline:
1. Analyze script to pick best hook scenes
2. Generate condensed narration
3. Generate vertical scenes
4. Generate CTA scene
5. Generate voiceover audio
6. Create short storyboard
7. Render vertical video
"""

from .models import (
    ShortConfig,
    ShortMode,
    ShortScene,
    ShortScript,
    ShortResult,
    VisualType,
    ShortsVisual,
    ShortsBeat,
    ShortsStoryboard,
    SceneComponentConfig,
    SummaryAnalysis,
    SceneHighlight,
)
from .generator import ShortGenerator
from .scene_generator import ShortSceneGenerator
from .custom_scene_generator import ShortsCustomSceneGenerator

__all__ = [
    "ShortConfig",
    "ShortMode",
    "ShortScene",
    "ShortScript",
    "ShortResult",
    "VisualType",
    "ShortsVisual",
    "ShortsBeat",
    "ShortsStoryboard",
    "SceneComponentConfig",
    "SummaryAnalysis",
    "SceneHighlight",
    "ShortGenerator",
    "ShortSceneGenerator",
    "ShortsCustomSceneGenerator",
]
