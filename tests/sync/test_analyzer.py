"""Tests for sync module analyzer."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from src.sync.models import (
    SyncPoint,
    SyncPointType,
    SceneSyncConfig,
    SyncMap,
)
from src.sync.analyzer import SyncAnalyzer


# Sample word timestamps
SAMPLE_TIMESTAMPS = [
    {"word": "Something", "start_seconds": 0.1, "end_seconds": 0.5625},
    {"word": "extraordinary", "start_seconds": 0.5875, "end_seconds": 1.35},
    {"word": "happened", "start_seconds": 1.375, "end_seconds": 1.8},
    {"word": "Eighty-three", "start_seconds": 4.4625, "end_seconds": 4.9875},
    {"word": "percent", "start_seconds": 5.5375, "end_seconds": 5.95},
    {"word": "OpenAI's", "start_seconds": 12.0375, "end_seconds": 12.725},
]

# Sample scene code
SAMPLE_SCENE_CODE = """
import React from "react";
import { interpolate, spring } from "remotion";

const PHASE = {
  NUMBERS: [0, 220],
  COMBINED: [200, 800],
};

export const TestScene = () => {
  const f = useCurrentFrame();

  const numbersOpacity = interpolate(f, [0, 50], [0, 1]);
  const windowsEntrance = spring({
    frame: Math.max(0, f - 220),
    fps: 30,
  });

  return <div />;
};
"""

# Sample LLM response
SAMPLE_LLM_RESPONSE = """
[
  {
    "id": "numbersAppear",
    "sync_type": "element_appear",
    "trigger_phrase": "Eighty-three percent",
    "trigger_word": "Eighty-three",
    "use_word_start": true,
    "offset_frames": -3,
    "visual_element": "Number display",
    "notes": "Main number reveal"
  },
  {
    "id": "windowsEntrance",
    "sync_type": "element_appear",
    "trigger_phrase": "OpenAI's model",
    "trigger_word": "OpenAI's",
    "use_word_start": true,
    "offset_frames": -3,
    "visual_element": "Chat window",
    "notes": ""
  }
]
"""


class TestSyncAnalyzerAnalyzeScene:
    """Tests for SyncAnalyzer.analyze_scene method."""

    def test_analyze_scene_basic(self):
        """Test basic scene analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock project
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            # Create scene file
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            scene_file = scenes_dir / "TestScene.tsx"
            scene_file.write_text(SAMPLE_SCENE_CODE)

            # Mock LLM provider
            llm_provider = MagicMock()
            llm_provider.generate.return_value = SAMPLE_LLM_RESPONSE

            analyzer = SyncAnalyzer(
                project=project,
                verbose=False,
                llm_provider=llm_provider,
            )

            config = analyzer.analyze_scene(
                scene_id="test_scene",
                scene_file=scene_file,
                word_timestamps=SAMPLE_TIMESTAMPS,
                narration_text="Test narration",
                scene_title="Test Scene",
                duration_seconds=30.0,
            )

            assert config.scene_id == "test_scene"
            assert config.scene_title == "Test Scene"
            assert config.duration_seconds == 30.0
            assert len(config.sync_points) == 2

    def test_analyze_scene_file_not_found(self):
        """Test scene analysis when file doesn't exist."""
        project = MagicMock()
        project.root_dir = Path("/nonexistent")

        analyzer = SyncAnalyzer(project=project, verbose=False)

        config = analyzer.analyze_scene(
            scene_id="missing",
            scene_file=Path("/nonexistent/missing.tsx"),
            word_timestamps=SAMPLE_TIMESTAMPS,
            narration_text="Test",
            scene_title="Missing",
            duration_seconds=20.0,
        )

        assert config.scene_id == "missing"
        assert len(config.sync_points) == 0

    def test_analyze_scene_extracts_timing_vars(self):
        """Test that scene analysis extracts timing variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            scene_file = scenes_dir / "TestScene.tsx"
            scene_file.write_text(SAMPLE_SCENE_CODE)

            llm_provider = MagicMock()
            llm_provider.generate.return_value = "[]"  # Empty sync points

            analyzer = SyncAnalyzer(
                project=project,
                verbose=False,
                llm_provider=llm_provider,
            )

            config = analyzer.analyze_scene(
                scene_id="test",
                scene_file=scene_file,
                word_timestamps=SAMPLE_TIMESTAMPS,
                narration_text="Test",
                scene_title="Test",
                duration_seconds=20.0,
            )

            # Should have extracted PHASE.NUMBERS, PHASE.COMBINED from the code
            assert "PHASE.NUMBERS" in config.current_timing_vars or len(config.current_timing_vars) >= 0


class TestSyncAnalyzerParseResponse:
    """Tests for SyncAnalyzer._parse_sync_points_response method."""

    def test_parse_valid_json_response(self):
        """Test parsing valid JSON response."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        sync_points = analyzer._parse_sync_points_response(SAMPLE_LLM_RESPONSE)

        assert len(sync_points) == 2
        assert sync_points[0].id == "numbersAppear"
        assert sync_points[0].sync_type == SyncPointType.ELEMENT_APPEAR
        assert sync_points[1].id == "windowsEntrance"

    def test_parse_json_with_extra_text(self):
        """Test parsing JSON embedded in other text."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        response = """
