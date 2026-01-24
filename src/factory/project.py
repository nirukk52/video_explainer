"""
Shorts Factory Project - Main entry point for the factory.

Ties together:
- ArtifactStore: Canonical storage
- ApprovalGate: Human checkpoints  
- Director: Non-linear orchestration
- Agents: Investigator, Witness, Editor

Usage:
    project = ShortsFactoryProject.create("DeepSeek pricing crash")
    
    # Run with auto-approve (testing)
    result = await project.run_with_auto_approve()
    
    # Run with human-in-the-loop
    result = await project.run()  # Returns at first gate
    project.approve_script("user123")  # Manual approval
    result = await project.resume()  # Continue to next gate
"""

import os
from pathlib import Path
from typing import Optional, Callable, Any
from uuid import uuid4

from src.factory.artifact_store import ArtifactStore, ArtifactType
from src.factory.approval_gate import ApprovalGate, ApprovalStatus
from src.factory.director import Director, DirectorState


class ShortsFactoryProject:
    """
    High-quality Varun Mayya style shorts generator factory.
    
    This is the main entry point for creating shorts.
    
    Architecture:
    - All state in ArtifactStore (canonical)
    - Hard gates at ApprovalGate (human checkpoints)
    - Non-linear orchestration via Director
    - Only locked artifacts go to render
    """
    
    def __init__(
        self,
        project_id: str,
        topic: str,
        output_dir: Path | str = "output",
        auto_approve: bool = False,
    ):
        """
        Initialize a Shorts Factory project.
        
        Args:
            project_id: Unique project identifier
            topic: Topic/claim for the short
            output_dir: Base output directory
            auto_approve: If True, auto-approve all gates (testing)
        """
        self.project_id = project_id
        self.topic = topic
        self.auto_approve = auto_approve
        
        # Project directory
        self.project_dir = Path(output_dir) / project_id
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Core components
        self.store = ArtifactStore(self.project_dir)
        self.gates = ApprovalGate(auto_approve=auto_approve)
        self.director = Director(self.store, self.gates)
        
        # Configuration
        self.duration_seconds = 45
        self.style = "varun_mayya"
        
        # Task executor (connects agents)
        self._setup_task_executor()
    
    @classmethod
    def create(
        cls,
        topic: str,
        output_dir: Path | str = "output",
        auto_approve: bool = False,
    ) -> "ShortsFactoryProject":
        """
        Create a new Shorts Factory project.
        
        Args:
            topic: Topic/claim for the short
            output_dir: Base output directory
            auto_approve: If True, auto-approve all gates
        
        Returns:
            New ShortsFactoryProject instance.
        """
        project_id = f"short_{uuid4().hex[:8]}"
        return cls(project_id, topic, output_dir, auto_approve)
    
    @classmethod
    def load(
        cls,
        project_id: str,
        output_dir: Path | str = "output",
    ) -> "ShortsFactoryProject":
        """
        Load an existing project from disk.
        
        Args:
            project_id: Project ID to load
            output_dir: Base output directory
        
        Returns:
            Loaded ShortsFactoryProject instance.
        """
        project_dir = Path(output_dir) / project_id
        if not project_dir.exists():
            raise ValueError(f"Project {project_id} not found at {project_dir}")
        
        # Load topic from store or default
        project = cls(project_id, "Loaded project", output_dir)
        
        # Try to get topic from script artifact
        script = project.store.get_latest(ArtifactType.SCRIPT)
        if script:
            project.topic = script.data.get("project_title", project.topic)
        
        return project
    
    def _setup_task_executor(self) -> None:
        """Set up the task executor that connects to agents."""
        
        async def execute_task(task):
            """Execute a task using the appropriate agent."""
            if task.agent == "script_generator":
                return await self._execute_script_task(task)
            elif task.agent == "investigator":
                return await self._execute_investigator_task(task)
            elif task.agent == "witness":
                return await self._execute_witness_task(task)
            else:
                raise ValueError(f"Unknown agent: {task.agent}")
        
        self.director.set_task_executor(execute_task)
    
    async def _execute_script_task(self, task) -> dict:
        """Execute a script generation task."""
        from src.script.generator import ScriptGenerator
        from src.config import load_config
        
        config = load_config()
        generator = ScriptGenerator(config)
        
        script = generator.generate_short(
            topic=task.params.get("topic"),
            duration_seconds=task.params.get("duration_seconds", 45),
            style=self.style,
        )
        
        return script.model_dump()
    
    async def _execute_investigator_task(self, task) -> dict:
        """Execute an investigation task."""
        from src.agents.investigator import Investigator
        
        investigator = Investigator()
        result = await investigator.search_urls(task.params.get("query"))
        
        return {
            "status": result.status,
            "verified_url": result.verified_url,
            "fallback_urls": result.fallback_urls,
            "credibility_score": result.credibility_score,
        }
    
    async def _execute_witness_task(self, task) -> dict:
        """Execute a capture task."""
        from src.agents.witness import Witness
        
        witness = Witness()
        bundle = await witness.capture_url(
            url=task.params.get("url"),
            description=task.params.get("description", ""),
            output_dir=str(self.project_dir / "captures"),
        )
        
        return {
            "status": bundle.status,
            "file_path": bundle.element_padded_path or bundle.fullpage_path,
            "strategy_used": bundle.strategy_used,
        }
    
    # === Main API ===
    
    async def run(self) -> dict:
        """
        Run the project.
        
        Returns at the first pending approval gate.
        Call approve_* methods then resume() to continue.
        
        Returns:
            Status dict with current state.
        """
        return await self.director.run(self.topic, self.duration_seconds)
    
    async def run_with_auto_approve(self) -> dict:
        """
        Run the project with auto-approval (testing mode).
        
        All gates are automatically approved.
        
        Returns:
            Final status dict.
        """
        self.gates._auto_approve = True
        return await self.director.run(self.topic, self.duration_seconds)
    
    async def resume(self) -> dict:
        """
        Resume the project from current state.
        
        Called after manual approvals to continue processing.
        
        Returns:
            Status dict with current state.
        """
        # Continue from current director state
        state = self.director.state
        
        if state == DirectorState.AWAITING_SCRIPT_APPROVAL:
            if self.gates.is_approved(ApprovalGate.GATE_SCRIPT):
                # Script approved, continue to investigation
                return await self.director.run(self.topic, self.duration_seconds)
        
        # Re-run the director loop
        return await self.director.run(self.topic, self.duration_seconds)
    
    # === Approval API ===
    
    def approve_script(self, user_id: str, feedback: str = None) -> dict:
        """Approve the script gate."""
        return self.director.approve_script(user_id, feedback)
    
    def reject_script(self, user_id: str, reason: str) -> dict:
        """Reject the script gate."""
        return self.director.reject_script(user_id, reason)
    
    def approve_evidence(self, user_id: str) -> dict:
        """Approve the evidence URLs gate."""
        return self.director.approve_evidence(user_id)
    
    def reject_evidence(self, user_id: str, reason: str) -> dict:
        """Reject the evidence URLs gate."""
        self.gates.reject(ApprovalGate.GATE_EVIDENCE_URLS, user_id, reason)
        return {"status": "rejected", "reason": reason}
    
    def approve_screenshots(self, user_id: str) -> dict:
        """Approve the screenshots gate."""
        return self.director.approve_screenshots(user_id)
    
    def reject_screenshots(self, user_id: str, reason: str) -> dict:
        """Reject the screenshots gate."""
        self.gates.reject(ApprovalGate.GATE_SCREENSHOTS, user_id, reason)
        return {"status": "rejected", "reason": reason}
    
    def approve_render(self, user_id: str) -> dict:
        """Approve the render gate (final)."""
        return self.director.approve_render(user_id)
    
    # === Query API ===
    
    def get_status(self) -> dict:
        """Get current project status."""
        return {
            "project_id": self.project_id,
            "topic": self.topic,
            "director_state": self.director.state.value,
            "store": self.store.summary(),
            "gates": self.gates.summary(),
            "render_ready": self.store.is_render_ready()[0],
        }
    
    def get_artifacts(self, type: ArtifactType = None) -> list[dict]:
        """Get artifacts, optionally filtered by type."""
        if type:
            artifacts = self.store.get_by_type(type)
        else:
            artifacts = self.store.list_all()
        return [a.to_dict() for a in artifacts]
    
    def get_script(self) -> Optional[dict]:
        """Get the current script artifact."""
        script = self.store.get_latest(ArtifactType.SCRIPT)
        return script.data if script else None
    
    def get_pending_gate(self) -> Optional[str]:
        """Get the ID of the current pending gate."""
        pending = self.gates.get_pending_gates()
        return pending[0].id if pending else None
    
    def is_complete(self) -> bool:
        """Check if the project is complete."""
        return self.director.state == DirectorState.COMPLETE
    
    def is_render_ready(self) -> tuple[bool, list[str]]:
        """Check if ready to render."""
        return self.store.is_render_ready()
    
    def get_render_manifest(self) -> Optional[dict]:
        """Get the render manifest (only if all artifacts locked)."""
        return self.store.get_render_manifest()
