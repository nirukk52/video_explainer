"""Tests for sync module prompts and formatters."""

import pytest

from src.sync.prompts import (
    SYNC_ANALYSIS_SYSTEM_PROMPT,
    SYNC_ANALYSIS_USER_PROMPT,
    SCENE_MIGRATION_SYSTEM_PROMPT,
    SCENE_MIGRATION_USER_PROMPT,
    format_word_timestamps,
    format_timing_vars,
    format_timing_constants,
    format_sync_points,
)
from src.sync.models import SyncPoint, SyncPointType


class TestSyncAnalysisPrompts:
    """Tests for sync analysis prompts."""

    def test_system_prompt_has_sync_types(self):
        """Test system prompt documents sync types."""
        assert "element_appear" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "element_exit" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "phase_transition" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "text_reveal" in SYNC_ANALYSIS_SYSTEM_PROMPT

    def test_system_prompt_has_guidelines(self):
        """Test system prompt has analysis guidelines."""
        assert "interpolate" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "spring" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "trigger_word" in SYNC_ANALYSIS_SYSTEM_PROMPT

    def test_system_prompt_has_output_format(self):
        """Test system prompt specifies output format."""
        assert "JSON" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "id" in SYNC_ANALYSIS_SYSTEM_PROMPT
        assert "sync_type" in SYNC_ANALYSIS_SYSTEM_PROMPT

    def test_user_prompt_has_placeholders(self):
        """Test user prompt has necessary placeholders."""
        placeholders = [
            "scene_id",
            "scene_title",
            "duration_seconds",  # Note: may have format spec like :.2f
            "duration_frames",
            "fps",
            "narration_text",
            "word_timestamps_formatted",
            "scene_code",
            "timing_vars_formatted",
        ]
        for placeholder in placeholders:
            assert placeholder in SYNC_ANALYSIS_USER_PROMPT, f"Missing {placeholder}"

    def test_user_prompt_formatting(self):
        """Test user prompt can be formatted."""
        formatted = SYNC_ANALYSIS_USER_PROMPT.format(
            scene_id="test_scene",
            scene_title="Test Scene",
            duration_seconds=30.0,
            duration_frames=900,
            fps=30,
            narration_text="Test narration",
            word_timestamps_formatted="1. \"test\" [0.0s - 0.5s]",
            scene_code="const x = 1;",
            timing_vars_formatted="- x = 1",
        )

        assert "test_scene" in formatted
        assert "Test Scene" in formatted
        assert "30.0" in formatted


class TestMigrationPrompts:
    """Tests for scene migration prompts."""

    def test_system_prompt_has_rules(self):
        """Test system prompt has migration rules."""
        assert "TIMING" in SCENE_MIGRATION_SYSTEM_PROMPT
        assert "import" in SCENE_MIGRATION_SYSTEM_PROMPT.lower()
        assert "replace" in SCENE_MIGRATION_SYSTEM_PROMPT.lower()

    def test_system_prompt_has_examples(self):
        """Test system prompt has code examples."""
        assert "interpolate" in SCENE_MIGRATION_SYSTEM_PROMPT
        assert "spring" in SCENE_MIGRATION_SYSTEM_PROMPT

    def test_user_prompt_has_placeholders(self):
        """Test user prompt has necessary placeholders."""
        placeholders = [
            "{scene_id}",
            "{scene_title}",
            "{duration_frames}",
            "{timing_constants_formatted}",
            "{scene_code}",
            "{sync_points_formatted}",
        ]
        for placeholder in placeholders:
            assert placeholder in SCENE_MIGRATION_USER_PROMPT

    def test_user_prompt_formatting(self):
        """Test user prompt can be formatted."""
        formatted = SCENE_MIGRATION_USER_PROMPT.format(
            scene_id="test_scene",
            scene_title="Test Scene",
            duration_frames=900,
            timing_constants_formatted="  numbersAppear: 120,",
            scene_code="const x = 120;",
            sync_points_formatted="- **numbersAppear** (frame 120)",
        )

        assert "test_scene" in formatted
        assert "120" in formatted