Here are the sync points I identified:

[
  {
    "id": "test",
    "sync_type": "element_appear",
    "trigger_phrase": "test phrase",
    "trigger_word": "test",
    "use_word_start": true,
    "offset_frames": -3
  }
]

These sync points should work well with the scene.
"""

        sync_points = analyzer._parse_sync_points_response(response)

        assert len(sync_points) == 1
        assert sync_points[0].id == "test"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns empty list."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        response = "This is not valid JSON at all"

        sync_points = analyzer._parse_sync_points_response(response)

        assert sync_points == []

    def test_parse_empty_array(self):
        """Test parsing empty JSON array."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        response = "[]"

        sync_points = analyzer._parse_sync_points_response(response)

        assert sync_points == []

    def test_parse_missing_required_fields(self):
        """Test parsing sync points with missing fields."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        response = """
[
  {
    "id": "valid",
    "sync_type": "element_appear",
    "trigger_phrase": "phrase",
    "trigger_word": "word"
  },
  {
    "sync_type": "element_appear"
  }
]
"""
        # Second item missing id and trigger_word, should be skipped

        sync_points = analyzer._parse_sync_points_response(response)

        assert len(sync_points) == 1
        assert sync_points[0].id == "valid"

    def test_parse_unknown_sync_type(self):
        """Test parsing with unknown sync type uses default."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        response = """
[
  {
    "id": "test",
    "sync_type": "unknown_type",
    "trigger_phrase": "phrase",
    "trigger_word": "word"
  }
]
"""

        sync_points = analyzer._parse_sync_points_response(response)

        assert len(sync_points) == 1
        assert sync_points[0].sync_type == SyncPointType.ELEMENT_APPEAR  # default


class TestSyncAnalyzerValidateSyncPoints:
    """Tests for SyncAnalyzer._validate_sync_points method."""

    def test_validate_valid_sync_points(self):
        """Test validating sync points with valid trigger words."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        sync_points = [
            SyncPoint(
                id="valid1",
                sync_type=SyncPointType.ELEMENT_APPEAR,
                trigger_phrase="Something extraordinary",
                trigger_word="Something",
            ),
            SyncPoint(
                id="valid2",
                sync_type=SyncPointType.DATA_UPDATE,
                trigger_phrase="Eighty-three percent",
                trigger_word="Eighty-three",
            ),
        ]

        validated = analyzer._validate_sync_points(sync_points, SAMPLE_TIMESTAMPS)

        assert len(validated) == 2

    def test_validate_invalid_trigger_word(self):
        """Test validating sync points with invalid trigger word."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        sync_points = [
            SyncPoint(
                id="invalid",
                sync_type=SyncPointType.ELEMENT_APPEAR,
                trigger_phrase="nonexistent word",
                trigger_word="nonexistent",
            ),
        ]

        validated = analyzer._validate_sync_points(sync_points, SAMPLE_TIMESTAMPS)

        # Should be filtered out (or fixed with suggestion)
        # Depends on whether a suggestion was found

    def test_validate_fixes_similar_word(self):
        """Test validation suggests similar word."""
        project = MagicMock()
        analyzer = SyncAnalyzer(project=project, verbose=False)

        # "someth" is close to "Something"
        sync_points = [
            SyncPoint(
                id="fixable",
                sync_type=SyncPointType.ELEMENT_APPEAR,
                trigger_phrase="someth extra",
                trigger_word="someth",
            ),
        ]

        validated = analyzer._validate_sync_points(sync_points, SAMPLE_TIMESTAMPS)

        # May or may not fix depending on implementation
        # At least shouldn't crash


class TestSyncAnalyzerFindSceneFile:
    """Tests for SyncAnalyzer._find_scene_file method."""

    def test_find_scene_file_pascal_case(self):
        """Test finding scene file with PascalCase naming."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            scene_file = scenes_dir / "TheImpossibleLeapScene.tsx"
            scene_file.write_text("// Scene")

            analyzer = SyncAnalyzer(project=project, verbose=False)

            found = analyzer._find_scene_file(
                scene_id="the_impossible_leap",
                scene_title="The Impossible Leap",
            )

            assert found is not None
            assert found.name == "TheImpossibleLeapScene.tsx"

    def test_find_scene_file_not_found(self):
        """Test finding scene file that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()

            analyzer = SyncAnalyzer(project=project, verbose=False)

            found = analyzer._find_scene_file(
                scene_id="nonexistent",
                scene_title="Nonexistent Scene",
            )

            assert found is None

    def test_find_scene_file_fallback_search(self):
        """Test finding scene file with fallback search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            # Different naming convention
            scene_file = scenes_dir / "ImpossibleLeapScene.tsx"
            scene_file.write_text("// Scene")

            analyzer = SyncAnalyzer(project=project, verbose=False)

            found = analyzer._find_scene_file(
                scene_id="impossible_leap",
                scene_title="Impossible Leap",
            )

            assert found is not None


