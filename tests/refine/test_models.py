"""Tests for refine models."""

import pytest
from pathlib import Path

from src.refine.models import (
    Beat,
    Issue,
    IssueType,
    Fix,
    FixStatus,
    SceneRefinementResult,
    RefinementResult,
    RefinementPhase,
    SyncIssue,
    SyncIssueType,
    ProjectSyncStatus,
)


class TestBeat:
    """Tests for Beat model."""

    def test_beat_creation(self):
        """Test creating a Beat."""
        beat = Beat(
            index=0,
            start_seconds=0,
            end_seconds=5,
            text="Test beat",
            expected_visual="Test visual",
        )
        assert beat.index == 0
        assert beat.start_seconds == 0
        assert beat.end_seconds == 5
        assert beat.text == "Test beat"
        assert beat.expected_visual == "Test visual"

    def test_beat_duration(self):
        """Test beat duration calculation."""
        beat = Beat(index=0, start_seconds=2.5, end_seconds=7.5, text="Test")
        assert beat.duration_seconds == 5.0

    def test_beat_mid_seconds(self):
        """Test beat mid point calculation."""
        beat = Beat(index=0, start_seconds=0, end_seconds=10, text="Test")
        assert beat.mid_seconds == 5.0

    def test_beat_to_dict(self):
        """Test Beat serialization."""
        beat = Beat(
            index=1,
            start_seconds=5,
            end_seconds=10,
            text="Test beat",
            expected_visual="Visual",
        )
        data = beat.to_dict()
        assert data["index"] == 1
        assert data["start_seconds"] == 5
        assert data["end_seconds"] == 10
        assert data["text"] == "Test beat"
        assert data["expected_visual"] == "Visual"

    def test_beat_from_dict(self):
        """Test Beat deserialization."""
        data = {
            "index": 2,
            "start_seconds": 10,
            "end_seconds": 15,
            "text": "Loaded beat",
            "expected_visual": "Loaded visual",
        }
        beat = Beat.from_dict(data)
        assert beat.index == 2
        assert beat.start_seconds == 10
        assert beat.end_seconds == 15
        assert beat.text == "Loaded beat"


class TestIssue:
    """Tests for Issue model."""

    def test_issue_creation(self):
        """Test creating an Issue."""
        issue = Issue(
            beat_index=0,
            principle_violated=IssueType.VISUAL_HIERARCHY,
            description="No clear focal point",
            severity="high",
        )
        assert issue.beat_index == 0
        assert issue.principle_violated == IssueType.VISUAL_HIERARCHY
        assert issue.description == "No clear focal point"
        assert issue.severity == "high"

    def test_issue_to_dict(self):
        """Test Issue serialization."""
        issue = Issue(
            beat_index=1,
            principle_violated=IssueType.PROGRESSIVE_DISCLOSURE,
            description="Elements appear too early",
            severity="medium",
            screenshot_path=Path("/tmp/screenshot.png"),
        )
        data = issue.to_dict()
        assert data["beat_index"] == 1
        assert data["principle_violated"] == "progressive_disclosure"
        assert data["severity"] == "medium"
        assert data["screenshot_path"] == "/tmp/screenshot.png"

    def test_issue_from_dict(self):
        """Test Issue deserialization."""
        data = {
            "beat_index": 2,
            "principle_violated": "show_dont_tell",
            "description": "Not showing the concept",
            "severity": "low",
        }
        issue = Issue.from_dict(data)
        assert issue.beat_index == 2
        assert issue.principle_violated == IssueType.SHOW_DONT_TELL


class TestFix:
    """Tests for Fix model."""

    def test_fix_creation(self):
        """Test creating a Fix."""
        issue = Issue(
            beat_index=0,
            principle_violated=IssueType.VISUAL_HIERARCHY,
            description="Test issue",
        )
        fix = Fix(
            issue=issue,
            file_path=Path("/path/to/scene.tsx"),
            description="Increase font size",
            code_change="fontSize: 64 -> 96",
            status=FixStatus.PENDING,
        )
        assert fix.issue == issue
        assert fix.file_path == Path("/path/to/scene.tsx")
        assert fix.status == FixStatus.PENDING

    def test_fix_to_dict(self):
        """Test Fix serialization."""
        issue = Issue(
            beat_index=0,
            principle_violated=IssueType.VISUAL_HIERARCHY,
            description="Test",
        )
        fix = Fix(
            issue=issue,
            file_path=Path("/scene.tsx"),
            description="Fix applied",
            code_change="change",
            status=FixStatus.APPLIED,
        )
        data = fix.to_dict()
        assert data["status"] == "applied"
        assert data["file_path"] == "/scene.tsx"


class TestSceneRefinementResult:
    """Tests for SceneRefinementResult model."""

    def test_result_success(self):
        """Test successful refinement result."""
        result = SceneRefinementResult(
            scene_id="scene1",
            scene_title="Test Scene",
            scene_file=Path("/scene.tsx"),
            verification_passed=True,
        )
        assert result.success is True

    def test_result_failure(self):
        """Test failed refinement result."""
        result = SceneRefinementResult(
            scene_id="scene1",
            scene_title="Test Scene",
            scene_file=Path("/scene.tsx"),
            verification_passed=False,
            error_message="Something went wrong",
        )
        assert result.success is False


class TestProjectSyncStatus:
    """Tests for ProjectSyncStatus model."""

    def test_synced_status(self):
        """Test synced project status."""
        status = ProjectSyncStatus(
            is_synced=True,
            storyboard_scene_count=5,
            narration_scene_count=5,
            voiceover_file_count=5,
            scene_file_count=5,
        )
        assert status.is_synced is True
        assert len(status.issues) == 0

    def test_unsynced_status(self):
        """Test unsynced project status with issues."""
        issues = [
            SyncIssue(
                issue_type=SyncIssueType.SCENE_COUNT_MISMATCH,
                description="Mismatch between storyboard and narrations",
            ),
            SyncIssue(
                issue_type=SyncIssueType.MISSING_VOICEOVER,
                description="Missing audio file",
                affected_scene="scene3",
            ),
        ]
        status = ProjectSyncStatus(
            is_synced=False,
            issues=issues,
            storyboard_scene_count=5,
            narration_scene_count=4,
        )
        assert status.is_synced is False
        assert len(status.issues) == 2


class TestIssueType:
    """Tests for IssueType enum."""

    def test_all_issue_types_exist(self):
        """Test that all 11 principle issue types exist plus 'other'."""
        expected_types = [
            "show_dont_tell",
            "animation_reveals",
            "progressive_disclosure",
            "text_complements",
            "visual_hierarchy",
            "breathing_room",
            "purposeful_motion",
            "emotional_resonance",
            "professional_polish",
            "sync_with_narration",
            "screen_space_utilization",
            "other",
        ]
        for type_name in expected_types:
            assert IssueType(type_name) is not None
