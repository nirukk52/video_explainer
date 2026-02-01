"""Tests for plan CLI commands."""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cli.main import cmd_plan


class TestCmdPlanCreate:
    """Tests for 'plan create' command."""

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create a mock project directory with required structure."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create config.json
        config = {
            "id": "test-project",
            "title": "Test Project",
            "description": "A test project",
            "version": "1.0.0",
            "video": {
                "resolution": {"width": 1920, "height": 1080},
                "fps": 30,
                "target_duration_seconds": 180,
            },
            "tts": {"provider": "mock", "voice_id": ""},
            "style": {},
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        # Create input directory with a sample file
        input_dir = project_dir / "input"
        input_dir.mkdir()
        with open(input_dir / "source.md", "w") as f:
            f.write("# Test Document\n\nThis is test content for the video.")

        return project_dir

    @pytest.fixture
    def mock_args(self, tmp_path, mock_project):
        """Create mock args for plan create command."""
        args = argparse.Namespace()
        args.project = "test-project"
        args.projects_dir = str(tmp_path)
        args.plan_command = "create"
        args.mock = True
        args.force = False
        args.duration = None
        args.no_interactive = True
        return args

    def test_create_plan_success(self, mock_args, mock_project, capsys):
        """Test successful plan creation."""
        result = cmd_plan(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Creating video plan" in captured.out
        assert "Plan saved to" in captured.out

        # Verify plan file was created
        plan_path = mock_project / "plan" / "plan.json"
        assert plan_path.exists()

    def test_create_plan_creates_both_files(self, mock_args, mock_project):
        """Test that both JSON and MD files are created."""
        cmd_plan(mock_args)

        plan_dir = mock_project / "plan"
        assert (plan_dir / "plan.json").exists()
        assert (plan_dir / "plan.md").exists()

    def test_create_plan_json_valid(self, mock_args, mock_project):
        """Test that created plan JSON is valid."""
        cmd_plan(mock_args)

        plan_path = mock_project / "plan" / "plan.json"
        with open(plan_path) as f:
            plan_data = json.load(f)

        assert "title" in plan_data
        assert "scenes" in plan_data
        assert "status" in plan_data
        assert plan_data["status"] == "draft"

    def test_create_plan_no_force_skips_existing(self, mock_args, mock_project, capsys):
        """Test that existing plan is not overwritten without --force."""
        # Create an existing plan
        plan_dir = mock_project / "plan"
        plan_dir.mkdir()
        with open(plan_dir / "plan.json", "w") as f:
            json.dump({"existing": True}, f)

        result = cmd_plan(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Plan already exists" in captured.out

    def test_create_plan_force_overwrites(self, mock_args, mock_project):
        """Test that --force overwrites existing plan."""
        # Create an existing plan
        plan_dir = mock_project / "plan"
        plan_dir.mkdir()
        with open(plan_dir / "plan.json", "w") as f:
            json.dump({"existing": True, "title": "Old Plan"}, f)

        mock_args.force = True
        result = cmd_plan(mock_args)

        assert result == 0

        # Verify plan was overwritten
        with open(plan_dir / "plan.json") as f:
            plan_data = json.load(f)
        assert "existing" not in plan_data

    def test_create_plan_no_input_files(self, mock_args, mock_project, capsys):
        """Test error when no input files exist."""
        # Remove input directory
        import shutil
        shutil.rmtree(mock_project / "input")

        result = cmd_plan(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Input directory not found" in captured.err

    def test_create_plan_project_not_found(self, mock_args, tmp_path, capsys):
        """Test error when project doesn't exist."""
        mock_args.project = "nonexistent-project"

        result = cmd_plan(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err


class TestCmdPlanShow:
    """Tests for 'plan show' command."""

    @pytest.fixture
    def project_with_plan(self, tmp_path):
        """Create a project with an existing plan."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create config
        config = {
            "id": "test-project",
            "title": "Test Project",
            "video": {"target_duration_seconds": 180},
            "tts": {},
            "style": {},
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        # Create plan
        plan_dir = project_dir / "plan"
        plan_dir.mkdir()
        plan = {
            "status": "draft",
            "created_at": "2024-01-15T10:00:00",
            "title": "Test Plan",
            "central_question": "Test?",
            "target_audience": "Testers",
            "estimated_total_duration_seconds": 60,
            "core_thesis": "Test",
            "key_concepts": ["A"],
            "complexity_score": 5,
            "scenes": [
                {
                    "scene_number": 1,
                    "scene_type": "hook",
                    "title": "Hook",
                    "concept_to_cover": "Test",
                    "visual_approach": "Test",
                    "ascii_visual": "",
                    "estimated_duration_seconds": 30,
                    "key_points": [],
                }
            ],
            "visual_style": "Test",
            "source_document": "test.md",
            "user_notes": "",
        }
        with open(plan_dir / "plan.json", "w") as f:
            json.dump(plan, f)

        return project_dir

    @pytest.fixture
    def mock_args(self, tmp_path, project_with_plan):
        args = argparse.Namespace()
        args.project = "test-project"
        args.projects_dir = str(tmp_path)
        args.plan_command = "show"
        args.mock = True
        return args

    def test_show_plan_success(self, mock_args, capsys):
        """Test showing an existing plan."""
        result = cmd_plan(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "VIDEO PLAN:" in captured.out
        assert "Test Plan" in captured.out

    def test_show_plan_no_plan(self, mock_args, tmp_path, capsys):
        """Test error when no plan exists."""
        # Create project without plan
        project_dir = tmp_path / "no-plan-project"
        project_dir.mkdir()
        config = {"id": "no-plan-project", "title": "No Plan", "video": {}, "tts": {}, "style": {}}
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        mock_args.project = "no-plan-project"

        result = cmd_plan(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No plan found" in captured.err


class TestCmdPlanApprove:
    """Tests for 'plan approve' command."""

    @pytest.fixture
    def project_with_draft_plan(self, tmp_path):
        """Create a project with a draft plan."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        config = {
            "id": "test-project",
            "title": "Test",
            "video": {},
            "tts": {},
            "style": {},
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        plan_dir = project_dir / "plan"
        plan_dir.mkdir()
        plan = {
            "status": "draft",
            "created_at": "2024-01-15T10:00:00",
            "approved_at": None,
            "title": "Draft Plan",
            "central_question": "?",
            "target_audience": "All",
            "estimated_total_duration_seconds": 60,
            "core_thesis": "Test",
            "key_concepts": [],
            "complexity_score": 5,
            "scenes": [
                {
                    "scene_number": 1,
                    "scene_type": "hook",
                    "title": "Hook",
                    "concept_to_cover": "Test",
                    "visual_approach": "Test",
                    "ascii_visual": "",
                    "estimated_duration_seconds": 30,
                    "key_points": [],
                }
            ],
            "visual_style": "Test",
            "source_document": "test.md",
            "user_notes": "",
        }
        with open(plan_dir / "plan.json", "w") as f:
            json.dump(plan, f)

        return project_dir

    @pytest.fixture
    def mock_args(self, tmp_path, project_with_draft_plan):
        args = argparse.Namespace()
        args.project = "test-project"
        args.projects_dir = str(tmp_path)
        args.plan_command = "approve"
        return args

    def test_approve_plan_success(self, mock_args, project_with_draft_plan, capsys):
        """Test approving a draft plan."""
        result = cmd_plan(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Plan approved" in captured.out

        # Verify plan status changed
        plan_path = project_with_draft_plan / "plan" / "plan.json"
        with open(plan_path) as f:
            plan_data = json.load(f)
        assert plan_data["status"] == "approved"
        assert plan_data["approved_at"] is not None

    def test_approve_already_approved(self, mock_args, project_with_draft_plan, capsys):
        """Test approving an already approved plan."""
        # First approval
        cmd_plan(mock_args)

        # Second approval attempt
        result = cmd_plan(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "already approved" in captured.out

    def test_approve_no_plan(self, mock_args, tmp_path, capsys):
        """Test error when no plan exists."""
        # Create project without plan
        project_dir = tmp_path / "no-plan"
        project_dir.mkdir()
        config = {"id": "no-plan", "title": "No Plan", "video": {}, "tts": {}, "style": {}}
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        mock_args.project = "no-plan"

        result = cmd_plan(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No plan found" in captured.err


class TestCmdPlanReview:
    """Tests for 'plan review' command."""

    @pytest.fixture
    def project_with_plan(self, tmp_path):
        """Create a project with a plan."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        config = {
            "id": "test-project",
            "title": "Test",
            "video": {},
            "tts": {},
            "style": {},
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        plan_dir = project_dir / "plan"
        plan_dir.mkdir()
        plan = {
            "status": "draft",
            "created_at": "2024-01-15T10:00:00",
            "title": "Review Plan",
            "central_question": "?",
            "target_audience": "All",
            "estimated_total_duration_seconds": 60,
            "core_thesis": "Test",
            "key_concepts": [],
            "complexity_score": 5,
            "scenes": [
                {
                    "scene_number": 1,
                    "scene_type": "hook",
                    "title": "Hook",
                    "concept_to_cover": "Test",
                    "visual_approach": "Test",
                    "ascii_visual": "",
                    "estimated_duration_seconds": 30,
                    "key_points": [],
                }
            ],
            "visual_style": "Test",
            "source_document": "test.md",
            "user_notes": "",
        }
        with open(plan_dir / "plan.json", "w") as f:
            json.dump(plan, f)

        return project_dir

    @pytest.fixture
    def mock_args(self, tmp_path, project_with_plan):
        args = argparse.Namespace()
        args.project = "test-project"
        args.projects_dir = str(tmp_path)
        args.plan_command = "review"
        args.mock = True
        return args

    def test_review_approve_via_interactive(self, mock_args, project_with_plan):
        """Test reviewing and approving via interactive session."""
        with patch('builtins.input', return_value='a'):
            result = cmd_plan(mock_args)

        assert result == 0

        # Verify plan was approved
        plan_path = project_with_plan / "plan" / "plan.json"
        with open(plan_path) as f:
            plan_data = json.load(f)
        assert plan_data["status"] == "approved"

    def test_review_quit_via_interactive(self, mock_args, project_with_plan):
        """Test reviewing and quitting via interactive session."""
        with patch('builtins.input', return_value='q'):
            result = cmd_plan(mock_args)

        # Quitting returns 1 (not approved)
        assert result == 1

    def test_review_no_plan(self, mock_args, tmp_path, capsys):
        """Test error when no plan exists to review."""
        project_dir = tmp_path / "no-plan"
        project_dir.mkdir()
        config = {"id": "no-plan", "title": "No Plan", "video": {}, "tts": {}, "style": {}}
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        mock_args.project = "no-plan"

        result = cmd_plan(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No plan found" in captured.err
