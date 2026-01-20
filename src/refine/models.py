"""
Data models for the refinement module.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class IssueType(str, Enum):
    """Types of issues that can be identified during refinement."""

    SHOW_DONT_TELL = "show_dont_tell"
    ANIMATION_REVEALS = "animation_reveals"
    PROGRESSIVE_DISCLOSURE = "progressive_disclosure"
    TEXT_COMPLEMENTS = "text_complements"
    VISUAL_HIERARCHY = "visual_hierarchy"
    BREATHING_ROOM = "breathing_room"
    PURPOSEFUL_MOTION = "purposeful_motion"
    EMOTIONAL_RESONANCE = "emotional_resonance"
    PROFESSIONAL_POLISH = "professional_polish"
    SYNC_WITH_NARRATION = "sync_with_narration"
    SCREEN_SPACE_UTILIZATION = "screen_space_utilization"
    OTHER = "other"


class FixStatus(str, Enum):
    """Status of a fix."""

    PENDING = "pending"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"


class RefinementPhase(str, Enum):
    """Phases of the refinement process."""

    ANALYZE = "analyze"
    SCRIPT = "script"
    VISUAL = "visual"


@dataclass
class Beat:
    """
    A visual beat in the narration - a key phrase that should trigger
    a specific visual change.
    """

    index: int
    start_seconds: float
    end_seconds: float
    text: str
    expected_visual: str = ""  # Description of what should be visible

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def mid_seconds(self) -> float:
        """Middle point of the beat, useful for screenshot timing."""
        return (self.start_seconds + self.end_seconds) / 2

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "expected_visual": self.expected_visual,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Beat":
        return cls(
            index=data["index"],
            start_seconds=data["start_seconds"],
            end_seconds=data["end_seconds"],
            text=data["text"],
            expected_visual=data.get("expected_visual", ""),
        )


@dataclass
class Issue:
    """An issue identified during visual inspection."""

    beat_index: int
    principle_violated: IssueType
    description: str
    severity: str = "medium"  # low, medium, high
    screenshot_path: Optional[Path] = None

    def to_dict(self) -> dict:
        return {
            "beat_index": self.beat_index,
            "principle_violated": self.principle_violated.value,
            "description": self.description,
            "severity": self.severity,
            "screenshot_path": str(self.screenshot_path) if self.screenshot_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Issue":
        return cls(
            beat_index=data["beat_index"],
            principle_violated=IssueType(data["principle_violated"]),
            description=data["description"],
            severity=data.get("severity", "medium"),
            screenshot_path=Path(data["screenshot_path"]) if data.get("screenshot_path") else None,
        )


@dataclass
class Fix:
    """A fix to be applied to address an issue."""

    issue: Issue
    file_path: Path
    description: str
    code_change: str  # Description or diff of the change
    status: FixStatus = FixStatus.PENDING
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "issue": self.issue.to_dict(),
            "file_path": str(self.file_path),
            "description": self.description,
            "code_change": self.code_change,
            "status": self.status.value,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Fix":
        return cls(
            issue=Issue.from_dict(data["issue"]),
            file_path=Path(data["file_path"]),
            description=data["description"],
            code_change=data["code_change"],
            status=FixStatus(data["status"]),
            error_message=data.get("error_message"),
        )


@dataclass
class SceneRefinementResult:
    """Result of refining a single scene."""

    scene_id: str
    scene_title: str
    scene_file: Path
    beats: list[Beat] = field(default_factory=list)
    issues_found: list[Issue] = field(default_factory=list)
    fixes_applied: list[Fix] = field(default_factory=list)
    verification_passed: bool = False
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.verification_passed and self.error_message is None

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "scene_title": self.scene_title,
            "scene_file": str(self.scene_file),
            "beats": [b.to_dict() for b in self.beats],
            "issues_found": [i.to_dict() for i in self.issues_found],
            "fixes_applied": [f.to_dict() for f in self.fixes_applied],
            "verification_passed": self.verification_passed,
            "error_message": self.error_message,
        }


@dataclass
class RefinementResult:
    """Overall result of the refinement process."""

    project_id: str
    phase: RefinementPhase
    scenes_refined: list[SceneRefinementResult] = field(default_factory=list)
    total_issues_found: int = 0
    total_fixes_applied: int = 0
    success: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "phase": self.phase.value,
            "scenes_refined": [s.to_dict() for s in self.scenes_refined],
            "total_issues_found": self.total_issues_found,
            "total_fixes_applied": self.total_fixes_applied,
            "success": self.success,
            "error_message": self.error_message,
        }


class NarrationIssueType(str, Enum):
    """Types of issues that can be identified in narrations."""

    WEAK_HOOK = "weak_hook"
    POOR_TRANSITION = "poor_transition"
    MISSING_TENSION = "missing_tension"
    NO_KEY_INSIGHT = "no_key_insight"
    LACKS_ANALOGY = "lacks_analogy"
    NO_EMOTIONAL_BEAT = "no_emotional_beat"
    WRONG_LENGTH = "wrong_length"
    TECHNICAL_INACCURACY = "technical_inaccuracy"
    REDUNDANT_TEXT = "redundant_text"
    OTHER = "other"


class ConceptDepth(str, Enum):
    """Depth of concept coverage."""

    NOT_COVERED = "not_covered"
    MENTIONED = "mentioned"  # Brief mention only
    EXPLAINED = "explained"  # Basic explanation
    DEEP_DIVE = "deep_dive"  # Detailed with examples/analogies


class SyncIssueType(str, Enum):
    """Types of project sync issues."""

    SCENE_COUNT_MISMATCH = "scene_count_mismatch"
    MISSING_VOICEOVER = "missing_voiceover"
    DURATION_MISMATCH = "duration_mismatch"
    MISSING_SCENE_FILE = "missing_scene_file"
    STORYBOARD_OUTDATED = "storyboard_outdated"


@dataclass
class SyncIssue:
    """A project synchronization issue."""

    issue_type: SyncIssueType
    description: str
    affected_scene: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "description": self.description,
            "affected_scene": self.affected_scene,
            "suggestion": self.suggestion,
        }


@dataclass
class ProjectSyncStatus:
    """Status of project file synchronization."""

    is_synced: bool
    issues: list[SyncIssue] = field(default_factory=list)
    storyboard_scene_count: int = 0
    narration_scene_count: int = 0
    voiceover_file_count: int = 0
    scene_file_count: int = 0

    def to_dict(self) -> dict:
        return {
            "is_synced": self.is_synced,
            "issues": [i.to_dict() for i in self.issues],
            "storyboard_scene_count": self.storyboard_scene_count,
            "narration_scene_count": self.narration_scene_count,
            "voiceover_file_count": self.voiceover_file_count,
            "scene_file_count": self.scene_file_count,
        }


# =============================================================================
# Phase 1: Gap Analysis Models
# =============================================================================


@dataclass
class SourceConcept:
    """A concept extracted from the source material."""

    name: str
    description: str
    importance: str = "medium"  # low, medium, high, critical
    prerequisites: list[str] = field(default_factory=list)
    section_reference: str = ""  # Where in the source this appears

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "importance": self.importance,
            "prerequisites": self.prerequisites,
            "section_reference": self.section_reference,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SourceConcept":
        return cls(
            name=data["name"],
            description=data["description"],
            importance=data.get("importance", "medium"),
            prerequisites=data.get("prerequisites", []),
            section_reference=data.get("section_reference", ""),
        )


@dataclass
class ConceptCoverage:
    """Analysis of how a concept is covered in the script."""

    concept: SourceConcept
    depth: ConceptDepth
    scene_ids: list[str] = field(default_factory=list)
    coverage_notes: str = ""
    suggestion: Optional[str] = None
    # Reason for intentional omission (if not covered but that's okay)
    # Values: too_tangential, too_advanced, time_constraints, covered_elsewhere, implementation_detail
    omission_reason: Optional[str] = None

    @property
    def is_covered(self) -> bool:
        return self.depth != ConceptDepth.NOT_COVERED

    @property
    def is_intentionally_omitted(self) -> bool:
        """Concept not covered but marked as okay to skip."""
        return not self.is_covered and self.omission_reason is not None

    @property
    def needs_improvement(self) -> bool:
        """High/critical importance concepts should have at least 'explained' depth."""
        # If intentionally omitted, don't flag as needing improvement
        if self.is_intentionally_omitted:
            return False
        if self.concept.importance in ("high", "critical"):
            return self.depth in (ConceptDepth.NOT_COVERED, ConceptDepth.MENTIONED)
        return self.depth == ConceptDepth.NOT_COVERED

    def to_dict(self) -> dict:
        return {
            "concept": self.concept.to_dict(),
            "depth": self.depth.value,
            "scene_ids": self.scene_ids,
            "coverage_notes": self.coverage_notes,
            "suggestion": self.suggestion,
            "omission_reason": self.omission_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConceptCoverage":
        return cls(
            concept=SourceConcept.from_dict(data["concept"]),
            depth=ConceptDepth(data["depth"]),
            scene_ids=data.get("scene_ids", []),
            coverage_notes=data.get("coverage_notes", ""),
            suggestion=data.get("suggestion"),
            omission_reason=data.get("omission_reason"),
        )


@dataclass
class NarrativeGap:
    """A gap in the narrative flow between scenes."""

    from_scene_id: str
    from_scene_title: str
    to_scene_id: str
    to_scene_title: str
    gap_description: str
    severity: str = "medium"  # low, medium, high
    suggested_bridge: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "from_scene_id": self.from_scene_id,
            "from_scene_title": self.from_scene_title,
            "to_scene_id": self.to_scene_id,
            "to_scene_title": self.to_scene_title,
            "gap_description": self.gap_description,
            "severity": self.severity,
            "suggested_bridge": self.suggested_bridge,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrativeGap":
        return cls(
            from_scene_id=data["from_scene_id"],
            from_scene_title=data["from_scene_title"],
            to_scene_id=data["to_scene_id"],
            to_scene_title=data["to_scene_title"],
            gap_description=data["gap_description"],
            severity=data.get("severity", "medium"),
            suggested_bridge=data.get("suggested_bridge"),
        )


@dataclass
class SuggestedScene:
    """A suggested new scene to address gaps."""

    title: str
    reason: str
    suggested_position: int  # Scene number (1-based) where it should be inserted
    concepts_addressed: list[str] = field(default_factory=list)
    suggested_narration: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "reason": self.reason,
            "suggested_position": self.suggested_position,
            "concepts_addressed": self.concepts_addressed,
            "suggested_narration": self.suggested_narration,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SuggestedScene":
        return cls(
            title=data["title"],
            reason=data["reason"],
            suggested_position=data["suggested_position"],
            concepts_addressed=data.get("concepts_addressed", []),
            suggested_narration=data.get("suggested_narration", ""),
        )


class ScriptPatchType(str, Enum):
    """Types of script patches."""

    ADD_SCENE = "add_scene"  # Insert a new scene
    MODIFY_SCENE = "modify_scene"  # Change an existing scene's content
    EXPAND_SCENE = "expand_scene"  # Add content to cover missing concepts
    ADD_BRIDGE = "add_bridge"  # Add transition content between scenes


@dataclass
class ScriptPatch:
    """A patch to apply to the script/narration."""

    patch_type: ScriptPatchType
    reason: str = ""  # Why this patch is needed
    priority: str = "medium"  # low, medium, high, critical

    def to_dict(self) -> dict:
        return {
            "patch_type": self.patch_type.value,
            "reason": self.reason,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScriptPatch":
        patch_type = ScriptPatchType(data["patch_type"])
        if patch_type == ScriptPatchType.ADD_SCENE:
            return AddScenePatch.from_dict(data)
        elif patch_type == ScriptPatchType.MODIFY_SCENE:
            return ModifyScenePatch.from_dict(data)
        elif patch_type == ScriptPatchType.EXPAND_SCENE:
            return ExpandScenePatch.from_dict(data)
        elif patch_type == ScriptPatchType.ADD_BRIDGE:
            return AddBridgePatch.from_dict(data)
        else:
            return cls(
                patch_type=patch_type,
                reason=data.get("reason", ""),
                priority=data.get("priority", "medium"),
            )


@dataclass
class AddScenePatch(ScriptPatch):
    """Patch to add a new scene."""

    patch_type: ScriptPatchType = field(default=ScriptPatchType.ADD_SCENE)
    insert_after_scene_id: Optional[str] = None  # None = insert at beginning
    new_scene_id: str = ""
    title: str = ""
    narration: str = ""
    visual_description: str = ""
    duration_seconds: float = 30.0
    concepts_addressed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "insert_after_scene_id": self.insert_after_scene_id,
            "new_scene_id": self.new_scene_id,
            "title": self.title,
            "narration": self.narration,
            "visual_description": self.visual_description,
            "duration_seconds": self.duration_seconds,
            "concepts_addressed": self.concepts_addressed,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict) -> "AddScenePatch":
        return cls(
            reason=data.get("reason", ""),
            priority=data.get("priority", "medium"),
            insert_after_scene_id=data.get("insert_after_scene_id"),
            new_scene_id=data.get("new_scene_id", ""),
            title=data.get("title", ""),
            narration=data.get("narration", ""),
            visual_description=data.get("visual_description", ""),
            duration_seconds=data.get("duration_seconds", 30.0),
            concepts_addressed=data.get("concepts_addressed", []),
        )


@dataclass
class ModifyScenePatch(ScriptPatch):
    """Patch to modify an existing scene's narration."""

    patch_type: ScriptPatchType = field(default=ScriptPatchType.MODIFY_SCENE)
    scene_id: str = ""
    field_name: str = "narration"  # narration, title, visual_description
    old_value: str = ""
    new_value: str = ""

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "scene_id": self.scene_id,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict) -> "ModifyScenePatch":
        return cls(
            reason=data.get("reason", ""),
            priority=data.get("priority", "medium"),
            scene_id=data.get("scene_id", ""),
            field_name=data.get("field_name", "narration"),
            old_value=data.get("old_value", ""),
            new_value=data.get("new_value", ""),
        )


