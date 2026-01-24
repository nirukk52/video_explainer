"""
Director State Machine - The brain/orchestrator for the Shorts Factory.

The Director holds the main state and orchestrates the entire pipeline.
Each state represents a phase in video production.

Pipeline flow:
    IDLE → DRAFTING → AWAITING_CAPTURE → REVIEWING → 
    FINALIZING → AWAITING_AUDIO → AWAITING_AVATAR → 
    READY_FOR_RENDER → RENDERING → COMPLETE
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any
import json


class DirectorPhase(str, Enum):
    """
    Production phases the Director moves through.
    
    Each phase has specific inputs, outputs, and completion criteria.
    """
    
    # === Pre-production ===
    IDLE = "idle"
    """Not started. Waiting for topic/brief."""
    
    DRAFTING = "drafting"
    """Director creating initial script with asset requirements.
    Input: Topic, URLs, duration
    Output: Draft script.json with assets_needed section
    """
    
    # === Asset Capture ===
    AWAITING_CAPTURE = "awaiting_capture"
    """Waiting for Witness agent to capture evidence.
    Input: assets_needed from script
    Output: evidence/manifest.json with captured files
    """
    
    REVIEWING = "reviewing"
    """Director reviewing captured assets.
    Input: Evidence manifest
    Output: Asset approval/rejection decisions
    """
    
    # === Script Finalization ===
    FINALIZING = "finalizing"
    """Director mapping captured assets to scenes.
    Input: Approved assets + draft script
    Output: Final script.json with real paths
    """
    
    # === Audio Production ===
    AWAITING_AUDIO = "awaiting_audio"
    """Waiting for TTS generation.
    Input: Final script.json
    Output: audio/voiceover.mp3 + word_timestamps
    """
    
    # === Avatar Production ===
    AWAITING_AVATAR = "awaiting_avatar"  
    """Waiting for avatar clip generation.
    Input: Audio + script with avatar scenes
    Output: avatar/*.mp4 clips
    """
    
    # === Render ===
    READY_FOR_RENDER = "ready_for_render"
    """All assets ready, awaiting human approval to render.
    Input: Complete script + all assets
    Output: Human approval
    """
    
    RENDERING = "rendering"
    """Remotion render in progress.
    Input: Approved script + assets
    Output: output/short.mp4
    """
    
    # === Terminal States ===
    COMPLETE = "complete"
    """Video rendered successfully."""
    
    ERROR = "error"
    """Pipeline failed. See error_message for details."""
    
    CANCELLED = "cancelled"
    """Production cancelled by user."""


@dataclass
class AssetStatus:
    """Status of a single asset (background, evidence, avatar clip)."""
    
    id: str
    """Asset identifier (e.g., 'drone_swarm.mp4')"""
    
    asset_type: str
    """Type: 'background', 'evidence', 'avatar'"""
    
    status: str = "pending"
    """Status: 'pending', 'capturing', 'captured', 'approved', 'rejected', 'failed'"""
    
    file_path: Optional[str] = None
    """Path to captured file (relative to project root)"""
    
    error: Optional[str] = None
    """Error message if failed"""
    
    metadata: dict = field(default_factory=dict)
    """Additional metadata (dimensions, duration, etc.)"""


@dataclass
class DirectorState:
    """
    Complete state of the Director for a project.
    
    This is the single source of truth for:
    - Where we are in the pipeline (phase)
    - What assets we need and their status
    - Script versions (draft → final)
    - Errors and progress
    """
    
    # === Identity ===
    project_id: str
    """Unique project identifier"""
    
    project_dir: Path
    """Root directory for project files"""
    
    # === Current Phase ===
    phase: DirectorPhase = DirectorPhase.IDLE
    """Current production phase"""
    
    phase_started_at: Optional[datetime] = None
    """When current phase started"""
    
    # === Topic/Brief ===
    topic: str = ""
    """Video topic/brief"""
    
    duration_seconds: int = 6
    """Target video duration"""
    
    evidence_urls: list[str] = field(default_factory=list)
    """URLs to investigate for evidence"""
    
    # === Script Versions ===
    draft_script: Optional[dict] = None
    """Initial script with assets_needed (Phase 1 output)"""
    
    final_script: Optional[dict] = None
    """Render-ready script with real paths (Phase 2 output)"""
    
    # === Asset Tracking ===
    assets: list[AssetStatus] = field(default_factory=list)
    """All assets and their capture status"""
    
    # === Audio ===
    audio_file: Optional[str] = None
    """Path to generated voiceover"""
    
    word_timestamps: Optional[list[dict]] = None
    """Word-level timing from TTS"""
    
    # === Errors & History ===
    error_message: Optional[str] = None
    """Error message if phase == ERROR"""
    
    history: list[dict] = field(default_factory=list)
    """Phase transition history"""
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # === Methods ===
    
    def transition_to(self, new_phase: DirectorPhase, reason: str = "") -> None:
        """
        Transition to a new phase.
        
        Records the transition in history and updates timestamps.
        """
        self.history.append({
            "from": self.phase.value,
            "to": new_phase.value,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        self.phase = new_phase
        self.phase_started_at = datetime.now()
        self.updated_at = datetime.now()
    
    def set_error(self, message: str) -> None:
        """Transition to ERROR state with message."""
        self.error_message = message
        self.transition_to(DirectorPhase.ERROR, message)
    
    def get_pending_assets(self) -> list[AssetStatus]:
        """Get assets that haven't been captured yet."""
        return [a for a in self.assets if a.status == "pending"]
    
    def get_captured_assets(self) -> list[AssetStatus]:
        """Get assets that have been captured (pending approval)."""
        return [a for a in self.assets if a.status == "captured"]
    
    def get_approved_assets(self) -> list[AssetStatus]:
        """Get assets that have been approved."""
        return [a for a in self.assets if a.status == "approved"]
    
    def all_assets_captured(self) -> bool:
        """Check if all assets have been captured (or failed)."""
        return all(a.status in ("captured", "approved", "rejected", "failed") for a in self.assets)
    
    def all_assets_approved(self) -> bool:
        """Check if all required assets are approved."""
        required = [a for a in self.assets if a.status != "rejected"]
        return all(a.status == "approved" for a in required)
    
    def is_ready_for_render(self) -> tuple[bool, list[str]]:
        """
        Check if project is ready for render.
        
        Returns (ready, missing_items).
        """
        missing = []
        
        if self.final_script is None:
            missing.append("final_script")
        
        if self.audio_file is None:
            missing.append("audio_file")
        
        # Check avatar clips for scenes that need them
        if self.final_script:
            for scene in self.final_script.get("scenes", []):
                if scene.get("avatar", {}).get("visible"):
                    avatar_src = scene.get("avatar", {}).get("src")
                    if avatar_src:
                        avatar_path = self.project_dir / avatar_src
                        if not avatar_path.exists():
                            missing.append(f"avatar:{avatar_src}")
        
        return len(missing) == 0, missing
    
    def to_dict(self) -> dict:
        """Serialize state to dictionary."""
        return {
            "project_id": self.project_id,
            "project_dir": str(self.project_dir),
            "phase": self.phase.value,
            "phase_started_at": self.phase_started_at.isoformat() if self.phase_started_at else None,
            "topic": self.topic,
            "duration_seconds": self.duration_seconds,
            "evidence_urls": self.evidence_urls,
            "draft_script": self.draft_script,
            "final_script": self.final_script,
            "assets": [
                {
                    "id": a.id,
                    "asset_type": a.asset_type,
                    "status": a.status,
                    "file_path": a.file_path,
                    "error": a.error,
                    "metadata": a.metadata
                }
                for a in self.assets
            ],
            "audio_file": self.audio_file,
            "error_message": self.error_message,
            "history": self.history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def save(self) -> Path:
        """Save state to project directory."""
        state_path = self.project_dir / ".director_state.json"
        with open(state_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return state_path
    
    @classmethod
    def load(cls, project_dir: Path) -> "DirectorState":
        """Load state from project directory."""
        state_path = project_dir / ".director_state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"No director state found at {state_path}")
        
        with open(state_path) as f:
            data = json.load(f)
        
        state = cls(
            project_id=data["project_id"],
            project_dir=Path(data["project_dir"]),
        )
        state.phase = DirectorPhase(data["phase"])
        state.topic = data.get("topic", "")
        state.duration_seconds = data.get("duration_seconds", 6)
        state.evidence_urls = data.get("evidence_urls", [])
        state.draft_script = data.get("draft_script")
        state.final_script = data.get("final_script")
        state.audio_file = data.get("audio_file")
        state.error_message = data.get("error_message")
        state.history = data.get("history", [])
        
        # Load assets
        for a in data.get("assets", []):
            state.assets.append(AssetStatus(
                id=a["id"],
                asset_type=a["asset_type"],
                status=a["status"],
                file_path=a.get("file_path"),
                error=a.get("error"),
                metadata=a.get("metadata", {})
            ))
        
        return state
    
    @classmethod
    def create(cls, project_id: str, project_dir: Path, topic: str, duration_seconds: int = 6) -> "DirectorState":
        """Create a new Director state for a project."""
        state = cls(
            project_id=project_id,
            project_dir=project_dir,
            topic=topic,
            duration_seconds=duration_seconds,
        )
        state.transition_to(DirectorPhase.IDLE, "Created")
        return state


# =============================================================================
# Phase Transition Rules
# =============================================================================

VALID_TRANSITIONS = {
    DirectorPhase.IDLE: [DirectorPhase.DRAFTING, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.DRAFTING: [DirectorPhase.AWAITING_CAPTURE, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.AWAITING_CAPTURE: [DirectorPhase.REVIEWING, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.REVIEWING: [DirectorPhase.AWAITING_CAPTURE, DirectorPhase.FINALIZING, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.FINALIZING: [DirectorPhase.AWAITING_AUDIO, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.AWAITING_AUDIO: [DirectorPhase.AWAITING_AVATAR, DirectorPhase.READY_FOR_RENDER, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.AWAITING_AVATAR: [DirectorPhase.READY_FOR_RENDER, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.READY_FOR_RENDER: [DirectorPhase.RENDERING, DirectorPhase.ERROR, DirectorPhase.CANCELLED],
    DirectorPhase.RENDERING: [DirectorPhase.COMPLETE, DirectorPhase.ERROR],
    DirectorPhase.COMPLETE: [],  # Terminal
    DirectorPhase.ERROR: [DirectorPhase.IDLE],  # Can restart
    DirectorPhase.CANCELLED: [DirectorPhase.IDLE],  # Can restart
}


def can_transition(from_phase: DirectorPhase, to_phase: DirectorPhase) -> bool:
    """Check if a phase transition is valid."""
    return to_phase in VALID_TRANSITIONS.get(from_phase, [])
