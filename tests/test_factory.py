"""
Tests for the Shorts Factory components.

Tests the core architecture:
- ArtifactStore: Canonical storage
- ApprovalGate: Human checkpoints
- Director: Non-linear orchestration
- ShortsFactoryProject: Main entry point
"""

import pytest
import tempfile
from pathlib import Path

from src.factory.artifact_store import ArtifactStore, ArtifactType, Artifact
from src.factory.approval_gate import ApprovalGate, ApprovalStatus, Gate
from src.factory.director import Director, DirectorState
from src.factory.project import ShortsFactoryProject


class TestArtifactStore:
    """Tests for the ArtifactStore class."""
    
    def test_put_creates_draft_artifact(self, tmp_path):
        """Storing an artifact should create it as draft."""
        store = ArtifactStore(tmp_path)
        
        artifact = store.put(
            type=ArtifactType.SCRIPT,
            data={"title": "Test Script", "scenes": []},
            created_by="test",
        )
        
        assert artifact.id.startswith("script_")
        assert artifact.status == "draft"
        assert artifact.data["title"] == "Test Script"
    
    def test_lock_makes_artifact_immutable(self, tmp_path):
        """Locking an artifact should mark it as locked."""
        store = ArtifactStore(tmp_path)
        
        artifact = store.put(
            type=ArtifactType.SCRIPT,
            data={"title": "Test"},
            created_by="test",
        )
        
        locked = store.lock(artifact.id, "user123")
        
        assert locked.status == "locked"
        assert locked.locked_by == "user123"
        assert locked.locked_at is not None
    
    def test_cannot_update_locked_artifact(self, tmp_path):
        """Updating a locked artifact should raise an error."""
        store = ArtifactStore(tmp_path)
        
        artifact = store.put(
            type=ArtifactType.SCRIPT,
            data={"title": "Test"},
            created_by="test",
        )
        store.lock(artifact.id, "user")
        
        with pytest.raises(ValueError, match="Cannot update locked"):
            store.update(artifact.id, {"title": "Modified"})
    
    def test_get_by_type_filters_correctly(self, tmp_path):
        """get_by_type should filter by type and status."""
        store = ArtifactStore(tmp_path)
        
        # Create various artifacts
        script = store.put(ArtifactType.SCRIPT, {"title": "Script"}, created_by="test")
        screenshot1 = store.put(ArtifactType.SCREENSHOT, {"path": "a.png"}, scene_id="1", created_by="test")
        screenshot2 = store.put(ArtifactType.SCREENSHOT, {"path": "b.png"}, scene_id="2", created_by="test")
        
        store.lock(screenshot1.id, "user")
        
        # Filter by type
        screenshots = store.get_by_type(ArtifactType.SCREENSHOT)
        assert len(screenshots) == 2
        
        # Filter by type and status
        locked_screenshots = store.get_by_type(ArtifactType.SCREENSHOT, status="locked")
        assert len(locked_screenshots) == 1
        assert locked_screenshots[0].id == screenshot1.id
    
    def test_is_render_ready_checks_locked_script(self, tmp_path):
        """is_render_ready should require a locked script."""
        store = ArtifactStore(tmp_path)
        
        # No script - not ready
        ready, missing = store.is_render_ready()
        assert not ready
        assert "Locked script required" in missing
        
        # Draft script - not ready
        script = store.put(
            ArtifactType.SCRIPT,
            {"scenes": []},
            created_by="test",
        )
        ready, missing = store.is_render_ready()
        assert not ready
        
        # Locked script - ready (no evidence scenes)
        store.lock(script.id, "user")
        ready, missing = store.is_render_ready()
        assert ready
    
    def test_persistence_across_instances(self, tmp_path):
        """Artifacts should persist across store instances."""
        # Create and store
        store1 = ArtifactStore(tmp_path)
        artifact = store1.put(
            type=ArtifactType.SCRIPT,
            data={"title": "Persistent"},
            created_by="test",
        )
        artifact_id = artifact.id
        
        # Load in new instance
        store2 = ArtifactStore(tmp_path)
        loaded = store2.get(artifact_id)
        
        assert loaded is not None
        assert loaded.data["title"] == "Persistent"