@dataclass
class ExpandScenePatch(ScriptPatch):
    """Patch to expand a scene to cover concepts more deeply."""

    patch_type: ScriptPatchType = field(default=ScriptPatchType.EXPAND_SCENE)
    scene_id: str = ""
    current_narration: str = ""
    expanded_narration: str = ""
    concepts_to_add: list[str] = field(default_factory=list)
    additional_duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "scene_id": self.scene_id,
            "current_narration": self.current_narration,
            "expanded_narration": self.expanded_narration,
            "concepts_to_add": self.concepts_to_add,
            "additional_duration_seconds": self.additional_duration_seconds,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict) -> "ExpandScenePatch":
        return cls(
            reason=data.get("reason", ""),
            priority=data.get("priority", "medium"),
            scene_id=data.get("scene_id", ""),
            current_narration=data.get("current_narration", ""),
            expanded_narration=data.get("expanded_narration", ""),
            concepts_to_add=data.get("concepts_to_add", []),
            additional_duration_seconds=data.get("additional_duration_seconds", 0.0),
        )


@dataclass
class AddBridgePatch(ScriptPatch):
    """Patch to add bridging content between two scenes."""

    patch_type: ScriptPatchType = field(default=ScriptPatchType.ADD_BRIDGE)
    from_scene_id: str = ""
    to_scene_id: str = ""
    bridge_type: str = "transition"  # transition, recap, foreshadow
    # Can either modify the ending of from_scene or beginning of to_scene
    modify_scene_id: str = ""  # Which scene to modify
    current_text: str = ""
    new_text: str = ""

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "from_scene_id": self.from_scene_id,
            "to_scene_id": self.to_scene_id,
            "bridge_type": self.bridge_type,
            "modify_scene_id": self.modify_scene_id,
            "current_text": self.current_text,
            "new_text": self.new_text,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict) -> "AddBridgePatch":
        return cls(
            reason=data.get("reason", ""),
            priority=data.get("priority", "medium"),
            from_scene_id=data.get("from_scene_id", ""),
            to_scene_id=data.get("to_scene_id", ""),
            bridge_type=data.get("bridge_type", "transition"),
            modify_scene_id=data.get("modify_scene_id", ""),
            current_text=data.get("current_text", ""),
            new_text=data.get("new_text", ""),
        )


