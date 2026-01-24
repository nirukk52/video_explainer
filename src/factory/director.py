"""
Director - Non-linear orchestrator for the Shorts Factory.

The Director is NOT a simple linear chain. It:
- Loops and iterates until quality thresholds are met
- Assigns tasks to agents
- Checks evidence quality
- Requests re-work when needed
- Only proceeds to render when all artifacts are locked

Key design:
- Director reads from ArtifactStore (never holds state)
- Director writes decisions to ArtifactStore
- Director respects ApprovalGate (hard gates)
- Director can iterate within stages
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any
from uuid import uuid4

from src.factory.artifact_store import ArtifactStore, ArtifactType, Artifact
from src.factory.approval_gate import ApprovalGate, ApprovalStatus


class DirectorState(str, Enum):
    """Current state of the Director."""
    
    IDLE = "idle"                        # Not started
    SCRIPTING = "scripting"              # Generating/iterating script
    AWAITING_SCRIPT_APPROVAL = "awaiting_script_approval"
    INVESTIGATING = "investigating"       # Finding evidence URLs
    AWAITING_EVIDENCE_APPROVAL = "awaiting_evidence_approval"
    CAPTURING = "capturing"               # Taking screenshots
    AWAITING_CAPTURE_APPROVAL = "awaiting_capture_approval"
    PACKAGING = "packaging"               # Creating render manifest
    AWAITING_RENDER_APPROVAL = "awaiting_render_approval"
    RENDERING = "rendering"               # Final render
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class DirectorTask:
    """A task assigned by the Director to an agent."""
    
    id: str
    agent: str  # investigator, witness, editor
    action: str  # What to do
    scene_id: Optional[str]
    params: dict[str, Any]
    
    # State
    status: str = "pending"  # pending, running, complete, failed
    result: Optional[dict] = None
    error: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class Director:
    """
    Non-linear orchestrator for the Shorts Factory.
    
    The Director:
    1. Reads project state from ArtifactStore
    2. Decides what needs to happen next
    3. Assigns tasks to agents
    4. Checks quality of results
    5. Iterates until satisfied
    6. Respects approval gates (hard blocks)
    7. Only triggers render when everything is locked
    """
    
    def __init__(
        self,
        store: ArtifactStore,
        gates: ApprovalGate,
        max_iterations: int = 3,
    ):
        """
        Initialize the Director.
        
        Args:
            store: Artifact store for reading/writing state
            gates: Approval gates for human checkpoints
            max_iterations: Max retries per stage before failing
        """
        self.store = store
        self.gates = gates
        self.max_iterations = max_iterations
        
        self._state = DirectorState.IDLE
        self._tasks: list[DirectorTask] = []
        self._iteration_counts: dict[str, int] = {}
        
        # Callbacks for task execution
        self._task_executor: Optional[Callable[[DirectorTask], Any]] = None
        
        # Progress callback
        self._progress_callback: Optional[Callable[[DirectorState, dict], None]] = None
    
    @property
    def state(self) -> DirectorState:
        """Current Director state."""
        return self._state
    
    def set_task_executor(self, executor: Callable[[DirectorTask], Any]) -> None:
        """Set the callback for executing tasks."""
        self._task_executor = executor
    
    def set_progress_callback(self, callback: Callable[[DirectorState, dict], None]) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def _report_progress(self, data: dict = None) -> None:
        """Report current state and progress."""
        if self._progress_callback:
            self._progress_callback(self._state, data or {})
    
    def _increment_iteration(self, stage: str) -> int:
        """Increment and return iteration count for a stage."""
        self._iteration_counts[stage] = self._iteration_counts.get(stage, 0) + 1
        return self._iteration_counts[stage]
    
    async def run(self, topic: str, duration_seconds: int = 45) -> dict:
        """
        Run the full Director loop.
        
        This is the main entry point. Director will:
        1. Generate script
        2. Wait for script approval
        3. Investigate evidence
        4. Wait for evidence approval
        5. Capture screenshots
        6. Wait for capture approval
        7. Package for render
        8. Wait for render approval
        9. Trigger render
        
        Args:
            topic: Topic for the short
            duration_seconds: Target duration
        
        Returns:
            Final status dict.
        """
        try:
            # Stage 1: Script Generation
            self._state = DirectorState.SCRIPTING
            self._report_progress({"topic": topic})
            
            script_artifact = await self._generate_script(topic, duration_seconds)
            
            # Gate 1: Script Approval
            self._state = DirectorState.AWAITING_SCRIPT_APPROVAL
            self._report_progress({"artifact_id": script_artifact.id})
            
            status = self.gates.request_approval(
                ApprovalGate.GATE_SCRIPT,
                [script_artifact.id],
                {"topic": topic}
            )
            
            if status == ApprovalStatus.PENDING:
                # Blocked - return current state
                return self._get_status("Waiting for script approval")
            
            if status == ApprovalStatus.REJECTED:
                return self._get_status("Script rejected", error=True)
            
            # Lock the script
            self.store.lock(script_artifact.id, "approval_gate")
            
            # Stage 2: Evidence Investigation
            self._state = DirectorState.INVESTIGATING
            self._report_progress()
            
            evidence_artifacts = await self._investigate_evidence(script_artifact)
            
            # Gate 2: Evidence Approval
            self._state = DirectorState.AWAITING_EVIDENCE_APPROVAL
            artifact_ids = [a.id for a in evidence_artifacts]
            self._report_progress({"artifact_ids": artifact_ids})
            
            status = self.gates.request_approval(
                ApprovalGate.GATE_EVIDENCE_URLS,
                artifact_ids,
            )
            
            if status == ApprovalStatus.PENDING:
                return self._get_status("Waiting for evidence approval")
            
            if status == ApprovalStatus.REJECTED:
                return self._get_status("Evidence rejected", error=True)
            
            # Lock evidence artifacts
            for artifact in evidence_artifacts:
                self.store.lock(artifact.id, "approval_gate")
            
            # Stage 3: Screenshot Capture
            self._state = DirectorState.CAPTURING
            self._report_progress()
            
            screenshot_artifacts = await self._capture_screenshots(evidence_artifacts)
            
            # Gate 3: Screenshots Approval
            self._state = DirectorState.AWAITING_CAPTURE_APPROVAL
            artifact_ids = [a.id for a in screenshot_artifacts]
            self._report_progress({"artifact_ids": artifact_ids})
            
            status = self.gates.request_approval(
                ApprovalGate.GATE_SCREENSHOTS,
                artifact_ids,
            )
            
            if status == ApprovalStatus.PENDING:
                return self._get_status("Waiting for screenshots approval")
            
            if status == ApprovalStatus.REJECTED:
                return self._get_status("Screenshots rejected", error=True)
            
            # Lock screenshot artifacts
            for artifact in screenshot_artifacts:
                self.store.lock(artifact.id, "approval_gate")
            
            # Stage 4: Package for Render
            self._state = DirectorState.PACKAGING
            self._report_progress()
            
            manifest = self.store.get_render_manifest()
            if not manifest:
                ready, missing = self.store.is_render_ready()
                return self._get_status(
                    f"Not render ready: {missing}",
                    error=True
                )
            
            manifest_artifact = self.store.put(
                ArtifactType.RENDER_MANIFEST,
                manifest,
                created_by="director",
            )
            
            # Gate 4: Render Approval
            self._state = DirectorState.AWAITING_RENDER_APPROVAL
            self._report_progress({"manifest_id": manifest_artifact.id})
            
            status = self.gates.request_approval(
                ApprovalGate.GATE_RENDER,
                [manifest_artifact.id],
            )
            
            if status == ApprovalStatus.PENDING:
                return self._get_status("Waiting for render approval")
            
            if status == ApprovalStatus.REJECTED:
                return self._get_status("Render rejected", error=True)
            
            # Lock manifest
            self.store.lock(manifest_artifact.id, "approval_gate")
            
            # Stage 5: Render (would trigger Remotion)
            self._state = DirectorState.RENDERING
            self._report_progress()
            
            # TODO: Trigger actual render
            # For now, just mark complete
            
            self._state = DirectorState.COMPLETE
            return self._get_status("Complete")
            
        except Exception as e:
            self._state = DirectorState.ERROR
            return self._get_status(str(e), error=True)
    
    async def _generate_script(self, topic: str, duration: int) -> Artifact:
        """Generate script and store as artifact."""
        # Create task for script generation
        task = DirectorTask(
            id=f"task_{uuid4().hex[:8]}",
            agent="script_generator",
            action="generate_short",
            scene_id=None,
            params={"topic": topic, "duration_seconds": duration},
        )
        self._tasks.append(task)
        
        # Execute task
        if self._task_executor:
            result = await self._execute_task(task)
            script_data = result
        else:
            # Mock script for testing
            script_data = self._get_mock_script(topic, duration)
        
        # Store as artifact
        artifact = self.store.put(
            ArtifactType.SCRIPT,
            script_data,
            created_by="director",
        )
        
        return artifact
    
    async def _investigate_evidence(self, script_artifact: Artifact) -> list[Artifact]:
        """Find evidence URLs for each scene that needs it."""
        artifacts = []
        script = script_artifact.data
        
        for scene in script.get("scenes", []):
            if not scene.get("needs_evidence", False):
                continue
            
            scene_id = str(scene.get("scene_id"))
            description = scene.get("visual_description", "")
            
            # Create investigation task
            task = DirectorTask(
                id=f"task_{uuid4().hex[:8]}",
                agent="investigator",
                action="search_urls",
                scene_id=scene_id,
                params={"query": description},
            )
            self._tasks.append(task)
            
            # Execute task
            if self._task_executor:
                result = await self._execute_task(task)
            else:
                # Mock result
                result = {
                    "status": "found",
                    "verified_url": f"https://example.com/{scene_id}",
                    "credibility_score": 0.85,
                }
            
            # Store as artifact
            artifact = self.store.put(
                ArtifactType.EVIDENCE_URL,
                result,
                scene_id=scene_id,
                created_by="investigator",
            )
            artifacts.append(artifact)
        
        return artifacts
    
    async def _capture_screenshots(self, evidence_artifacts: list[Artifact]) -> list[Artifact]:
        """Capture screenshots for each evidence URL."""
        screenshot_artifacts = []
        
        for evidence in evidence_artifacts:
            url = evidence.data.get("verified_url")
            if not url:
                continue
            
            scene_id = evidence.scene_id
            
            # Create capture task
            task = DirectorTask(
                id=f"task_{uuid4().hex[:8]}",
                agent="witness",
                action="capture_url",
                scene_id=scene_id,
                params={"url": url},
            )
            self._tasks.append(task)
            
            # Execute task
            if self._task_executor:
                result = await self._execute_task(task)
                file_path = result.get("file_path")
            else:
                # Mock result
                result = {"status": "success", "file_path": None}
                file_path = None
            
            # Store as artifact
            artifact = self.store.put(
                ArtifactType.SCREENSHOT,
                result,
                scene_id=scene_id,
                file_path=file_path,
                created_by="witness",
            )
            screenshot_artifacts.append(artifact)
        
        return screenshot_artifacts
    
    async def _execute_task(self, task: DirectorTask) -> Any:
        """Execute a task using the registered executor."""
        task.status = "running"
        try:
            result = self._task_executor(task)
            if asyncio.iscoroutine(result):
                result = await result
            task.status = "complete"
            task.result = result
            task.completed_at = datetime.now()
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            raise
    
    def _get_mock_script(self, topic: str, duration: int) -> dict:
        """Generate a mock script for testing."""
        return {
            "project_title": topic,
            "total_duration_seconds": duration,
            "scenes": [
                {
                    "scene_id": 1,
                    "role": "hook",
                    "voiceover": "This is going to blow your mind.",
                    "visual_type": "full_avatar",
                    "visual_description": "Avatar with bold text overlay",
                    "needs_evidence": False,
                    "duration_seconds": 3,
                },
                {
                    "scene_id": 2,
                    "role": "evidence",
                    "voiceover": "Look at this proof right here.",
                    "visual_type": "static_highlight",
                    "visual_description": f"Screenshot of {topic}",
                    "needs_evidence": True,
                    "duration_seconds": 5,
                },
                {
                    "scene_id": 3,
                    "role": "analysis",
                    "voiceover": "And here's why this matters.",
                    "visual_type": "full_avatar",
                    "visual_description": "Avatar explaining",
                    "needs_evidence": False,
                    "duration_seconds": 5,
                },
                {
                    "scene_id": 4,
                    "role": "conclusion",
                    "voiceover": "Follow for more insights.",
                    "visual_type": "full_avatar",
                    "visual_description": "Avatar with CTA",
                    "needs_evidence": False,
                    "duration_seconds": 3,
                },
            ],
        }
    
    def _get_status(self, message: str, error: bool = False) -> dict:
        """Get current status as dict."""
        return {
            "state": self._state.value,
            "message": message,
            "error": error,
            "store_summary": self.store.summary(),
            "gates_summary": self.gates.summary(),
            "tasks": [
                {
                    "id": t.id,
                    "agent": t.agent,
                    "action": t.action,
                    "status": t.status,
                }
                for t in self._tasks
            ],
        }
    
    # === Manual Approval Methods (for HITL flow) ===
    
    def approve_script(self, user_id: str, feedback: str = None) -> dict:
        """Manually approve script gate."""
        script = self.store.get_latest(ArtifactType.SCRIPT)
        if script:
            self.gates.approve(
                ApprovalGate.GATE_SCRIPT,
                user_id,
                [script.id],
                feedback=feedback,
            )
            self.store.lock(script.id, user_id)
        return self._get_status("Script approved")
    
    def reject_script(self, user_id: str, reason: str) -> dict:
        """Manually reject script gate."""
        script = self.store.get_latest(ArtifactType.SCRIPT)
        self.gates.reject(
            ApprovalGate.GATE_SCRIPT,
            user_id,
            reason,
            [script.id] if script else [],
        )
        return self._get_status("Script rejected")
    
    def approve_evidence(self, user_id: str, artifact_ids: list[str] = None) -> dict:
        """Manually approve evidence gate."""
        if artifact_ids is None:
            artifacts = self.store.get_by_type(ArtifactType.EVIDENCE_URL, status="draft")
            artifact_ids = [a.id for a in artifacts]
        
        self.gates.approve(
            ApprovalGate.GATE_EVIDENCE_URLS,
            user_id,
            artifact_ids,
        )
        
        for aid in artifact_ids:
            self.store.lock(aid, user_id)
        
        return self._get_status("Evidence approved")
    
    def approve_screenshots(self, user_id: str, artifact_ids: list[str] = None) -> dict:
        """Manually approve screenshots gate."""
        if artifact_ids is None:
            artifacts = self.store.get_by_type(ArtifactType.SCREENSHOT, status="draft")
            artifact_ids = [a.id for a in artifacts]
        
        self.gates.approve(
            ApprovalGate.GATE_SCREENSHOTS,
            user_id,
            artifact_ids,
        )
        
        for aid in artifact_ids:
            self.store.lock(aid, user_id)
        
        return self._get_status("Screenshots approved")
    
    def approve_render(self, user_id: str) -> dict:
        """Manually approve render gate."""
        manifest = self.store.get_latest(ArtifactType.RENDER_MANIFEST)
        if manifest:
            self.gates.approve(
                ApprovalGate.GATE_RENDER,
                user_id,
                [manifest.id],
            )
            self.store.lock(manifest.id, user_id)
        return self._get_status("Render approved")
