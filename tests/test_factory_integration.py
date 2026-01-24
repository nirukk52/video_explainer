"""
Integration tests for the Shorts Factory with DeepSeek pricing prompt.

Tests the full HITL flow:
1. Create project with topic
2. Generate script → Wait at script approval gate
3. Approve script → Lock script → Continue to investigation
4. Investigate evidence → Wait at evidence approval gate
5. Approve evidence → Lock evidence → Continue to capture
6. Capture screenshots → Wait at capture approval gate
7. Approve screenshots → Lock screenshots → Continue to packaging
8. Package render manifest → Wait at render approval gate
9. Approve render → Lock manifest → Ready to render
"""

import pytest
import tempfile
from pathlib import Path

from src.factory.project import ShortsFactoryProject
from src.factory.artifact_store import ArtifactType
from src.factory.approval_gate import ApprovalGate, ApprovalStatus
from src.factory.director import DirectorState


class TestDeepSeekPricingFlow:
    """Test the full flow with DeepSeek pricing crash prompt."""
    
    TOPIC = "DeepSeek's pricing is crashing the AI market"
    
    @pytest.mark.asyncio
    async def test_full_flow_with_auto_approve(self):
        """Test the full pipeline with auto-approval (happy path)."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic=self.TOPIC,
                output_dir=tmp,
                auto_approve=True,
            )
            
            result = await project.run_with_auto_approve()
            
            # Should complete (or be at render stage)
            assert result["state"] in ["complete", "rendering"]
            
            # Should have a locked script
            script = project.store.get_locked_script()
            assert script is not None
            assert script.status == "locked"
    
    @pytest.mark.asyncio
    async def test_hitl_script_approval_flow(self):
        """Test HITL flow for script approval gate."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic=self.TOPIC,
                output_dir=tmp,
                auto_approve=False,  # Manual approval
            )
            
            # Run - should stop at script approval
            result = await project.run()
            
            # Should be waiting for script approval
            assert result["state"] == "awaiting_script_approval"
            
            # Script should be in draft state
            script = project.store.get_latest(ArtifactType.SCRIPT)
            assert script is not None
            assert script.status == "draft"
            
            # Gate should be pending
            assert not project.gates.is_approved(ApprovalGate.GATE_SCRIPT)
            
            # Approve the script
            project.approve_script("test_user", feedback="Looks good!")
            
            # Now gate should be approved
            assert project.gates.is_approved(ApprovalGate.GATE_SCRIPT)
            
            # Script should be locked
            script = project.store.get_latest(ArtifactType.SCRIPT)
            assert script.status == "locked"
    
    @pytest.mark.asyncio
    async def test_hitl_rejection_flow(self):
        """Test HITL flow when script is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic=self.TOPIC,
                output_dir=tmp,
                auto_approve=False,
            )
            
            # Run - should stop at script approval
            await project.run()
            
            # Reject the script
            result = project.reject_script("test_user", "Need more evidence scenes")
            
            # Gate should be rejected
            gate = project.gates.get_gate(ApprovalGate.GATE_SCRIPT)
            assert gate.status == ApprovalStatus.REJECTED
            
            # Script should still be draft (not locked)
            script = project.store.get_latest(ArtifactType.SCRIPT)
            assert script.status == "draft"
    
    def test_artifact_store_tracks_all_outputs(self):
        """Test that artifact store tracks all outputs correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic=self.TOPIC,
                output_dir=tmp,
            )
            
            # Add various artifacts
            project.store.put(
                ArtifactType.SCRIPT,
                {"title": "Test Script", "scenes": []},
                created_by="test",
            )
            project.store.put(
                ArtifactType.EVIDENCE_URL,
                {"url": "https://example.com", "verified": True},
                scene_id="1",
                created_by="investigator",
            )
            project.store.put(
                ArtifactType.SCREENSHOT,
                {"path": "scene1.png"},
                scene_id="1",
                created_by="witness",
            )
            
            # Summary should reflect all artifacts
            summary = project.store.summary()
            assert summary["total_artifacts"] == 3
            assert "script" in summary["by_type"]
            assert "evidence_url" in summary["by_type"]
            assert "screenshot" in summary["by_type"]
    
    def test_render_only_after_all_locked(self):
        """Test that render manifest only available when all artifacts locked."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic=self.TOPIC,
                output_dir=tmp,
            )
            
            # Add a script with an evidence scene
            script = project.store.put(
                ArtifactType.SCRIPT,
                {
                    "title": "Test",
                    "scenes": [
                        {"scene_id": "1", "needs_evidence": True},
                    ],
                },
                created_by="director",
            )
            
            # Not ready - script not locked
            ready, missing = project.is_render_ready()
            assert not ready
            assert "Locked script required" in missing
            
            # Lock script
            project.store.lock(script.id, "user")
            
            # Still not ready - missing screenshot
            ready, missing = project.is_render_ready()
            assert not ready
            assert any("scene 1" in m for m in missing)
            
            # Add and lock screenshot
            screenshot = project.store.put(
                ArtifactType.SCREENSHOT,
                {"path": "scene1.png"},
                scene_id="1",
                created_by="witness",
            )
            project.store.lock(screenshot.id, "user")
            
            # Now ready
            ready, missing = project.is_render_ready()
            assert ready
            assert len(missing) == 0
            
            # Manifest should be available
            manifest = project.get_render_manifest()
            assert manifest is not None
            assert len(manifest["render_queue"]) == 1
            assert manifest["render_queue"][0]["locked"] == True
    
    def test_project_persistence(self):
        """Test that project state persists and can be loaded."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create project
            project1 = ShortsFactoryProject.create(
                topic=self.TOPIC,
                output_dir=tmp,
            )
            project_id = project1.project_id
            
            # Add some artifacts
            project1.store.put(
                ArtifactType.SCRIPT,
                {"title": "Persisted Script"},
                created_by="test",
            )
            
            # Load project in new instance
            project2 = ShortsFactoryProject.load(project_id, output_dir=tmp)
            
            # Should have the same artifacts
            script = project2.store.get_latest(ArtifactType.SCRIPT)
            assert script is not None
            assert script.data["title"] == "Persisted Script"