@dataclass
class GapAnalysisResult:
    """Result of analyzing gaps between source material and script."""

    project_id: str
    source_file: str
    concepts: list[ConceptCoverage] = field(default_factory=list)
    narrative_gaps: list[NarrativeGap] = field(default_factory=list)
    suggested_scenes: list[SuggestedScene] = field(default_factory=list)
    patches: list[ScriptPatch] = field(default_factory=list)  # Actionable patches
    overall_coverage_score: float = 0.0  # 0-100
    analysis_notes: str = ""
    intentional_omissions_summary: str = ""  # Brief explanation of what was left out and why

    @property
    def missing_concepts(self) -> list[str]:
        """Concepts not covered at all (excluding intentional omissions)."""
        return [
            c.concept.name for c in self.concepts
            if c.depth == ConceptDepth.NOT_COVERED and not c.is_intentionally_omitted
        ]

    @property
    def intentionally_omitted_concepts(self) -> list[tuple[str, str]]:
        """Concepts intentionally not covered, with their reasons."""
        return [
            (c.concept.name, c.omission_reason or "unspecified")
            for c in self.concepts
            if c.is_intentionally_omitted
        ]

    @property
    def shallow_concepts(self) -> list[str]:
        """Important concepts that need deeper coverage."""
        return [c.concept.name for c in self.concepts if c.needs_improvement and c.is_covered]

    @property
    def has_critical_gaps(self) -> bool:
        """Check if there are any critical gaps that must be addressed."""
        # Don't count intentionally omitted concepts as critical gaps
        critical_missing = any(
            c.concept.importance == "critical"
            and c.depth == ConceptDepth.NOT_COVERED
            and not c.is_intentionally_omitted
            for c in self.concepts
        )
        high_severity_gaps = any(g.severity == "high" for g in self.narrative_gaps)
        return critical_missing or high_severity_gaps

    @property
    def critical_patches(self) -> list[ScriptPatch]:
        """Patches with critical or high priority."""
        return [p for p in self.patches if p.priority in ("critical", "high")]

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "source_file": self.source_file,
            "concepts": [c.to_dict() for c in self.concepts],
            "narrative_gaps": [g.to_dict() for g in self.narrative_gaps],
            "suggested_scenes": [s.to_dict() for s in self.suggested_scenes],
            "patches": [p.to_dict() for p in self.patches],
            "overall_coverage_score": self.overall_coverage_score,
            "analysis_notes": self.analysis_notes,
            "intentional_omissions_summary": self.intentional_omissions_summary,
            "missing_concepts": self.missing_concepts,
            "intentionally_omitted_concepts": self.intentionally_omitted_concepts,
            "shallow_concepts": self.shallow_concepts,
            "has_critical_gaps": self.has_critical_gaps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GapAnalysisResult":
        return cls(
            project_id=data["project_id"],
            source_file=data["source_file"],
            concepts=[ConceptCoverage.from_dict(c) for c in data.get("concepts", [])],
            narrative_gaps=[NarrativeGap.from_dict(g) for g in data.get("narrative_gaps", [])],
            suggested_scenes=[SuggestedScene.from_dict(s) for s in data.get("suggested_scenes", [])],
            patches=[ScriptPatch.from_dict(p) for p in data.get("patches", [])],
            overall_coverage_score=data.get("overall_coverage_score", 0.0),
            analysis_notes=data.get("analysis_notes", ""),
            intentional_omissions_summary=data.get("intentional_omissions_summary", ""),
        )


