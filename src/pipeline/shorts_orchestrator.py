"""
Shorts Orchestrator - Evidence-based short-form video pipeline.

Extends the VideoPipeline with evidence stages for Varun Mayya style shorts:
1. Script generation (with evidence requirements)
2. URL investigation (Exa.ai search)
3. Screenshot capture (Browserbase)
4. Asset packaging (Editor)
5. Remotion rendering

Includes human-in-the-loop checkpoints at each stage.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Literal, Any

from ..config import Config, load_config
from ..models import Script, ShortsProject
from ..script.generator import ScriptGenerator
from ..agents.investigator import Investigator
from ..agents.witness import Witness
from ..agents.editor import Editor


@dataclass
class ApprovalCheckpoint:
    """
    A human-in-the-loop checkpoint requiring user approval.
    
    Used to pause the pipeline and get user confirmation before proceeding.
    """
    
    stage: str
    data: dict
    status: Literal["pending", "approved", "rejected"] = "pending"
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None


@dataclass
class ShortsResult:
    """Result of the shorts generation pipeline."""
    
    success: bool
    project: ShortsProject
    checkpoints: list[ApprovalCheckpoint] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "project_id": self.project.project_id,
            "status": self.project.status,
            "error_message": self.error_message,
            "checkpoints": [
                {
                    "stage": cp.stage,
                    "status": cp.status,
                    "approved_at": cp.approved_at.isoformat() if cp.approved_at else None,
                }
                for cp in self.checkpoints
            ],
        }


class ShortsOrchestrator:
    """
    Orchestrates the full shorts video production pipeline.
    
    Pipeline stages:
    1. generate_script - Create script with evidence requirements
    2. investigate - Find URLs for evidence scenes
    3. capture - Take screenshots of evidence
    4. package - Create render manifest
    5. render - Generate final video
    
    Each stage has a HITL checkpoint for user approval.
    """
    
    def __init__(
        self,
        config: Config | None = None,
        output_dir: Path | str = "output",
        approval_callback: Optional[Callable[[ApprovalCheckpoint], bool]] = None,
    ):
        """
        Initialize the shorts orchestrator.
        
        Args:
            config: Configuration object. If None, loads from config.yaml.
            output_dir: Directory for output files.
            approval_callback: Callback for HITL checkpoints. If None, auto-approves.
        """
        self.config = config or load_config()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # HITL callback - if not provided, auto-approve (for testing)
        self._approval_callback = approval_callback or (lambda cp: True)
        
        # Initialize components (lazy-loaded)
        self._script_gen: Optional[ScriptGenerator] = None
        self._investigator: Optional[Investigator] = None
        self._witness: Optional[Witness] = None
        self._editor: Optional[Editor] = None
        
        # Progress callback
        self._progress_callback: Optional[Callable[[str, float, dict], None]] = None
    
    @property
    def script_gen(self) -> ScriptGenerator:
        """Lazy-load script generator."""
        if self._script_gen is None:
            self._script_gen = ScriptGenerator(self.config)
        return self._script_gen
    
    @property
    def investigator(self) -> Investigator:
        """Lazy-load investigator."""
        if self._investigator is None:
            self._investigator = Investigator()
        return self._investigator
    
    @property
    def witness(self) -> Witness:
        """Lazy-load witness."""
        if self._witness is None:
            self._witness = Witness()
        return self._witness
    
    @property
    def editor(self) -> Editor:
        """Lazy-load editor."""
        if self._editor is None:
            self._editor = Editor()
        return self._editor
    
    def set_progress_callback(
        self,
        callback: Callable[[str, float, dict], None]
    ) -> None:
        """
        Set a callback for progress updates.
        
        Args:
            callback: Function that receives (stage_name, progress_percent, data)
        """
        self._progress_callback = callback
    
    def _report_progress(self, stage: str, progress: float, data: dict = None) -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(stage, progress, data or {})
    
    def _create_checkpoint(self, stage: str, data: dict) -> ApprovalCheckpoint:
        """Create a checkpoint and get approval."""
        checkpoint = ApprovalCheckpoint(stage=stage, data=data)
        
        # Call approval callback
        approved = self._approval_callback(checkpoint)
        
        if approved:
            checkpoint.status = "approved"
            checkpoint.approved_at = datetime.now()
        else:
            checkpoint.status = "rejected"
        
        return checkpoint
    
    async def generate_short(
        self,
        topic: str,
        duration_seconds: int = 45,
        evidence_urls: list[str] | None = None,
        style: str = "varun_mayya",
    ) -> ShortsResult:
        """
        Generate a complete short-form video from a topic.
        
        Full pipeline with HITL checkpoints:
        1. Generate script -> [CHECKPOINT: Approve script]
        2. Investigate URLs -> [CHECKPOINT: Approve search queries]
        3. Capture screenshots -> [CHECKPOINT: Approve screenshots]
        4. Package for render -> [CHECKPOINT: Approve manifest]
        
        Args:
            topic: The topic or claim to create a short about
            duration_seconds: Target duration (15-60 seconds)
            evidence_urls: Optional URLs to use as evidence
            style: Style preset (varun_mayya, johnny_harris, generic)
        
        Returns:
            ShortsResult with project state and checkpoints.
        """
        project_id = f"short_{uuid.uuid4().hex[:8]}"
        project_dir = self.output_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        project = ShortsProject(
            project_id=project_id,
            topic=topic,
            style=style,
            duration_seconds=duration_seconds,
            evidence_urls=evidence_urls or [],
        )
        
        checkpoints: list[ApprovalCheckpoint] = []
        
        try:
            # Stage 1: Generate Script
            self._report_progress("script", 0, {"topic": topic})
            project.status = "scripted"
            project.current_stage = "script"
            
            script = self.script_gen.generate_short(
                topic=topic,
                duration_seconds=duration_seconds,
                evidence_urls=evidence_urls,
                style=style,
            )
            project.script = script
            
            # Save script
            script_path = project_dir / "script.json"
            with open(script_path, "w") as f:
                json.dump(script.model_dump(), f, indent=2)
            
            self._report_progress("script", 100, {"script": script.model_dump()})
            
            # CHECKPOINT 1: Approve script
            checkpoint = self._create_checkpoint("script", {
                "script": script.model_dump(),
                "scene_count": len(script.scenes),
                "total_duration": script.total_duration_seconds,
            })
            checkpoints.append(checkpoint)
            
            if checkpoint.status == "rejected":
                project.status = "error"
                project.error_message = "Script rejected by user"
                return ShortsResult(
                    success=False,
                    project=project,
                    checkpoints=checkpoints,
                    error_message="Script rejected",
                )
            
            # Stage 2: Investigate URLs
            # (For now, we'll skip this stage if evidence_urls are provided)
            # TODO: Implement async investigation
            
            # Stage 3: Capture Screenshots
            # (Skip for mock mode - will be implemented with actual capture)
            
            # Stage 4: Package for render
            self._report_progress("package", 0)
            project.status = "editing"
            project.current_stage = "edit"
            
            # Create render manifest
            render_manifest = self._create_render_manifest(project, project_dir)
            project.render_manifest = render_manifest
            
            # Save manifest
            manifest_path = project_dir / "render_manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(render_manifest, f, indent=2)
            
            self._report_progress("package", 100, {"manifest": render_manifest})
            
            # CHECKPOINT 2: Approve manifest
            checkpoint = self._create_checkpoint("manifest", {
                "manifest": render_manifest,
                "scene_count": len(render_manifest.get("render_queue", [])),
            })
            checkpoints.append(checkpoint)
            
            if checkpoint.status == "rejected":
                project.status = "error"
                project.error_message = "Manifest rejected by user"
                return ShortsResult(
                    success=False,
                    project=project,
                    checkpoints=checkpoints,
                    error_message="Manifest rejected",
                )
            
            # Mark complete
            project.status = "complete"
            project.current_stage = "done"
            
            return ShortsResult(
                success=True,
                project=project,
                checkpoints=checkpoints,
            )
            
        except Exception as e:
            project.status = "error"
            project.error_message = str(e)
            return ShortsResult(
                success=False,
                project=project,
                checkpoints=checkpoints,
                error_message=str(e),
            )
    
    def _create_render_manifest(
        self,
        project: ShortsProject,
        project_dir: Path,
    ) -> dict:
        """Create a render manifest from the project state."""
        if not project.script:
            return {}
        
        render_queue = []
        for scene in project.script.scenes:
            render_queue.append({
                "scene_id": scene.scene_id,
                "scene_type": scene.scene_type,
                "duration_seconds": scene.duration_seconds,
                "voiceover": scene.voiceover,
                "visual": {
                    "type": scene.visual_cue.visual_type,
                    "description": scene.visual_cue.description,
                },
            })
        
        return {
            "project_id": project.project_id,
            "topic": project.topic,
            "style": project.style,
            "resolution": project.resolution,
            "total_duration_seconds": project.script.total_duration_seconds,
            "scene_count": len(render_queue),
            "render_queue": render_queue,
            "output_dir": str(project_dir),
        }
    
    async def generate_with_mock(
        self,
        topic: str,
        duration_seconds: int = 45,
        mock_script: dict | None = None,
    ) -> ShortsResult:
        """
        Generate a short using mock data (for testing HITL flow).
        
        Uses pre-baked responses instead of real LLM calls.
        
        Args:
            topic: The topic (used for project naming)
            duration_seconds: Target duration
            mock_script: Optional mock script data. If None, uses fixture.
        
        Returns:
            ShortsResult with mock data and checkpoints.
        """
        project_id = f"mock_{uuid.uuid4().hex[:8]}"
        project_dir = self.output_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        project = ShortsProject(
            project_id=project_id,
            topic=topic,
            duration_seconds=duration_seconds,
        )
        
        checkpoints: list[ApprovalCheckpoint] = []
        
        # Use mock script or load from fixture
        if mock_script is None:
            mock_script = self._get_mock_script(topic, duration_seconds)
        
        # Create Script from mock data
        from ..models import Script, ScriptScene, VisualCue
        
        scenes = []
        for s in mock_script.get("scenes", []):
            visual_cue = VisualCue(
                description=s.get("visual_description", ""),
                visual_type=s.get("visual_type", "full_avatar"),
                elements=[],
                duration_seconds=s.get("duration_seconds", 5.0),
            )
            scene = ScriptScene(
                scene_id=str(s.get("scene_id", 1)),
                scene_type=s.get("role", "evidence"),
                title=f"Scene {s.get('scene_id', 1)}",
                voiceover=s.get("voiceover", ""),
                visual_cue=visual_cue,
                duration_seconds=s.get("duration_seconds", 5.0),
                needs_evidence=s.get("needs_evidence", False),
            )
            scenes.append(scene)
        
        script = Script(
            title=mock_script.get("project_title", topic),
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            source_document=f"mock:{topic}",
        )
        project.script = script
        project.status = "scripted"
        
        # CHECKPOINT 1: Script
        checkpoint = self._create_checkpoint("script", {
            "script": script.model_dump(),
            "scene_count": len(scenes),
            "mock_mode": True,
        })
        checkpoints.append(checkpoint)
        
        if checkpoint.status == "rejected":
            project.status = "error"
            return ShortsResult(
                success=False,
                project=project,
                checkpoints=checkpoints,
                error_message="Mock script rejected",
            )
        
        # Create manifest
        project.render_manifest = self._create_render_manifest(project, project_dir)
        project.status = "complete"
        
        return ShortsResult(
            success=True,
            project=project,
            checkpoints=checkpoints,
        )
    
    def _get_mock_script(self, topic: str, duration: int) -> dict:
        """Get a mock script for testing."""
        return {
            "project_title": f"Mock: {topic[:30]}",
            "scenes": [
                {
                    "scene_id": 1,
                    "role": "hook",
                    "voiceover": "This is going to blow your mind.",
                    "visual_type": "full_avatar",
                    "visual_description": "Avatar with bold text overlay",
                    "needs_evidence": False,
                    "duration_seconds": 3.0,
                },
                {
                    "scene_id": 2,
                    "role": "evidence",
                    "voiceover": "Look at this. The proof is right here.",
                    "visual_type": "static_highlight",
                    "visual_description": "Screenshot of the main claim",
                    "needs_evidence": True,
                    "duration_seconds": 5.0,
                },
                {
                    "scene_id": 3,
                    "role": "analysis",
                    "voiceover": "And here's why this matters to you.",
                    "visual_type": "full_avatar",
                    "visual_description": "Avatar explaining implications",
                    "needs_evidence": False,
                    "duration_seconds": 5.0,
                },
                {
                    "scene_id": 4,
                    "role": "conclusion",
                    "voiceover": "Follow for more insights like this.",
                    "visual_type": "full_avatar",
                    "visual_description": "Avatar with CTA text",
                    "needs_evidence": False,
                    "duration_seconds": 3.0,
                },
            ],
        }