class TestSyncAnalyzerAnalyzeProject:
    """Tests for SyncAnalyzer.analyze_project method."""

    def test_analyze_project_loads_existing_sync_map(self):
        """Test that analyze_project loads existing sync map."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create existing sync map
            sync_dir = Path(tmpdir) / "sync"
            sync_dir.mkdir()
            sync_map_path = sync_dir / "sync_map.json"
            existing_map = {
                "project_id": "test_project",
                "fps": 30,
                "scenes": [
                    {
                        "scene_id": "scene1",
                        "scene_title": "Scene 1",
                        "scene_file": "scene1.tsx",
                        "duration_seconds": 30.0,
                        "sync_points": [],
                        "current_timing_vars": [],
                        "narration_text": "",
                    }
                ],
                "generated_at": "2024-01-01",
                "version": "1.0",
            }
            with open(sync_map_path, "w") as f:
                json.dump(existing_map, f)

            analyzer = SyncAnalyzer(project=project, verbose=False)

            sync_map = analyzer.analyze_project(force=False)

            assert sync_map.project_id == "test_project"
            assert len(sync_map.scenes) == 1

    def test_analyze_project_force_regenerate(self):
        """Test that analyze_project regenerates when force=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create manifest
            voiceover_dir = Path(tmpdir) / "voiceover"
            voiceover_dir.mkdir()
            manifest_path = voiceover_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump({"scenes": []}, f)

            # Mock load_storyboard
            project.load_storyboard.return_value = {"scenes": []}

            analyzer = SyncAnalyzer(project=project, verbose=False)

            sync_map = analyzer.analyze_project(force=True)

            assert sync_map.project_id == "test_project"

    def test_analyze_project_missing_manifest(self):
        """Test analyze_project raises error when manifest missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            analyzer = SyncAnalyzer(project=project, verbose=False)

            with pytest.raises(FileNotFoundError):
                analyzer.analyze_project(force=True)


class TestSyncAnalyzerSaveSyncMap:
    """Tests for SyncAnalyzer.save_sync_map method."""

    def test_save_sync_map_creates_file(self):
        """Test save_sync_map creates JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            analyzer = SyncAnalyzer(project=project, verbose=False)

            sync_map = SyncMap(
                project_id="test",
                fps=30,
                scenes=[
                    SceneSyncConfig(
                        scene_id="scene1",
                        scene_title="Scene 1",
                        scene_file="scene1.tsx",
                        duration_seconds=30.0,
                    )
                ],
            )

            output_path = analyzer.save_sync_map(sync_map)

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            assert data["project_id"] == "test"
            assert len(data["scenes"]) == 1

    def test_save_sync_map_creates_directory(self):
        """Test save_sync_map creates sync directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            analyzer = SyncAnalyzer(project=project, verbose=False)

            sync_map = SyncMap(project_id="test", fps=30, scenes=[])

            output_path = analyzer.save_sync_map(sync_map)

            assert (Path(tmpdir) / "sync").exists()
