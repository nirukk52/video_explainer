"""
Video Refinement Module

This module provides tools to refine video projects to high quality standards
(3Blue1Brown / Veritasium level). It implements a 3-phase refinement process:

Phase 1 (Analyze): Compare source material against script to identify gaps
Phase 2 (Script): Refine narrations and update script structure
Phase 3 (Visual): Inspect and refine scene visuals

The refinement process is designed to be human-in-the-loop, with AI handling
tedious work while humans make creative judgments.

Example usage:
    from src.refine import VisualInspector, ScriptAnalyzer, NarrationRefiner
    from src.project import load_project

    project = load_project("projects/my-project")

    # Phase 1: Gap analysis
    analyzer = ScriptAnalyzer(project)
    gaps = analyzer.analyze()

    # Phase 2: Narration refinement
    refiner = NarrationRefiner(project)
    narration_result = refiner.refine()

    # Phase 3: Visual refinement
    inspector = VisualInspector(project)
    visual_result = inspector.refine_scene(0)
"""

from .models import (
    # Core models
    Beat,
    Issue,
    IssueType,
    Fix,
    FixStatus,
    RefinementPhase,
    RefinementResult,
    SceneRefinementResult,
    ProjectSyncStatus,
    SyncIssue,
    SyncIssueType,
    # Phase 1: Gap Analysis models
    ConceptDepth,
    SourceConcept,
    ConceptCoverage,
    NarrativeGap,
    SuggestedScene,
    GapAnalysisResult,
    # Script Patch models (Phase 1 output, Phase 2 input)
    ScriptPatchType,
    ScriptPatch,
    AddScenePatch,
    ModifyScenePatch,
    ExpandScenePatch,
    AddBridgePatch,
    # Phase 2: Narration Refinement models
    NarrationIssueType,
    NarrationIssue,
    NarrationScores,
    SceneNarrationAnalysis,
    NarrationRefinementResult,
)
from .principles import (
    GUIDING_PRINCIPLES,
    Principle,
    format_principles_for_prompt,
    format_checklist_for_prompt,
    get_principle_by_id,
)
from .narration_principles import (
    NARRATION_PRINCIPLES,
    NarrationPrinciple,
    format_principles_for_prompt as format_narration_principles_for_prompt,
    format_checklist_for_prompt as format_narration_checklist_for_prompt,
)
from .validation import validate_project_sync, ProjectValidator
from .visual import BeatParser, ScreenshotCapture, VisualInspector
from .script import ScriptAnalyzer, ScriptRefiner, NarrationRefiner

__all__ = [
    # Core Models
    "Beat",
    "Issue",
    "IssueType",
    "Fix",
    "FixStatus",
    "RefinementPhase",
    "RefinementResult",
    "SceneRefinementResult",
    "ProjectSyncStatus",
    "SyncIssue",
    "SyncIssueType",
    # Phase 1: Gap Analysis Models
    "ConceptDepth",
    "SourceConcept",
    "ConceptCoverage",
    "NarrativeGap",
    "SuggestedScene",
    "GapAnalysisResult",
    # Script Patch Models
    "ScriptPatchType",
    "ScriptPatch",
    "AddScenePatch",
    "ModifyScenePatch",
    "ExpandScenePatch",
    "AddBridgePatch",
    # Phase 2: Narration Refinement Models
    "NarrationIssueType",
    "NarrationIssue",
    "NarrationScores",
    "SceneNarrationAnalysis",
    "NarrationRefinementResult",
    # Visual Principles
    "GUIDING_PRINCIPLES",
    "Principle",
    "format_principles_for_prompt",
    "format_checklist_for_prompt",
    "get_principle_by_id",
    # Narration Principles
    "NARRATION_PRINCIPLES",
    "NarrationPrinciple",
    "format_narration_principles_for_prompt",
    "format_narration_checklist_for_prompt",
    # Validation
    "validate_project_sync",
    "ProjectValidator",
    # Phase 1: Script Analysis
    "ScriptAnalyzer",
    # Phase 2: Script Refinement
    "ScriptRefiner",
    "NarrationRefiner",  # Alias for backwards compatibility
    # Phase 3: Visual
    "BeatParser",
    "ScreenshotCapture",
    "VisualInspector",
]
