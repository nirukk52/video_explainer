"""Tests for sync module timing generator."""

import pytest
from pathlib import Path
import tempfile
import json

from src.sync.models import (
    SyncPoint,
    SyncPointType,
    SceneSyncConfig,
    SyncMap,
    SceneTimingBlock,
    ProjectTiming,
)
from src.sync.timing_generator import (
    generate_scene_timing,
    generate_project_timing,
    generate_timing_typescript,
    generate_timing_file,
)


# Sample word timestamps
SAMPLE_TIMESTAMPS = [
    {"word": "Something", "start_seconds": 0.1, "end_seconds": 0.5625},
    {"word": "extraordinary", "start_seconds": 0.5875, "end_seconds": 1.35},
    {"word": "Eighty-three", "start_seconds": 4.4625, "end_seconds": 4.9875},
    {"word": "percent", "start_seconds": 5.5375, "end_seconds": 5.95},
    {"word": "OpenAI's", "start_seconds": 12.0375, "end_seconds": 12.725},
    {"word": "o1", "start_seconds": 12.7375, "end_seconds": 13.0875},
]


class TestGenerateSceneTiming:
    """Tests for generate_scene_timing function."""

    def test_generate_timing_basic(self):
        """Test basic timing generation."""
        sp1 = SyncPoint(
            id="numbersAppear",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Eighty-three percent",
            trigger_word="Eighty-three",
            use_word_start=True,
            offset_frames=-3,
        )
        config = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test Scene",
            scene_file="test.tsx",
            duration_seconds=20.0,
            sync_points=[sp1],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        assert block.scene_id == "test_scene"
        assert block.duration_frames == 600  # 20 * 30
        assert "numbersAppear" in block.timing_constants
        # 4.4625 * 30 - 3 = ~130 frames
        assert block.timing_constants["numbersAppear"] > 0

    def test_generate_timing_multiple_points(self):
        """Test timing generation with multiple sync points."""
        sp1 = SyncPoint(
            id="intro",
            sync_type=SyncPointType.PHASE_TRANSITION,
            trigger_phrase="Something",
            trigger_word="Something",
        )
        sp2 = SyncPoint(
            id="numbersReveal",
            sync_type=SyncPointType.DATA_UPDATE,
            trigger_phrase="Eighty-three",
            trigger_word="Eighty-three",
        )
        sp3 = SyncPoint(
            id="windowsAppear",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="OpenAI's o1",
            trigger_word="OpenAI's",
        )

        config = SceneSyncConfig(
            scene_id="multi_point",
            scene_title="Multi Point Scene",
            scene_file="multi.tsx",
            duration_seconds=30.0,
            sync_points=[sp1, sp2, sp3],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # phase_transition sync points are now skipped (informational only)
        # so only 2 constants are generated (numbersReveal, windowsAppear)
        assert len(block.timing_constants) == 2
        assert "intro" not in block.timing_constants  # skipped as phase_transition
        assert block.timing_constants["numbersReveal"] < block.timing_constants["windowsAppear"]
        # Verify warning about skipped sync point
        assert any("intro" in w and "phase_transition" in w for w in block.warnings)

    def test_generate_timing_word_not_found(self):
        """Test timing generation when word not found (uses fallback)."""
        sp = SyncPoint(
            id="missingWord",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="nonexistent word",
            trigger_word="nonexistent",
        )
        config = SceneSyncConfig(
            scene_id="fallback_test",
            scene_title="Fallback Test",
            scene_file="test.tsx",
            duration_seconds=10.0,
            sync_points=[sp],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # Should use fallback (middle of scene)
        assert block.timing_constants["missingWord"] == 150  # 300 / 2
        assert len(block.warnings) > 0
        assert "not found" in block.warnings[0].lower()

    def test_generate_timing_with_offset(self):
        """Test timing generation respects offset."""
        sp = SyncPoint(
            id="anticipated",
            sync_type=SyncPointType.ANIMATION_START,
            trigger_phrase="Eighty-three",
            trigger_word="Eighty-three",
            offset_frames=-5,
        )
        config = SceneSyncConfig(
            scene_id="offset_test",
            scene_title="Offset Test",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # Frame should be word start minus 5
        # 4.4625 * 30 = ~133, minus 5 = 128
        expected = int(4.4625 * 30) - 5
        assert block.timing_constants["anticipated"] == expected

    def test_generate_timing_clamps_to_range(self):
        """Test timing generation clamps frames to valid range."""
        sp = SyncPoint(
            id="earlyTrigger",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Something",
            trigger_word="Something",
            offset_frames=-100,  # Very large negative offset
        )
        config = SceneSyncConfig(
            scene_id="clamp_test",
            scene_title="Clamp Test",
            scene_file="test.tsx",
            duration_seconds=10.0,
            sync_points=[sp],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # Should clamp to 0, not negative
        assert block.timing_constants["earlyTrigger"] >= 0


class TestGenerateProjectTiming:
    """Tests for generate_project_timing function."""

    def test_generate_project_timing_single_scene(self):
        """Test project timing with single scene."""
        sp = SyncPoint(
            id="test",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Something",
            trigger_word="Something",
        )
        scene = SceneSyncConfig(
            scene_id="scene1",
            scene_title="Scene 1",
            scene_file="scene1.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )
        sync_map = SyncMap(
            project_id="test_project",
            fps=30,
            scenes=[scene],
        )
        manifest = {
            "scenes": [
                {
                    "scene_id": "scene1",
                    "word_timestamps": SAMPLE_TIMESTAMPS,
                }
            ]
        }

        timing = generate_project_timing(sync_map, manifest, fps=30)

        assert timing.project_id == "test_project"
        assert timing.fps == 30
        assert len(timing.scenes) == 1
        assert timing.scenes[0].scene_id == "scene1"

    def test_generate_project_timing_multiple_scenes(self):
        """Test project timing with multiple scenes."""
        sp1 = SyncPoint(
            id="a",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Something",
            trigger_word="Something",
        )
        sp2 = SyncPoint(
            id="b",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="extraordinary",
            trigger_word="extraordinary",
        )
        scene1 = SceneSyncConfig(
            scene_id="scene1",
            scene_title="Scene 1",
            scene_file="scene1.tsx",
            duration_seconds=20.0,
            sync_points=[sp1],
        )
        scene2 = SceneSyncConfig(
            scene_id="scene2",
            scene_title="Scene 2",
            scene_file="scene2.tsx",
            duration_seconds=25.0,
            sync_points=[sp2],
        )
        sync_map = SyncMap(
            project_id="multi",
            fps=30,
            scenes=[scene1, scene2],
        )
        manifest = {
            "scenes": [
                {"scene_id": "scene1", "word_timestamps": SAMPLE_TIMESTAMPS},
                {"scene_id": "scene2", "word_timestamps": SAMPLE_TIMESTAMPS},
            ]
        }

        timing = generate_project_timing(sync_map, manifest, fps=30)

        assert len(timing.scenes) == 2
        assert timing.scenes[0].duration_frames == 600
        assert timing.scenes[1].duration_frames == 750


class TestGenerateTimingTypescript:
    """Tests for generate_timing_typescript function."""

    def test_generate_typescript_basic(self):
        """Test basic TypeScript generation."""
        block = SceneTimingBlock(
            scene_id="the_impossible_leap",
            duration_frames=1112,
            timing_constants={
                "numbersAppear": 129,
                "vsAppear": 176,
                "windowsEntrance": 356,
            },
        )
        timing = ProjectTiming(
            project_id="test",
            fps=30,
            scenes=[block],
        )

        ts_code = generate_timing_typescript(timing)

        # Check structure
        assert "export const TIMING" in ts_code
        assert "as const" in ts_code
        assert "the_impossible_leap:" in ts_code
        assert "duration: 1112" in ts_code
        assert "numbersAppear: 129" in ts_code
        assert "vsAppear: 176" in ts_code
        assert "windowsEntrance: 356" in ts_code

    def test_generate_typescript_header_comments(self):
        """Test TypeScript has header comments."""
        timing = ProjectTiming(
            project_id="test",
            fps=30,
            scenes=[
                SceneTimingBlock(scene_id="test", duration_frames=100, timing_constants={})
            ],
        )

        ts_code = generate_timing_typescript(timing)

        assert "Auto-generated" in ts_code
        assert "DO NOT EDIT MANUALLY" in ts_code

    def test_generate_typescript_type_helpers(self):
        """Test TypeScript includes type helpers."""
        timing = ProjectTiming(
            project_id="test",
            fps=30,
            scenes=[
                SceneTimingBlock(scene_id="test", duration_frames=100, timing_constants={})
            ],
        )

        ts_code = generate_timing_typescript(timing)

        assert "export type SceneTiming" in ts_code
        assert "export type SceneId" in ts_code

    def test_generate_typescript_multiple_scenes(self):
        """Test TypeScript with multiple scenes."""
        blocks = [
            SceneTimingBlock(
                scene_id="scene1",
                duration_frames=900,
                timing_constants={"a": 100, "b": 200},
            ),
            SceneTimingBlock(
                scene_id="scene2",
                duration_frames=1200,
                timing_constants={"c": 300, "d": 400},
            ),
        ]
        timing = ProjectTiming(project_id="test", fps=30, scenes=blocks)

        ts_code = generate_timing_typescript(timing)

        assert "scene1:" in ts_code
        assert "scene2:" in ts_code
        assert "a: 100" in ts_code
        assert "c: 300" in ts_code

    def test_generate_typescript_constants_sorted(self):
        """Test that timing constants are sorted alphabetically."""
        block = SceneTimingBlock(
            scene_id="test",
            duration_frames=500,
            timing_constants={
                "zebra": 100,
                "alpha": 200,
                "middle": 300,
            },
        )
        timing = ProjectTiming(project_id="test", fps=30, scenes=[block])

        ts_code = generate_timing_typescript(timing)

        # Find positions
        alpha_pos = ts_code.find("alpha:")
        middle_pos = ts_code.find("middle:")
        zebra_pos = ts_code.find("zebra:")

        assert alpha_pos < middle_pos < zebra_pos


class TestGenerateTimingFile:
    """Tests for generate_timing_file function."""

    def test_generate_timing_file_creates_file(self):
        """Test timing file is created."""
        sp = SyncPoint(
            id="test",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Something",
            trigger_word="Something",
        )
        scene = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )
        sync_map = SyncMap(project_id="test", fps=30, scenes=[scene])
        manifest = {
            "scenes": [{"scene_id": "test_scene", "word_timestamps": SAMPLE_TIMESTAMPS}]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "scenes" / "timing.ts"

            timing = generate_timing_file(
                sync_map, manifest, output_path, fps=30, verbose=False
            )

            assert output_path.exists()
            content = output_path.read_text()
            assert "export const TIMING" in content
            assert "test_scene:" in content

    def test_generate_timing_file_creates_directory(self):
        """Test timing file creates parent directories."""
        sync_map = SyncMap(project_id="test", fps=30, scenes=[])
        manifest = {"scenes": []}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "timing.ts"

            generate_timing_file(sync_map, manifest, output_path, fps=30, verbose=False)

            assert output_path.parent.exists()

    def test_generate_timing_file_returns_timing_data(self):
        """Test timing file returns ProjectTiming data."""
        sp = SyncPoint(
            id="point1",
            sync_type=SyncPointType.DATA_UPDATE,
            trigger_phrase="Eighty-three",
            trigger_word="Eighty-three",
        )
        scene = SceneSyncConfig(
            scene_id="scene1",
            scene_title="Scene 1",
            scene_file="s1.tsx",
            duration_seconds=20.0,
            sync_points=[sp],
        )
        sync_map = SyncMap(project_id="test", fps=30, scenes=[scene])
        manifest = {
            "scenes": [{"scene_id": "scene1", "word_timestamps": SAMPLE_TIMESTAMPS}]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "timing.ts"

            timing = generate_timing_file(
                sync_map, manifest, output_path, fps=30, verbose=False
            )

            assert isinstance(timing, ProjectTiming)
            assert timing.project_id == "test"
            assert len(timing.scenes) == 1
            assert "point1" in timing.scenes[0].timing_constants


class TestTimingGeneratorClass:
    """Tests for TimingGenerator class."""

    def test_timing_generator_validate_timing_missing_file(self):
        """Test validation when timing file is missing."""
        from src.sync.timing_generator import TimingGenerator
        from unittest.mock import MagicMock

        project = MagicMock()
        project.root_dir = Path("/nonexistent")

        generator = TimingGenerator(project, verbose=False)
        issues = generator.validate_timing()

        assert len(issues) > 0
        assert "not found" in issues[0].lower()

    def test_timing_generator_validate_timing_valid_file(self):
        """Test validation with valid timing file."""
        from src.sync.timing_generator import TimingGenerator
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()

            timing_file = scenes_dir / "timing.ts"
            timing_file.write_text("""
export const TIMING = {
  test_scene: {
    duration: 900,
    start: 100,
  },
} as const;
""")

            project = MagicMock()
            project.root_dir = Path(tmpdir)

            generator = TimingGenerator(project, verbose=False)
            issues = generator.validate_timing()

            assert len(issues) == 0

    def test_timing_generator_validate_timing_missing_export(self):
        """Test validation catches missing export."""
        from src.sync.timing_generator import TimingGenerator
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()

            timing_file = scenes_dir / "timing.ts"
            timing_file.write_text("const TIMING = {};")  # Missing export

            project = MagicMock()
            project.root_dir = Path(tmpdir)

            generator = TimingGenerator(project, verbose=False)
            issues = generator.validate_timing()

            assert any("TIMING export" in issue for issue in issues)

    def test_timing_generator_validate_timing_negative_frames(self):
        """Test validation catches negative frame numbers."""
        from src.sync.timing_generator import TimingGenerator
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()

            timing_file = scenes_dir / "timing.ts"
            timing_file.write_text("""
export const TIMING = {
  test: {
    duration: 900,
    negative: -5,
  },
} as const;
""")

            project = MagicMock()
            project.root_dir = Path(tmpdir)

            generator = TimingGenerator(project, verbose=False)
            issues = generator.validate_timing()

            assert any("negative" in issue.lower() for issue in issues)


class TestInformationalSyncPointFiltering:
    """Tests for filtering informational sync points (phase_transition, animation_peak)."""

    def test_phase_transition_is_skipped(self):
        """Test that phase_transition sync points are skipped from timing constants."""
        sp = SyncPoint(
            id="phaseChange",
            sync_type=SyncPointType.PHASE_TRANSITION,
            trigger_phrase="Not an incremental",
            trigger_word="Not",
        )
        config = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test Scene",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # phase_transition should NOT be in timing constants
        assert "phaseChange" not in block.timing_constants
        # Should have warning about skipping
        assert any("phaseChange" in w and "phase_transition" in w for w in block.warnings)

    def test_animation_peak_is_skipped(self):
        """Test that animation_peak sync points are skipped from timing constants."""
        sp = SyncPoint(
            id="peakMoment",
            sync_type=SyncPointType.ANIMATION_PEAK,
            trigger_phrase="peak moment",
            trigger_word="peak",
        )
        config = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test Scene",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # animation_peak should NOT be in timing constants
        assert "peakMoment" not in block.timing_constants
        # Should have warning about skipping
        assert any("peakMoment" in w and "animation_peak" in w for w in block.warnings)

    def test_element_appear_is_not_skipped(self):
        """Test that element_appear sync points are included in timing constants."""
        sp = SyncPoint(
            id="elementAppears",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Something extraordinary",
            trigger_word="Something",
        )
        config = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test Scene",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # element_appear SHOULD be in timing constants
        assert "elementAppears" in block.timing_constants
        # Should NOT have warning about skipping for this type
        assert not any("elementAppears" in w and "informational" in w for w in block.warnings)

    def test_mixed_sync_types_filters_correctly(self):
        """Test that a mix of sync types filters correctly."""
        sync_points = [
            SyncPoint(
                id="intro",
                sync_type=SyncPointType.PHASE_TRANSITION,  # SKIP
                trigger_phrase="intro",
                trigger_word="Something",
            ),
            SyncPoint(
                id="numbersAppear",
                sync_type=SyncPointType.ELEMENT_APPEAR,  # INCLUDE
                trigger_phrase="Eighty-three",
                trigger_word="Eighty-three",
            ),
            SyncPoint(
                id="climax",
                sync_type=SyncPointType.ANIMATION_PEAK,  # SKIP
                trigger_phrase="peak",
                trigger_word="percent",
            ),
            SyncPoint(
                id="dataUpdate",
                sync_type=SyncPointType.DATA_UPDATE,  # INCLUDE
                trigger_phrase="OpenAI's",
                trigger_word="OpenAI's",
            ),
            SyncPoint(
                id="textReveal",
                sync_type=SyncPointType.TEXT_REVEAL,  # INCLUDE
                trigger_phrase="o1",
                trigger_word="o1",
            ),
        ]
        config = SceneSyncConfig(
            scene_id="mixed_test",
            scene_title="Mixed Test",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=sync_points,
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # Check that informational types are skipped
        assert "intro" not in block.timing_constants
        assert "climax" not in block.timing_constants

        # Check that actionable types are included
        assert "numbersAppear" in block.timing_constants
        assert "dataUpdate" in block.timing_constants
        assert "textReveal" in block.timing_constants

        # Check count
        assert len(block.timing_constants) == 3

        # Check warnings for skipped types
        assert any("intro" in w and "phase_transition" in w for w in block.warnings)
        assert any("climax" in w and "animation_peak" in w for w in block.warnings)

    def test_all_actionable_types_are_included(self):
        """Test that all actionable sync types are included in timing constants."""
        actionable_types = [
            SyncPointType.ELEMENT_APPEAR,
            SyncPointType.ELEMENT_EXIT,
            SyncPointType.TEXT_REVEAL,
            SyncPointType.ANIMATION_START,
            SyncPointType.DATA_UPDATE,
            SyncPointType.EMPHASIS,
        ]

        for sync_type in actionable_types:
            sp = SyncPoint(
                id=f"test_{sync_type.value}",
                sync_type=sync_type,
                trigger_phrase="Something",
                trigger_word="Something",
            )
            config = SceneSyncConfig(
                scene_id="test_scene",
                scene_title="Test Scene",
                scene_file="test.tsx",
                duration_seconds=30.0,
                sync_points=[sp],
            )

            block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

            assert f"test_{sync_type.value}" in block.timing_constants, \
                f"{sync_type.value} should be included in timing constants"

    def test_empty_after_filtering(self):
        """Test behavior when all sync points are filtered out."""
        sync_points = [
            SyncPoint(
                id="phase1",
                sync_type=SyncPointType.PHASE_TRANSITION,
                trigger_phrase="phase one",
                trigger_word="Something",
            ),
            SyncPoint(
                id="peak1",
                sync_type=SyncPointType.ANIMATION_PEAK,
                trigger_phrase="peak",
                trigger_word="Eighty-three",
            ),
        ]
        config = SceneSyncConfig(
            scene_id="all_filtered",
            scene_title="All Filtered",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=sync_points,
        )

        block = generate_scene_timing(config, SAMPLE_TIMESTAMPS, fps=30)

        # All sync points should be filtered, leaving empty timing constants
        assert len(block.timing_constants) == 0
        # But duration should still be set
        assert block.duration_frames == 900
        # Should have warnings for both skipped points
        assert len([w for w in block.warnings if "Skipped" in w]) == 2