class TestFormatWordTimestamps:
    """Tests for format_word_timestamps function."""

    def test_format_basic(self):
        """Test basic word timestamps formatting."""
        timestamps = [
            {"word": "Hello", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "world", "start_seconds": 0.5, "end_seconds": 1.0},
        ]

        result = format_word_timestamps(timestamps)

        assert '"Hello"' in result
        assert '"world"' in result
        assert "0.000s" in result
        assert "0.500s" in result

    def test_format_with_limit(self):
        """Test formatting with max_words limit."""
        timestamps = [
            {"word": f"word{i}", "start_seconds": i, "end_seconds": i + 0.5}
            for i in range(10)
        ]

        result = format_word_timestamps(timestamps, max_words=5)

        assert "word0" in result
        assert "word4" in result
        assert "... and 5 more words" in result

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_word_timestamps([])
        assert result == ""

    def test_format_preserves_order(self):
        """Test formatting preserves word order."""
        timestamps = [
            {"word": "first", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "second", "start_seconds": 0.5, "end_seconds": 1.0},
            {"word": "third", "start_seconds": 1.0, "end_seconds": 1.5},
        ]

        result = format_word_timestamps(timestamps)

        first_pos = result.find("first")
        second_pos = result.find("second")
        third_pos = result.find("third")

        assert first_pos < second_pos < third_pos


class TestFormatTimingVars:
    """Tests for format_timing_vars function."""

    def test_format_basic(self):
        """Test basic timing vars formatting."""
        timing_vars = [
            {"name": "numbersAppear", "value": 120, "type": "simple", "line": 5},
            {"name": "PHASE.NUMBERS", "value": 220, "type": "object_property", "line": 3},
        ]

        result = format_timing_vars(timing_vars)

        assert "numbersAppear" in result
        assert "120" in result
        assert "PHASE.NUMBERS" in result
        assert "line 5" in result

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_timing_vars([])
        assert "No timing variables detected" in result

    def test_format_includes_type(self):
        """Test formatting includes variable type."""
        timing_vars = [
            {"name": "test", "value": 100, "type": "interpolate", "line": 1},
        ]

        result = format_timing_vars(timing_vars)

        assert "interpolate" in result


class TestFormatTimingConstants:
    """Tests for format_timing_constants function."""

    def test_format_basic(self):
        """Test basic timing constants formatting."""
        constants = {
            "numbersAppear": 120,
            "windowsEntrance": 220,
            "chartReveal": 450,
        }

        result = format_timing_constants(constants)

        assert "numbersAppear: 120" in result
        assert "windowsEntrance: 220" in result
        assert "chartReveal: 450" in result

    def test_format_empty_dict(self):
        """Test formatting empty dict."""
        result = format_timing_constants({})
        assert result == ""

    def test_format_indentation(self):
        """Test formatting has proper indentation."""
        constants = {"test": 100}

        result = format_timing_constants(constants)

        assert result.startswith("  ")


class TestFormatSyncPoints:
    """Tests for format_sync_points function."""

    def test_format_sync_point_objects(self):
        """Test formatting SyncPoint objects."""
        sync_points = [
            SyncPoint(
                id="numbersAppear",
                sync_type=SyncPointType.ELEMENT_APPEAR,
                trigger_phrase="Eighty-three percent",
                trigger_word="Eighty-three",
                visual_element="Number display",
            ),
        ]

        result = format_sync_points(sync_points)

        assert "**numbersAppear**" in result
        assert "element_appear" in result
        assert "Eighty-three" in result

    def test_format_sync_point_dicts(self):
        """Test formatting sync point dicts."""
        sync_points = [
            {
                "id": "test",
                "sync_type": "data_update",
                "trigger_phrase": "test phrase",
                "trigger_word": "test",
                "visual_element": "Test element",
                "calculated_frame": 150,
            },
        ]

        result = format_sync_points(sync_points)

        assert "**test**" in result
        assert "frame 150" in result
        assert "data_update" in result

    def test_format_multiple_points(self):
        """Test formatting multiple sync points."""
        sync_points = [
            SyncPoint(
                id="point1",
                sync_type=SyncPointType.ELEMENT_APPEAR,
                trigger_phrase="first",
                trigger_word="first",
            ),
            SyncPoint(
                id="point2",
                sync_type=SyncPointType.ELEMENT_EXIT,
                trigger_phrase="second",
                trigger_word="second",
            ),
        ]

        result = format_sync_points(sync_points)

        assert "point1" in result
        assert "point2" in result

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_sync_points([])
        assert result == ""
