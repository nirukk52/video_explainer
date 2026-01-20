"""Tests for refine CLI command."""

import pytest
import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from src.refine.command import add_refine_parser, cmd_refine


class TestAddRefineParser:
    """Tests for parser setup."""

    def test_adds_refine_subparser(self):
        """Test that refine subparser is added correctly."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        add_refine_parser(subparsers)

        # Parse a refine command
        args = parser.parse_args(["refine", "test-project"])
        assert args.project == "test-project"

    def test_phase_argument(self):
        """Test phase argument options."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_refine_parser(subparsers)

        # Test visual phase (default)
        args = parser.parse_args(["refine", "test-project"])
        assert args.phase == "visual"

        # Test analyze phase
        args = parser.parse_args(["refine", "test-project", "--phase", "analyze"])
        assert args.phase == "analyze"

        # Test script phase
        args = parser.parse_args(["refine", "test-project", "--phase", "script"])
        assert args.phase == "script"

    def test_scene_argument(self):
        """Test scene argument."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_refine_parser(subparsers)

        args = parser.parse_args(["refine", "test-project", "--scene", "3"])
        assert args.scene == 3

    def test_force_argument(self):
        """Test force flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_refine_parser(subparsers)

        args = parser.parse_args(["refine", "test-project", "--force"])
        assert args.force is True

    def test_skip_validation_argument(self):
        """Test skip-validation flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_refine_parser(subparsers)

        args = parser.parse_args(["refine", "test-project", "--skip-validation"])
        assert args.skip_validation is True

    def test_quiet_argument(self):
        """Test quiet flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_refine_parser(subparsers)

        args = parser.parse_args(["refine", "test-project", "--quiet"])
        assert args.quiet is True

    def test_projects_dir_argument(self):
        """Test projects-dir argument."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_refine_parser(subparsers)

        # Default value
        args = parser.parse_args(["refine", "test-project"])
        assert args.projects_dir == "projects"

        # Custom value
        args = parser.parse_args(["refine", "test-project", "--projects-dir", "/custom/path"])
        assert args.projects_dir == "/custom/path"


class TestCmdRefine:
    """Tests for cmd_refine function."""

    @pytest.fixture
    def mock_args(self):
        """Create mock arguments."""
        args = MagicMock()
        args.project = "test-project"
        args.projects_dir = "projects"
        args.phase = "visual"
        args.scene = None
        args.force = False
        args.skip_validation = False
        args.quiet = False
        return args

    def test_cmd_refine_project_not_found(self, mock_args):
        """Test error when project not found."""
        with patch("src.refine.command.load_project") as mock_load:
            mock_load.side_effect = FileNotFoundError("Project not found")

            result = cmd_refine(mock_args)

            assert result == 1  # Non-zero exit code

    def test_cmd_refine_validation_failure(self, mock_args, project_with_files):
        """Test behavior when validation fails."""
        with patch("src.refine.command.load_project") as mock_load:
            mock_load.return_value = project_with_files

            with patch("src.refine.command.validate_project_sync") as mock_validate:
                mock_status = MagicMock()
                mock_status.is_synced = False
                mock_status.issues = [MagicMock(description="Test issue", suggestion="Fix it")]
                mock_validate.return_value = mock_status

                result = cmd_refine(mock_args)

                # Should fail due to validation
                assert result == 1


class TestPhaseHandling:
    """Tests for different phase handling."""

    @pytest.fixture
    def mock_args(self):
        """Create mock arguments."""
        args = MagicMock()
        args.project = "test-project"
        args.projects_dir = "projects"
        args.scene = None
        args.force = False
        args.skip_validation = True
        args.quiet = False
        args.batch_approve = False
        return args

    def test_analyze_phase(self, mock_args, project_with_files):
        """Test analyze phase execution."""
        mock_args.phase = "analyze"

        with patch("src.refine.command.load_project") as mock_load:
            mock_load.return_value = project_with_files

            with patch("src.refine.command.ScriptAnalyzer") as mock_analyzer_class:
                # Create mock analyzer instance
                mock_analyzer = MagicMock()
                mock_analyzer_class.return_value = mock_analyzer

                # Mock the analyze() result
                mock_result = MagicMock()
                mock_result.has_critical_gaps = False
                mock_result.source_file = "input.md"
                mock_result.overall_coverage_score = 80.0
                mock_result.missing_concepts = []
                mock_result.shallow_concepts = []
                mock_result.narrative_gaps = []
                mock_result.suggested_scenes = []
                mock_result.patches = []
                mock_result.analysis_notes = "Good coverage"
                mock_analyzer.analyze.return_value = mock_result
                mock_analyzer.save_result.return_value = Path("/tmp/gap_analysis.json")

                result = cmd_refine(mock_args)

                # Analyze phase returns 0 when no critical gaps
                assert result == 0
                mock_analyzer.analyze.assert_called_once()

    def test_script_phase(self, mock_args, project_with_files):
        """Test script phase execution."""
        mock_args.phase = "script"

        with patch("src.refine.command.load_project") as mock_load:
            mock_load.return_value = project_with_files

            with patch("src.refine.command.ScriptRefiner") as mock_refiner_class:
                # Create mock refiner instance
                mock_refiner = MagicMock()
                mock_refiner_class.return_value = mock_refiner

                # Mock the refine() result (returns tuple)
                from src.refine.models import NarrationRefinementResult
                mock_narration_result = NarrationRefinementResult(
                    project_id="test-project",
                    overall_storytelling_score=8.0,
                    total_issues_found=0,
                )
                mock_refiner.refine.return_value = ([], mock_narration_result)
                mock_refiner.save_result.return_value = Path("/tmp/narration_analysis.json")

                result = cmd_refine(mock_args)

                # Script phase returns 0 when no patches
                assert result == 0
                mock_refiner.refine.assert_called_once()


class TestVisualPhase:
    """Tests for visual phase execution."""

    @pytest.fixture
    def mock_args(self):
        """Create mock arguments."""
        args = MagicMock()
        args.project = "test-project"
        args.projects_dir = "projects"
        args.phase = "visual"
        args.scene = None
        args.force = False
        args.skip_validation = True
        args.quiet = True
        return args

    def test_visual_phase_no_storyboard(self, mock_args, project_with_files):
        """Test visual phase when storyboard is missing."""
        with patch("src.refine.command.load_project") as mock_load:
            mock_project = MagicMock()
            mock_project.id = "test"
            mock_project.title = "Test"
            mock_project.root_dir = Path("/tmp/test")
            mock_project.load_storyboard.side_effect = FileNotFoundError("No storyboard")
            mock_load.return_value = mock_project

            result = cmd_refine(mock_args)

            assert result == 1  # Error due to missing storyboard


class TestOutputFormatting:
    """Tests for output formatting."""

    @pytest.fixture
    def mock_args(self):
        """Create mock arguments."""
        args = MagicMock()
        args.project = "test-project"
        args.projects_dir = "projects"
        args.phase = "visual"
        args.scene = 1
        args.force = False
        args.skip_validation = True
        args.quiet = False
        return args

    def test_summary_includes_scene_info(self, capsys):
        """Test that summary includes scene information."""
        from src.refine.command import _print_refinement_summary
        from src.refine.models import SceneRefinementResult

        results = [
            SceneRefinementResult(
                scene_id="scene1",
                scene_title="Test Scene 1",
                scene_file=Path("/test.tsx"),
                verification_passed=True,
                issues_found=[],
                fixes_applied=[],
            )
        ]

        _print_refinement_summary(results)
        captured = capsys.readouterr()

        assert "Test Scene 1" in captured.out
        assert "SUMMARY" in captured.out

    def test_summary_shows_pass_fail(self, capsys):
        """Test that summary shows pass/fail status."""
        from src.refine.command import _print_refinement_summary
        from src.refine.models import SceneRefinementResult, Issue, IssueType

        results = [
            SceneRefinementResult(
                scene_id="scene1",
                scene_title="Passed Scene",
                scene_file=Path("/test.tsx"),
                verification_passed=True,
            ),
            SceneRefinementResult(
                scene_id="scene2",
                scene_title="Failed Scene",
                scene_file=Path("/test2.tsx"),
                verification_passed=False,
                issues_found=[
                    Issue(
                        beat_index=0,
                        principle_violated=IssueType.VISUAL_HIERARCHY,
                        description="Test issue",
                    )
                ],
            ),
        ]

        _print_refinement_summary(results)
        captured = capsys.readouterr()

        assert "✅" in captured.out  # Passed
        assert "⚠️" in captured.out  # Failed
        assert "Passed: 1/2" in captured.out

    def test_summary_counts_issues_and_fixes(self, capsys):
        """Test that summary counts issues and fixes."""
        from src.refine.command import _print_refinement_summary
        from src.refine.models import SceneRefinementResult, Issue, IssueType, Fix, FixStatus

        issue = Issue(
            beat_index=0,
            principle_violated=IssueType.VISUAL_HIERARCHY,
            description="Test issue",
        )
        fix = Fix(
            issue=issue,
            file_path=Path("/test.tsx"),
            description="Test fix",
            code_change="// change",
            status=FixStatus.APPLIED,
        )

        results = [
            SceneRefinementResult(
                scene_id="scene1",
                scene_title="Test Scene",
                scene_file=Path("/test.tsx"),
                verification_passed=True,
                issues_found=[issue],
                fixes_applied=[fix],
            )
        ]

        _print_refinement_summary(results)
        captured = capsys.readouterr()

        assert "Issues found: 1" in captured.out
        assert "Fixes applied: 1" in captured.out
