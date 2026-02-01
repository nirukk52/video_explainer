"""Tests for PlanEditor class."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from io import StringIO

import pytest

from src.config import Config
from src.models import PlannedScene, VideoPlan
from src.planning.editor import PlanEditor
from src.planning.generator import PlanGenerator


class TestPlanEditor:
    """Tests for the PlanEditor class."""

    @pytest.fixture
    def mock_config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def generator(self, mock_config):
        return PlanGenerator(config=mock_config)

    @pytest.fixture
    def sample_plan(self):
        """Create a sample plan for testing."""
        scenes = [
            PlannedScene(
                scene_number=1,
                scene_type="hook",
                title="The Challenge",
                concept_to_cover="The problem",
                visual_approach="Dramatic visualization",
                ascii_visual="[HOOK ASCII]",
                estimated_duration_seconds=45.0,
                key_points=["Hook point"],
            ),
            PlannedScene(
                scene_number=2,
                scene_type="conclusion",
                title="Wrap Up",
                concept_to_cover="Summary",
                visual_approach="Recap",
                ascii_visual="[CONCLUSION ASCII]",
                estimated_duration_seconds=30.0,
                key_points=["Conclusion point"],
            ),
        ]

        return VideoPlan(
            status="draft",
            created_at="2024-01-15T10:00:00",
            title="Test Plan",
            central_question="Test question?",
            target_audience="Testers",
            estimated_total_duration_seconds=75.0,
            core_thesis="Test thesis",
            key_concepts=["A", "B"],
            complexity_score=5,
            scenes=scenes,
            visual_style="Test style",
            source_document="test.md",
        )

    def test_editor_initialization(self, generator, tmp_path):
        """Test that editor initializes correctly."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        assert editor.generator == generator
        assert editor.plan_dir == tmp_path

    def test_display_plan(self, generator, sample_plan, tmp_path, capsys):
        """Test displaying a plan without interactive session."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        editor.display_plan(sample_plan)

        captured = capsys.readouterr()
        assert "VIDEO PLAN:" in captured.out
        assert sample_plan.title in captured.out

    def test_approve_plan(self, generator, sample_plan, tmp_path):
        """Test approving a plan."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        assert sample_plan.status == "draft"
        assert sample_plan.approved_at is None

        approved_plan = editor.approve_plan(sample_plan)

        assert approved_plan.status == "approved"
        assert approved_plan.approved_at is not None

        # Check that plan was saved
        plan_path = tmp_path / "plan.json"
        assert plan_path.exists()

    def test_approve_plan_sets_timestamp(self, generator, sample_plan, tmp_path):
        """Test that approval sets proper timestamp."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        approved_plan = editor.approve_plan(sample_plan)

        # Should be a valid ISO timestamp
        from datetime import datetime
        datetime.fromisoformat(approved_plan.approved_at)


class TestPlanEditorInteractive:
    """Tests for interactive session functionality."""

    @pytest.fixture
    def mock_config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def generator(self, mock_config):
        return PlanGenerator(config=mock_config)

    @pytest.fixture
    def sample_plan(self):
        scenes = [
            PlannedScene(
                scene_number=1,
                scene_type="hook",
                title="Test Hook",
                concept_to_cover="Test",
                visual_approach="Test",
                ascii_visual="",
                estimated_duration_seconds=30.0,
                key_points=[],
            ),
        ]

        return VideoPlan(
            status="draft",
            created_at="2024-01-15T10:00:00",
            title="Test Plan",
            central_question="?",
            target_audience="All",
            estimated_total_duration_seconds=30.0,
            core_thesis="Test",
            key_concepts=[],
            complexity_score=5,
            scenes=scenes,
            visual_style="Test",
            source_document="test.md",
        )

    def test_interactive_approve_command(self, generator, sample_plan, tmp_path):
        """Test 'a' command approves plan."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', return_value='a'):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is True
        assert plan.status == "approved"

    def test_interactive_approve_full_command(self, generator, sample_plan, tmp_path):
        """Test 'approve' command approves plan."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', return_value='approve'):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is True
        assert plan.status == "approved"

    def test_interactive_quit_command(self, generator, sample_plan, tmp_path):
        """Test 'q' command exits without approving."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', return_value='q'):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is False
        # Plan should be saved as draft
        plan_path = tmp_path / "plan.json"
        assert plan_path.exists()

    def test_interactive_save_command(self, generator, sample_plan, tmp_path):
        """Test 's' command saves and continues."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        # First save, then quit
        with patch('builtins.input', side_effect=['s', 'q']):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is False
        plan_path = tmp_path / "plan.json"
        assert plan_path.exists()

    def test_interactive_refine_command(self, generator, sample_plan, tmp_path):
        """Test 'r' command refines plan."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        # Refine then approve
        with patch('builtins.input', side_effect=['r Add more detail', 'a']):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is True
        assert "Add more detail" in plan.user_notes

    def test_interactive_refine_without_feedback(self, generator, sample_plan, tmp_path, capsys):
        """Test 'r' command without feedback shows usage."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', side_effect=['r', 'q']):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_interactive_help_command(self, generator, sample_plan, tmp_path, capsys):
        """Test 'h' command shows help."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', side_effect=['h', 'q']):
            editor.run_interactive_session(sample_plan)

        captured = capsys.readouterr()
        assert "Commands:" in captured.out
        assert "approve" in captured.out
        assert "refine" in captured.out

    def test_interactive_unknown_command(self, generator, sample_plan, tmp_path, capsys):
        """Test unknown command shows error and help."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', side_effect=['xyz', 'q']):
            editor.run_interactive_session(sample_plan)

        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_interactive_empty_input_continues(self, generator, sample_plan, tmp_path):
        """Test empty input continues loop."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        # Empty input, then quit
        with patch('builtins.input', side_effect=['', 'q']):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is False

    def test_interactive_keyboard_interrupt(self, generator, sample_plan, tmp_path):
        """Test Ctrl+C exits gracefully."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is False

    def test_interactive_eof(self, generator, sample_plan, tmp_path):
        """Test EOF exits gracefully."""
        editor = PlanEditor(generator=generator, plan_dir=tmp_path)

        with patch('builtins.input', side_effect=EOFError()):
            plan, was_approved = editor.run_interactive_session(sample_plan)

        assert was_approved is False
