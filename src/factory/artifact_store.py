"""
Artifact Store - Canonical store for all pipeline outputs.

All agents write to this single store. No agent holds state internally.
The store tracks draft vs locked artifacts, enabling approval workflows.

Key concepts:
- Draft: Artifact can be modified, not yet approved
- Locked: Artifact is approved and immutable, ready for render
- Version: Each modification creates a new version (audit trail)
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Literal
from uuid import uuid4


class ArtifactType(str, Enum):
    """Types of artifacts produced by the pipeline."""
    
    # Script artifacts
    SCRIPT = "script"                    # Full script.json
    SCENE = "scene"                      # Individual scene data
    
    # Evidence artifacts  
    EVIDENCE_URL = "evidence_url"        # Verified URL from Investigator
    SEARCH_QUERY = "search_query"        # Exa.ai search query
    
    # Capture artifacts
    SCREENSHOT = "screenshot"            # Single screenshot file
    SCREENSHOT_BUNDLE = "screenshot_bundle"  # Bundle of 5 variants
    RECORDING = "recording"              # Scroll recording video
    
    # Render artifacts
    RENDER_MANIFEST = "render_manifest"  # Locked render spec
    RENDERED_SCENE = "rendered_scene"    # Individual scene video
    FINAL_VIDEO = "final_video"          # Final composed video
    
    # Analysis artifacts
    HOOK_ANALYSIS = "hook_analysis"
    BEAT_SHEET = "beat_sheet"
    RETENTION_SCORE = "retention_score"


@dataclass
class Artifact:
    """
    A single artifact in the store.
    
    Artifacts are immutable once locked. Modifications create new versions.
    """
    
    id: str
    type: ArtifactType
    scene_id: Optional[str]  # Which scene this belongs to (None for project-level)
    
    # Content
    data: dict[str, Any]     # Structured data (JSON-serializable)
    file_path: Optional[str]  # Path to file (for screenshots, videos)
    
    # State
    status: Literal["draft", "locked"] = "draft"
    version: int = 1
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "unknown"  # Which agent created this
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None  # Who approved (user_id or "auto")
    
    # Audit
    previous_version_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "scene_id": self.scene_id,
            "data": self.data,
            "file_path": self.file_path,
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "locked_by": self.locked_by,
            "previous_version_id": self.previous_version_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Artifact":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=ArtifactType(data["type"]),
            scene_id=data.get("scene_id"),
            data=data.get("data", {}),
            file_path=data.get("file_path"),
            status=data.get("status", "draft"),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            created_by=data.get("created_by", "unknown"),
            locked_at=datetime.fromisoformat(data["locked_at"]) if data.get("locked_at") else None,
            locked_by=data.get("locked_by"),
            previous_version_id=data.get("previous_version_id"),
        )


class ArtifactStore:
    """
    Canonical store for all pipeline artifacts.
    
    All agents MUST write outputs here. No internal state.
    
    Features:
    - Draft/Locked lifecycle
    - Version history
    - Scene-scoped and project-scoped artifacts
    - File management (screenshots, videos)
    - JSON persistence
    """
    
    def __init__(self, project_dir: Path | str):
        """
        Initialize the artifact store.
        
        Args:
            project_dir: Root directory for this project's artifacts.
        """
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        self.artifacts_dir = self.project_dir / "artifacts"
        self.files_dir = self.project_dir / "files"
        self.artifacts_dir.mkdir(exist_ok=True)
        self.files_dir.mkdir(exist_ok=True)
        
        # In-memory index (loaded from disk)
        self._artifacts: dict[str, Artifact] = {}
        self._index_path = self.project_dir / "artifact_index.json"
        
        # Load existing artifacts
        self._load_index()
    
    def _load_index(self) -> None:
        """Load artifact index from disk."""
        if self._index_path.exists():
            with open(self._index_path) as f:
                data = json.load(f)
            for artifact_data in data.get("artifacts", []):
                artifact = Artifact.from_dict(artifact_data)
                self._artifacts[artifact.id] = artifact
    
    def _save_index(self) -> None:
        """Save artifact index to disk."""
        data = {
            "artifacts": [a.to_dict() for a in self._artifacts.values()],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self._index_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def put(
        self,
        type: ArtifactType,
        data: dict[str, Any],
        scene_id: Optional[str] = None,
        file_path: Optional[str] = None,
        created_by: str = "unknown",
    ) -> Artifact:
        """
        Store a new artifact (always as draft).
        
        Args:
            type: Type of artifact
            data: Structured data (JSON-serializable)
            scene_id: Scene this belongs to (None for project-level)
            file_path: Path to associated file (will be copied to store)
            created_by: Agent that created this artifact
        
        Returns:
            The created Artifact.
        """
        artifact_id = f"{type.value}_{uuid4().hex[:8]}"
        
        # Copy file to store if provided
        stored_file_path = None
        if file_path and os.path.exists(file_path):
            ext = Path(file_path).suffix
            stored_file_path = str(self.files_dir / f"{artifact_id}{ext}")
            shutil.copy2(file_path, stored_file_path)
        
        artifact = Artifact(
            id=artifact_id,
            type=type,
            scene_id=scene_id,
            data=data,
            file_path=stored_file_path,
            status="draft",
            version=1,
            created_by=created_by,
        )
        
        self._artifacts[artifact_id] = artifact
        self._save_index()
        
        return artifact
    
    def update(
        self,
        artifact_id: str,
        data: dict[str, Any],
        updated_by: str = "unknown",
    ) -> Artifact:
        """
        Update a draft artifact (creates new version).
        
        Cannot update locked artifacts.
        
        Args:
            artifact_id: ID of artifact to update
            data: New data (replaces existing)
            updated_by: Agent making the update
        
        Returns:
            The new version of the artifact.
        
        Raises:
            ValueError: If artifact is locked or not found.
        """
        if artifact_id not in self._artifacts:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        old_artifact = self._artifacts[artifact_id]
        
        if old_artifact.status == "locked":
            raise ValueError(f"Cannot update locked artifact {artifact_id}")
        
        # Create new version
        new_id = f"{old_artifact.type.value}_{uuid4().hex[:8]}"
        new_artifact = Artifact(
            id=new_id,
            type=old_artifact.type,
            scene_id=old_artifact.scene_id,
            data=data,
            file_path=old_artifact.file_path,
            status="draft",
            version=old_artifact.version + 1,
            created_by=updated_by,
            previous_version_id=artifact_id,
        )
        
        self._artifacts[new_id] = new_artifact
        self._save_index()
        
        return new_artifact
    
    def lock(
        self,
        artifact_id: str,
        locked_by: str = "user",
    ) -> Artifact:
        """
        Lock an artifact (mark as approved, immutable).
        
        Args:
            artifact_id: ID of artifact to lock
            locked_by: Who approved (user_id or "auto")
        
        Returns:
            The locked artifact.
        
        Raises:
            ValueError: If artifact not found or already locked.
        """
        if artifact_id not in self._artifacts:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        artifact = self._artifacts[artifact_id]
        
        if artifact.status == "locked":
            return artifact  # Already locked, no-op
        
        artifact.status = "locked"
        artifact.locked_at = datetime.now()
        artifact.locked_by = locked_by
        
        self._save_index()
        return artifact
    
    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Get an artifact by ID."""
        return self._artifacts.get(artifact_id)
    
    def get_by_type(
        self,
        type: ArtifactType,
        scene_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[Artifact]:
        """
        Get artifacts by type, optionally filtered by scene and status.
        
        Args:
            type: Artifact type to filter by
            scene_id: Optional scene ID filter
            status: Optional status filter ("draft" or "locked")
        
        Returns:
            List of matching artifacts.
        """
        results = []
        for artifact in self._artifacts.values():
            if artifact.type != type:
                continue
            if scene_id is not None and artifact.scene_id != scene_id:
                continue
            if status is not None and artifact.status != status:
                continue
            results.append(artifact)
        return results
    
    def get_latest(
        self,
        type: ArtifactType,
        scene_id: Optional[str] = None,
    ) -> Optional[Artifact]:
        """Get the latest version of an artifact type."""
        artifacts = self.get_by_type(type, scene_id)
        if not artifacts:
            return None
        return max(artifacts, key=lambda a: a.version)
    
    def get_locked_script(self) -> Optional[Artifact]:
        """Get the locked script artifact (required for render)."""
        locked = self.get_by_type(ArtifactType.SCRIPT, status="locked")
        return locked[0] if locked else None
    
    def get_locked_screenshots(self) -> list[Artifact]:
        """Get all locked screenshot artifacts."""
        return self.get_by_type(ArtifactType.SCREENSHOT, status="locked")
    
    def is_render_ready(self) -> tuple[bool, list[str]]:
        """
        Check if all required artifacts are locked for render.
        
        Returns:
            (ready, missing_items) tuple.
        """
        missing = []
        
        # Must have locked script
        if not self.get_locked_script():
            missing.append("Locked script required")
        
        # Check each scene has locked evidence (if needed)
        script = self.get_locked_script()
        if script:
            for scene in script.data.get("scenes", []):
                if scene.get("needs_evidence"):
                    scene_id = scene.get("scene_id")
                    screenshots = self.get_by_type(
                        ArtifactType.SCREENSHOT,
                        scene_id=str(scene_id),
                        status="locked"
                    )
                    if not screenshots:
                        missing.append(f"Locked screenshot for scene {scene_id}")
        
        return len(missing) == 0, missing
    
    def get_render_manifest(self) -> Optional[dict]:
        """
        Generate render manifest from locked artifacts.
        
        Only returns manifest if all required artifacts are locked.
        
        Returns:
            Render manifest dict or None if not ready.
        """
        ready, missing = self.is_render_ready()
        if not ready:
            return None
        
        script = self.get_locked_script()
        if not script:
            return None
        
        render_queue = []
        for scene in script.data.get("scenes", []):
            scene_id = str(scene.get("scene_id"))
            
            # Get locked screenshot for this scene
            screenshots = self.get_by_type(
                ArtifactType.SCREENSHOT,
                scene_id=scene_id,
                status="locked"
            )
            screenshot_path = screenshots[0].file_path if screenshots else None
            
            render_queue.append({
                "scene_id": scene_id,
                "voiceover": scene.get("voiceover"),
                "visual_type": scene.get("visual_type"),
                "screenshot_path": screenshot_path,
                "duration_seconds": scene.get("duration_seconds", 5),
                "locked": True,
            })
        
        return {
            "project_dir": str(self.project_dir),
            "script_version": script.version,
            "locked_at": script.locked_at.isoformat() if script.locked_at else None,
            "render_queue": render_queue,
        }
    
    def list_all(self) -> list[Artifact]:
        """List all artifacts in the store."""
        return list(self._artifacts.values())
    
    def summary(self) -> dict:
        """Get a summary of the store state."""
        by_type = {}
        for artifact in self._artifacts.values():
            key = artifact.type.value
            if key not in by_type:
                by_type[key] = {"draft": 0, "locked": 0}
            by_type[key][artifact.status] += 1
        
        ready, missing = self.is_render_ready()
        
        return {
            "project_dir": str(self.project_dir),
            "total_artifacts": len(self._artifacts),
            "by_type": by_type,
            "render_ready": ready,
            "missing_for_render": missing,
        }
