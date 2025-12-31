"""Sound design module for video explainer.

This module provides SFX generation for frame-accurate sound design.

The sound design workflow is:
1. Define sfx_cues in storyboard.json (frame-accurate annotations)
2. Generate SFX files using SoundLibrary
3. Remotion renders video with SFX at specified frames

Components:
- library: SFX generation with 10 focused sounds
"""

from .library import SoundLibrary, SOUND_MANIFEST

__all__ = [
    "SoundLibrary",
    "SOUND_MANIFEST",
]