class TestApprovalGateFlow:
    """Test approval gate behavior in detail."""
    
    def test_gates_block_progression(self):
        """Test that gates properly block pipeline progression."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic="Test topic",
                output_dir=tmp,
            )
            
            # Cannot proceed to investigate without script approval
            can_proceed, blocking = project.gates.can_proceed_to("investigate")
            assert not can_proceed
            assert ApprovalGate.GATE_SCRIPT in blocking
    
    def test_approval_creates_audit_trail(self):
        """Test that approvals create proper audit trail."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic="Test topic",
                output_dir=tmp,
            )
            
            # Add and approve script
            project.store.put(
                ArtifactType.SCRIPT,
                {"title": "Test"},
                created_by="director",
            )
            project.approve_script("user_123", feedback="LGTM!")
            
            # Check audit trail
            gate = project.gates.get_gate(ApprovalGate.GATE_SCRIPT)
            assert len(gate.events) == 1
            
            event = gate.events[0]
            assert event.decided_by == "user_123"
            assert event.feedback == "LGTM!"
            assert event.decided_at is not None


class TestDirectorStateMachine:
    """Test Director state transitions."""
    
    @pytest.mark.asyncio
    async def test_state_transitions_in_order(self):
        """Test that Director transitions through states in order."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                topic="Test topic",
                output_dir=tmp,
                auto_approve=True,
            )
            
            states_seen = []
            
            def track_state(state, data):
                states_seen.append(state.value)
            
            project.director.set_progress_callback(track_state)
            
            await project.run_with_auto_approve()
            
            # Should have seen multiple states
            assert len(states_seen) > 0
            
            # First state should be scripting
            if states_seen:
                assert states_seen[0] == "scripting"