class TestApprovalGate:
    """Tests for the ApprovalGate class."""
    
    def test_standard_gates_initialized(self):
        """Standard gates should be initialized automatically."""
        gates = ApprovalGate()
        
        assert gates.get_gate(ApprovalGate.GATE_SCRIPT) is not None
        assert gates.get_gate(ApprovalGate.GATE_EVIDENCE_URLS) is not None
        assert gates.get_gate(ApprovalGate.GATE_SCREENSHOTS) is not None
        assert gates.get_gate(ApprovalGate.GATE_RENDER) is not None
    
    def test_approval_changes_gate_status(self):
        """Approving a gate should change its status to approved."""
        gates = ApprovalGate()
        
        gates.approve(
            ApprovalGate.GATE_SCRIPT,
            "user123",
            ["artifact_1"],
        )
        
        assert gates.is_approved(ApprovalGate.GATE_SCRIPT)
        
        gate = gates.get_gate(ApprovalGate.GATE_SCRIPT)
        assert len(gate.events) == 1
        assert gate.events[0].decided_by == "user123"
    
    def test_rejection_requires_reason(self):
        """Rejecting a gate should require a reason."""
        gates = ApprovalGate()
        
        with pytest.raises(ValueError, match="Rejection reason is required"):
            gates.reject(
                ApprovalGate.GATE_SCRIPT,
                "user123",
                "",  # Empty reason
            )
    
    def test_rejection_records_reason(self):
        """Rejection should record the reason."""
        gates = ApprovalGate()
        
        gates.reject(
            ApprovalGate.GATE_SCRIPT,
            "user123",
            "Script needs more evidence",
        )
        
        gate = gates.get_gate(ApprovalGate.GATE_SCRIPT)
        assert gate.status == ApprovalStatus.REJECTED
        assert gate.events[0].rejection_reason == "Script needs more evidence"
    
    def test_auto_approve_mode(self):
        """Auto-approve mode should approve all gates automatically."""
        gates = ApprovalGate(auto_approve=True)
        
        status = gates.request_approval(
            ApprovalGate.GATE_SCRIPT,
            ["artifact_1"],
        )
        
        assert status == ApprovalStatus.AUTO_APPROVED
        assert gates.is_approved(ApprovalGate.GATE_SCRIPT)
    
    def test_can_proceed_to_checks_prerequisites(self):
        """can_proceed_to should check prerequisite gates."""
        gates = ApprovalGate()
        
        # Cannot proceed to investigate without script approval
        can_proceed, blocking = gates.can_proceed_to("investigate")
        assert not can_proceed
        assert ApprovalGate.GATE_SCRIPT in blocking
        
        # After script approval, can proceed
        gates.approve(ApprovalGate.GATE_SCRIPT, "user")
        can_proceed, blocking = gates.can_proceed_to("investigate")
        assert can_proceed


class TestDirector:
    """Tests for the Director class."""
    
    def test_director_starts_in_idle_state(self, tmp_path):
        """Director should start in IDLE state."""
        store = ArtifactStore(tmp_path)
        gates = ApprovalGate()
        director = Director(store, gates)
        
        assert director.state == DirectorState.IDLE
    
    @pytest.mark.asyncio
    async def test_director_generates_mock_script(self, tmp_path):
        """Director should generate a mock script when no executor set."""
        store = ArtifactStore(tmp_path)
        gates = ApprovalGate(auto_approve=True)
        director = Director(store, gates)
        
        result = await director.run("Test topic", 45)
        
        # Should have created a script artifact
        scripts = store.get_by_type(ArtifactType.SCRIPT)
        assert len(scripts) > 0
    
    def test_approve_script_locks_artifact(self, tmp_path):
        """approve_script should lock the script artifact."""
        store = ArtifactStore(tmp_path)
        gates = ApprovalGate()
        director = Director(store, gates)
        
        # Add a script artifact
        store.put(
            ArtifactType.SCRIPT,
            {"title": "Test", "scenes": []},
            created_by="director",
        )
        
        director.approve_script("user123")
        
        script = store.get_latest(ArtifactType.SCRIPT)
        assert script.status == "locked"


