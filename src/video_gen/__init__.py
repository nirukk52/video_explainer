"""Video generation module.

This module provides integration with text-to-video APIs for generating AI videos
from prompts. Supports fal.ai (Veo3) for pure text-to-video generation.
"""

from .fal_generator import (
    FalVideoGenerator,
    FalVideoResult, 
    FalVideoConfig,
    AspectRatio,
    Duration,
    Resolution,
)

__all__ = [
    "FalVideoGenerator",
    "FalVideoResult",
    "FalVideoConfig",
    "AspectRatio",
    "Duration", 
    "Resolution",
]
