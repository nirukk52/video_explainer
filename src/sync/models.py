"""
Data models for visual-voiceover sync feature.

This module defines the data structures for sync points, timing maps,
and migration plans used in the sync phase.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Any


class SyncPointType(str, Enum):
    """Types of synchronization points."""

    ELEMENT_APPEAR = "element_appear"  # Visual element enters the scene
    ELEMENT_EXIT = "element_exit"  # Visual element leaves the scene
    PHASE_TRANSITION = "phase_transition"  # Major visual phase change
    TEXT_REVEAL = "text_reveal"  # Text or label appears
    ANIMATION_START = "animation_start"  # Animation begins
    ANIMATION_PEAK = "animation_peak"  # Animation reaches climax
    DATA_UPDATE = "data_update"  # Data visualization updates
    EMPHASIS = "emphasis"  # Visual emphasis (glow, scale, etc.)


@dataclass
class SyncPoint:
    """A synchronization point between visual and voiceover."""

    id: str  # e.g., "numbersAppear", "windowsEntrance"
    sync_type: SyncPointType
    trigger_phrase: str  # Full phrase context, e.g., "Eighty-three point three percent"
    trigger_word: str  # Specific word to sync to, e.g., "Eighty-three"
    use_word_start: bool = True  # True = word start, False = word end
    offset_frames: int = -3  # Negative = anticipate (animation starts before word)
    visual_element: str = ""  # Description of what appears, e.g., "BigNumber component"
    notes: str = ""  # Additional context for the sync point

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sync_type": self.sync_type.value,
            "trigger_phrase": self.trigger_phrase,
            "trigger_word": self.trigger_word,
            "use_word_start": self.use_word_start,
            "offset_frames": self.offset_frames,
            "visual_element": self.visual_element,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncPoint":
        return cls(
            id=data["id"],
            sync_type=SyncPointType(data["sync_type"]),
            trigger_phrase=data["trigger_phrase"],
            trigger_word=data["trigger_word"],
            use_word_start=data.get("use_word_start", True),
            offset_frames=data.get("offset_frames", -3),
            visual_element=data.get("visual_element", ""),
            notes=data.get("notes", ""),
        )


@dataclass
class SceneSyncConfig:
    """Sync configuration for a single scene."""

    scene_id: str
    scene_title: str
    scene_file: str  # Relative path to .tsx file
    duration_seconds: float
    sync_points: list[SyncPoint] = field(default_factory=list)
    current_timing_vars: list[str] = field(default_factory=list)  # Extracted from code
    narration_text: str = ""  # Full narration text for context

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "scene_title": self.scene_title,
            "scene_file": self.scene_file,
            "duration_seconds": self.duration_seconds,
            "sync_points": [sp.to_dict() for sp in self.sync_points],
            "current_timing_vars": self.current_timing_vars,
            "narration_text": self.narration_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SceneSyncConfig":
        return cls(
            scene_id=data["scene_id"],
            scene_title=data["scene_title"],
            scene_file=data["scene_file"],
            duration_seconds=data["duration_seconds"],
            sync_points=[SyncPoint.from_dict(sp) for sp in data.get("sync_points", [])],
            current_timing_vars=data.get("current_timing_vars", []),
            narration_text=data.get("narration_text", ""),
        )


@dataclass
class SyncMap:
    """Complete sync map for a project."""

    project_id: str
    fps: int = 30
    scenes: list[SceneSyncConfig] = field(default_factory=list)
    generated_at: str = ""  # ISO timestamp
    version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "fps": self.fps,
            "scenes": [s.to_dict() for s in self.scenes],
            "generated_at": self.generated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncMap":
        return cls(
            project_id=data["project_id"],
            fps=data.get("fps", 30),
            scenes=[SceneSyncConfig.from_dict(s) for s in data.get("scenes", [])],
            generated_at=data.get("generated_at", ""),
            version=data.get("version", "1.0"),
        )

    def get_scene(self, scene_id: str) -> Optional[SceneSyncConfig]:
        """Get scene config by ID."""
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        return None


@dataclass
class SceneTimingBlock:
    """Timing constants for a single scene."""

    scene_id: str
    duration_frames: int
    timing_constants: dict[str, int] = field(default_factory=dict)  # id -> frame number
    warnings: list[str] = field(default_factory=list)  # Any issues during generation

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "duration_frames": self.duration_frames,
            "timing_constants": self.timing_constants,
            "warnings": self.warnings,
        }


@dataclass
class ProjectTiming:
    """Complete timing data for a project."""

    project_id: str
    fps: int
    scenes: list[SceneTimingBlock] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "fps": self.fps,
            "scenes": [s.to_dict() for s in self.scenes],
        }


@dataclass
class MigrationPlan:
    """Plan for migrating a scene to use centralized timing."""

    scene_id: str
    scene_file: Path
    original_code: str
    migrated_code: str
    imports_added: list[str] = field(default_factory=list)
    constants_replaced: dict[str, str] = field(default_factory=dict)  # old -> new
    success: bool = False
    error_message: Optional[str] = None
    backup_path: Optional[Path] = None

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "scene_file": str(self.scene_file),
            "imports_added": self.imports_added,
            "constants_replaced": self.constants_replaced,
            "success": self.success,
            "error_message": self.error_message,
            "backup_path": str(self.backup_path) if self.backup_path else None,
        }


class SyncStepStatus(str, Enum):
    """Status of a sync step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class SyncPhaseResult:
    """Result of the sync phase execution."""

    project_id: str
    sync_map_generated: bool = False
    timing_file_generated: bool = False
    scenes_migrated: int = 0
    total_scenes: int = 0
    sync_points_found: int = 0
    migration_results: list[MigrationPlan] = field(default_factory=list)
    sync_map_path: Optional[Path] = None
    timing_file_path: Optional[Path] = None
    success: bool = False
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "sync_map_generated": self.sync_map_generated,
            "timing_file_generated": self.timing_file_generated,
            "scenes_migrated": self.scenes_migrated,
            "total_scenes": self.total_scenes,
            "sync_points_found": self.sync_points_found,
            "migration_results": [m.to_dict() for m in self.migration_results],
            "sync_map_path": str(self.sync_map_path) if self.sync_map_path else None,
            "timing_file_path": str(self.timing_file_path) if self.timing_file_path else None,
            "success": self.success,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncPhaseResult":
        return cls(
            project_id=data["project_id"],
            sync_map_generated=data.get("sync_map_generated", False),
            timing_file_generated=data.get("timing_file_generated", False),
            scenes_migrated=data.get("scenes_migrated", 0),
            total_scenes=data.get("total_scenes", 0),
            sync_points_found=data.get("sync_points_found", 0),
            sync_map_path=Path(data["sync_map_path"]) if data.get("sync_map_path") else None,
            timing_file_path=Path(data["timing_file_path"]) if data.get("timing_file_path") else None,
            success=data.get("success", False),
            error_message=data.get("error_message"),
            warnings=data.get("warnings", []),
        )
