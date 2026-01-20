"""
Script refinement module for Phase 1 (Gap Analysis) and Phase 2 (Script Refinement).

Phase 1: Analyze source material against script to identify:
- Missing concepts
- Shallow coverage of important topics
- Narrative gaps between scenes
- Generate patches to fix identified gaps

Phase 2: Apply patches and refine narrations for better storytelling:
- Load patches from Phase 1
- Generate additional storytelling refinement patches
- Apply approved patches to script.json and narrations.json
"""

from .analyzer import ScriptAnalyzer
from .narration_refiner import ScriptRefiner, NarrationRefiner

__all__ = [
    "ScriptAnalyzer",
    "ScriptRefiner",
    "NarrationRefiner",  # Alias for backwards compatibility
]