class TestShortsFactoryProject:
    """Tests for the ShortsFactoryProject class."""
    
    def test_create_generates_project_id(self):
        """Creating a project should generate a unique ID."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                "Test topic",
                output_dir=tmp,
            )
            
            assert project.project_id.startswith("short_")
            assert project.topic == "Test topic"
    
    def test_project_directory_created(self):
        """Project should create its output directory."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                "Test topic",
                output_dir=tmp,
            )
            
            assert project.project_dir.exists()
            assert (project.project_dir / "artifacts").exists()
    
    def test_get_status_returns_project_info(self):
        """get_status should return project information."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                "DeepSeek pricing crash",
                output_dir=tmp,
            )
            
            status = project.get_status()
            
            assert status["project_id"] == project.project_id
            assert status["topic"] == "DeepSeek pricing crash"
            assert "director_state" in status
            assert "store" in status
            assert "gates" in status
    
    @pytest.mark.asyncio
    async def test_run_with_auto_approve_completes(self):
        """Running with auto-approve should complete the pipeline."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                "Test topic",
                output_dir=tmp,
                auto_approve=True,
            )
            
            result = await project.run_with_auto_approve()
            
            # Should complete without blocking
            assert result["state"] in ["complete", "rendering"]
    
    def test_approval_api_works(self):
        """Manual approval API should work correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            project = ShortsFactoryProject.create(
                "Test topic",
                output_dir=tmp,
            )
            
            # Add a script artifact manually
            project.store.put(
                ArtifactType.SCRIPT,
                {"title": "Test", "scenes": []},
                created_by="test",
            )
            
            # Approve script
            result = project.approve_script("user123")
            
            # Check approval went through
            assert project.gates.is_approved(ApprovalGate.GATE_SCRIPT)
            
            # Script should be locked
            script = project.store.get_latest(ArtifactType.SCRIPT)
            assert script.status == "locked"


class TestIntegration:
    """Integration tests for the factory components."""
    
    def test_full_artifact_lifecycle(self, tmp_path):
        """Test the full lifecycle: create -> update -> lock."""
        store = ArtifactStore(tmp_path)
        
        # Create
        artifact = store.put(
            ArtifactType.SCRIPT,
            {"title": "Draft", "version": 1},
            created_by="director",
        )
        assert artifact.version == 1
        
        # Update (creates new version)
        updated = store.update(
            artifact.id,
            {"title": "Updated", "version": 2},
            updated_by="director",
        )
        assert updated.version == 2
        assert updated.previous_version_id == artifact.id
        
        # Lock
        locked = store.lock(updated.id, "user")
        assert locked.status == "locked"
        
        # Cannot update locked
        with pytest.raises(ValueError):
            store.update(updated.id, {"title": "Should fail"})
    
    def test_render_readiness_with_evidence(self, tmp_path):
        """Test render readiness when scenes require evidence."""
        store = ArtifactStore(tmp_path)
        
        # Script with evidence scene
        script = store.put(
            ArtifactType.SCRIPT,
            {
                "title": "Test",
                "scenes": [
                    {"scene_id": "1", "needs_evidence": True},
                    {"scene_id": "2", "needs_evidence": False},
                ],
            },
            created_by="director",
        )
        store.lock(script.id, "user")
        
        # Not ready - missing screenshot for scene 1
        ready, missing = store.is_render_ready()
        assert not ready
        assert any("scene 1" in m for m in missing)
        
        # Add screenshot for scene 1
        screenshot = store.put(
            ArtifactType.SCREENSHOT,
            {"path": "scene1.png"},
            scene_id="1",
            created_by="witness",
        )
        
        # Still not ready - screenshot not locked
        ready, missing = store.is_render_ready()
        assert not ready
        
        # Lock screenshot
        store.lock(screenshot.id, "user")
        
        # Now ready
        ready, missing = store.is_render_ready()
        assert ready
        assert len(missing) == 0