# =============================================================================
# Phase 2: Narration Refinement Models
# =============================================================================


@dataclass
class NarrationIssue:
    """An issue identified in a scene's narration."""

    scene_id: str
    issue_type: NarrationIssueType
    description: str
    current_text: str  # The problematic portion
    severity: str = "medium"  # low, medium, high
    suggested_fix: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "issue_type": self.issue_type.value,
            "description": self.description,
            "current_text": self.current_text,
            "severity": self.severity,
            "suggested_fix": self.suggested_fix,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrationIssue":
        return cls(
            scene_id=data["scene_id"],
            issue_type=NarrationIssueType(data["issue_type"]),
            description=data["description"],
            current_text=data["current_text"],
            severity=data.get("severity", "medium"),
            suggested_fix=data.get("suggested_fix"),
        )


@dataclass
class NarrationScores:
    """Quality scores for a scene's narration."""

    hook: float = 0.0  # 0-10: Does it grab attention?
    flow: float = 0.0  # 0-10: Does it connect to prev/next scenes?
    tension: float = 0.0  # 0-10: Does it build anticipation?
    insight: float = 0.0  # 0-10: Is there a clear takeaway?
    engagement: float = 0.0  # 0-10: Does it use analogies, questions, surprises?
    accuracy: float = 0.0  # 0-10: Is it technically correct?
    length: float = 0.0  # 0-10: Is it the right length for the duration?

    @property
    def overall(self) -> float:
        """Weighted average of all scores."""
        weights = {
            "hook": 1.5,
            "flow": 1.2,
            "tension": 1.0,
            "insight": 1.3,
            "engagement": 1.2,
            "accuracy": 1.5,
            "length": 0.8,
        }
        total = sum(
            getattr(self, attr) * weight for attr, weight in weights.items()
        )
        return total / sum(weights.values())

    def to_dict(self) -> dict:
        return {
            "hook": self.hook,
            "flow": self.flow,
            "tension": self.tension,
            "insight": self.insight,
            "engagement": self.engagement,
            "accuracy": self.accuracy,
            "length": self.length,
            "overall": self.overall,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrationScores":
        return cls(
            hook=data.get("hook", 0.0),
            flow=data.get("flow", 0.0),
            tension=data.get("tension", 0.0),
            insight=data.get("insight", 0.0),
            engagement=data.get("engagement", 0.0),
            accuracy=data.get("accuracy", 0.0),
            length=data.get("length", 0.0),
        )


@dataclass
class SceneNarrationAnalysis:
    """Analysis of a single scene's narration."""

    scene_id: str
    scene_title: str
    current_narration: str
    duration_seconds: float
    word_count: int
    scores: NarrationScores
    issues: list[NarrationIssue] = field(default_factory=list)
    suggested_revision: Optional[str] = None
    revision_applied: bool = False

    @property
    def needs_revision(self) -> bool:
        """Check if this narration has significant issues."""
        return len([i for i in self.issues if i.severity in ("medium", "high")]) > 0

    @property
    def expected_word_count(self) -> int:
        """Expected words based on duration (~150 words/minute)."""
        return int(self.duration_seconds * 2.5)  # 150 wpm = 2.5 words/sec

    @property
    def length_ratio(self) -> float:
        """Ratio of actual to expected word count."""
        if self.expected_word_count == 0:
            return 1.0
        return self.word_count / self.expected_word_count

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "scene_title": self.scene_title,
            "current_narration": self.current_narration,
            "duration_seconds": self.duration_seconds,
            "word_count": self.word_count,
            "expected_word_count": self.expected_word_count,
            "length_ratio": self.length_ratio,
            "scores": self.scores.to_dict(),
            "issues": [i.to_dict() for i in self.issues],
            "suggested_revision": self.suggested_revision,
            "revision_applied": self.revision_applied,
            "needs_revision": self.needs_revision,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SceneNarrationAnalysis":
        return cls(
            scene_id=data["scene_id"],
            scene_title=data["scene_title"],
            current_narration=data["current_narration"],
            duration_seconds=data["duration_seconds"],
            word_count=data["word_count"],
            scores=NarrationScores.from_dict(data["scores"]),
            issues=[NarrationIssue.from_dict(i) for i in data.get("issues", [])],
            suggested_revision=data.get("suggested_revision"),
            revision_applied=data.get("revision_applied", False),
        )


@dataclass
class NarrationRefinementResult:
    """Result of refining all narrations in a project."""

    project_id: str
    scene_analyses: list[SceneNarrationAnalysis] = field(default_factory=list)
    overall_storytelling_score: float = 0.0
    total_issues_found: int = 0
    revisions_applied: int = 0

    @property
    def scenes_needing_revision(self) -> list[str]:
        """Scene IDs that need revision."""
        return [s.scene_id for s in self.scene_analyses if s.needs_revision]

    @property
    def high_priority_scenes(self) -> list[str]:
        """Scenes with high-severity issues."""
        result = []
        for scene in self.scene_analyses:
            if any(i.severity == "high" for i in scene.issues):
                result.append(scene.scene_id)
        return result

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "scene_analyses": [s.to_dict() for s in self.scene_analyses],
            "overall_storytelling_score": self.overall_storytelling_score,
            "total_issues_found": self.total_issues_found,
            "revisions_applied": self.revisions_applied,
            "scenes_needing_revision": self.scenes_needing_revision,
            "high_priority_scenes": self.high_priority_scenes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrationRefinementResult":
        return cls(
            project_id=data["project_id"],
            scene_analyses=[
                SceneNarrationAnalysis.from_dict(s)
                for s in data.get("scene_analyses", [])
            ],
            overall_storytelling_score=data.get("overall_storytelling_score", 0.0),
            total_issues_found=data.get("total_issues_found", 0),
            revisions_applied=data.get("revisions_applied", 0),
        )
