"""Tests for sync module data models."""

import pytest
from pathlib import Path

from src.sync.models import (
    SyncPoint,
    SyncPointType,
    SceneSyncConfig,
    SyncMap,
    SceneTimingBlock,
    ProjectTiming,
    MigrationPlan,
    SyncPhaseResult,
)


class TestSyncPoint:
    """Tests for SyncPoint model."""

    def test_create_sync_point(self):
        """Test basic SyncPoint creation."""
        sp = SyncPoint(
            id="numbersAppear",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="Eighty-three point three percent",
            trigger_word="Eighty-three",
        )
        assert sp.id == "numbersAppear"
        assert sp.sync_type == SyncPointType.ELEMENT_APPEAR
        assert sp.trigger_phrase == "Eighty-three point three percent"
        assert sp.trigger_word == "Eighty-three"
        assert sp.use_word_start is True  # default
        assert sp.offset_frames == -3  # default

    def test_sync_point_with_custom_offset(self):
        """Test SyncPoint with custom offset."""
        sp = SyncPoint(
            id="chartReveal",
            sync_type=SyncPointType.DATA_UPDATE,
            trigger_phrase="the data shows",
            trigger_word="data",
            use_word_start=False,
            offset_frames=-5,
        )
        assert sp.use_word_start is False
        assert sp.offset_frames == -5

    def test_sync_point_to_dict(self):
        """Test SyncPoint serialization to dict."""
        sp = SyncPoint(
            id="test",
            sync_type=SyncPointType.PHASE_TRANSITION,
            trigger_phrase="test phrase",
            trigger_word="phrase",
            visual_element="Test element",
            notes="Test notes",
        )
        data = sp.to_dict()
        assert data["id"] == "test"
        assert data["sync_type"] == "phase_transition"
        assert data["visual_element"] == "Test element"
        assert data["notes"] == "Test notes"

    def test_sync_point_from_dict(self):
        """Test SyncPoint deserialization from dict."""
        data = {
            "id": "windowsEntrance",
            "sync_type": "element_appear",
            "trigger_phrase": "OpenAI's o1",
            "trigger_word": "OpenAI's",
            "use_word_start": True,
            "offset_frames": -3,
            "visual_element": "ChatWindow component",
            "notes": "",
        }
        sp = SyncPoint.from_dict(data)
        assert sp.id == "windowsEntrance"
        assert sp.sync_type == SyncPointType.ELEMENT_APPEAR
        assert sp.trigger_word == "OpenAI's"

    def test_sync_point_roundtrip(self):
        """Test SyncPoint serialization roundtrip."""
        original = SyncPoint(
            id="emphasisMoment",
            sync_type=SyncPointType.EMPHASIS,
            trigger_phrase="extraordinary happened",
            trigger_word="extraordinary",
            use_word_start=True,
            offset_frames=-2,
            visual_element="Glow effect",
            notes="Peak emphasis",
        )
        restored = SyncPoint.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.sync_type == original.sync_type
        assert restored.trigger_phrase == original.trigger_phrase
        assert restored.offset_frames == original.offset_frames


class TestSyncPointType:
    """Tests for SyncPointType enum."""

    def test_all_sync_types_exist(self):
        """Test that all expected sync types are defined."""
        expected = [
            "element_appear",
            "element_exit",
            "phase_transition",
            "text_reveal",
            "animation_start",
            "animation_peak",
            "data_update",
            "emphasis",
        ]
        for name in expected:
            assert SyncPointType(name) is not None

    def test_sync_type_value(self):
        """Test sync type string values."""
        assert SyncPointType.ELEMENT_APPEAR.value == "element_appear"
        assert SyncPointType.PHASE_TRANSITION.value == "phase_transition"


class TestSceneSyncConfig:
    """Tests for SceneSyncConfig model."""

    def test_create_scene_sync_config(self):
        """Test basic SceneSyncConfig creation."""
        config = SceneSyncConfig(
            scene_id="the_impossible_leap",
            scene_title="The Impossible Leap",
            scene_file="scenes/TheImpossibleLeapScene.tsx",
            duration_seconds=37.0,
        )
        assert config.scene_id == "the_impossible_leap"
        assert config.duration_seconds == 37.0
        assert config.sync_points == []

    def test_scene_sync_config_with_sync_points(self):
        """Test SceneSyncConfig with sync points."""
        sp1 = SyncPoint(
            id="point1",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="test",
            trigger_word="test",
        )
        sp2 = SyncPoint(
            id="point2",
            sync_type=SyncPointType.ELEMENT_EXIT,
            trigger_phrase="test2",
            trigger_word="test2",
        )
        config = SceneSyncConfig(
            scene_id="test",
            scene_title="Test Scene",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp1, sp2],
        )
        assert len(config.sync_points) == 2

    def test_scene_sync_config_serialization(self):
        """Test SceneSyncConfig serialization."""
        sp = SyncPoint(
            id="test",
            sync_type=SyncPointType.TEXT_REVEAL,
            trigger_phrase="phrase",
            trigger_word="word",
        )
        config = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test",
            scene_file="test.tsx",
            duration_seconds=20.0,
            sync_points=[sp],
            current_timing_vars=["PHASE.START", "numbersAppear"],
            narration_text="Test narration",
        )
        data = config.to_dict()
        restored = SceneSyncConfig.from_dict(data)

        assert restored.scene_id == config.scene_id
        assert len(restored.sync_points) == 1
        assert restored.current_timing_vars == ["PHASE.START", "numbersAppear"]


class TestSyncMap:
    """Tests for SyncMap model."""

    def test_create_sync_map(self):
        """Test basic SyncMap creation."""
        sync_map = SyncMap(
            project_id="thinking-models",
            fps=30,
        )
        assert sync_map.project_id == "thinking-models"
        assert sync_map.fps == 30
        assert sync_map.scenes == []

    def test_sync_map_with_scenes(self):
        """Test SyncMap with scene configurations."""
        scene1 = SceneSyncConfig(
            scene_id="scene1",
            scene_title="Scene 1",
            scene_file="scene1.tsx",
            duration_seconds=30.0,
        )
        scene2 = SceneSyncConfig(
            scene_id="scene2",
            scene_title="Scene 2",
            scene_file="scene2.tsx",
            duration_seconds=45.0,
        )
        sync_map = SyncMap(
            project_id="test",
            fps=30,
            scenes=[scene1, scene2],
            generated_at="2024-01-23T12:00:00",
        )
        assert len(sync_map.scenes) == 2
        assert sync_map.generated_at == "2024-01-23T12:00:00"

    def test_sync_map_get_scene(self):
        """Test SyncMap.get_scene method."""
        scene1 = SceneSyncConfig(
            scene_id="the_impossible_leap",
            scene_title="The Impossible Leap",
            scene_file="leap.tsx",
            duration_seconds=37.0,
        )
        scene2 = SceneSyncConfig(
            scene_id="learning_from_outcomes",
            scene_title="Learning From Outcomes",
            scene_file="outcomes.tsx",
            duration_seconds=42.0,
        )
        sync_map = SyncMap(
            project_id="test",
            scenes=[scene1, scene2],
        )

        # Find existing scene
        found = sync_map.get_scene("the_impossible_leap")
        assert found is not None
        assert found.scene_title == "The Impossible Leap"

        # Return None for non-existent scene
        not_found = sync_map.get_scene("nonexistent")
        assert not_found is None

    def test_sync_map_serialization(self):
        """Test SyncMap serialization roundtrip."""
        sp = SyncPoint(
            id="test",
            sync_type=SyncPointType.ELEMENT_APPEAR,
            trigger_phrase="test",
            trigger_word="test",
        )
        scene = SceneSyncConfig(
            scene_id="test_scene",
            scene_title="Test",
            scene_file="test.tsx",
            duration_seconds=30.0,
            sync_points=[sp],
        )
        original = SyncMap(
            project_id="test_project",
            fps=30,
            scenes=[scene],
            generated_at="2024-01-23T12:00:00",
            version="1.0",
        )

        data = original.to_dict()
        restored = SyncMap.from_dict(data)

        assert restored.project_id == original.project_id
        assert restored.fps == original.fps
        assert len(restored.scenes) == 1
        assert len(restored.scenes[0].sync_points) == 1


class TestSceneTimingBlock:
    """Tests for SceneTimingBlock model."""

    def test_create_scene_timing_block(self):
        """Test basic SceneTimingBlock creation."""
        block = SceneTimingBlock(
            scene_id="test_scene",
            duration_frames=900,
            timing_constants={
                "numbersAppear": 120,
                "chartReveal": 450,
                "windowsEntrance": 220,
            },
        )
        assert block.scene_id == "test_scene"
        assert block.duration_frames == 900
        assert len(block.timing_constants) == 3
        assert block.timing_constants["numbersAppear"] == 120

    def test_scene_timing_block_with_warnings(self):
        """Test SceneTimingBlock with warnings."""
        block = SceneTimingBlock(
            scene_id="test",
            duration_frames=600,
            timing_constants={"fallback": 300},
            warnings=["Word 'missing' not found, using fallback"],
        )
        assert len(block.warnings) == 1

    def test_scene_timing_block_serialization(self):
        """Test SceneTimingBlock serialization."""
        block = SceneTimingBlock(
            scene_id="test",
            duration_frames=1200,
            timing_constants={"a": 100, "b": 200},
            warnings=["warning1"],
        )
        data = block.to_dict()

        assert data["scene_id"] == "test"
        assert data["duration_frames"] == 1200
        assert data["timing_constants"]["a"] == 100
        assert "warning1" in data["warnings"]


class TestProjectTiming:
    """Tests for ProjectTiming model."""

    def test_create_project_timing(self):
        """Test basic ProjectTiming creation."""
        timing = ProjectTiming(
            project_id="test",
            fps=30,
        )
        assert timing.project_id == "test"
        assert timing.fps == 30
        assert timing.scenes == []

    def test_project_timing_with_scenes(self):
        """Test ProjectTiming with scene timing blocks."""
        block1 = SceneTimingBlock(
            scene_id="scene1",
            duration_frames=900,
            timing_constants={"a": 100},
        )
        block2 = SceneTimingBlock(
            scene_id="scene2",
            duration_frames=1200,
            timing_constants={"b": 200},
        )
        timing = ProjectTiming(
            project_id="test",
            fps=30,
            scenes=[block1, block2],
        )
        assert len(timing.scenes) == 2


class TestMigrationPlan:
    """Tests for MigrationPlan model."""

    def test_create_migration_plan(self):
        """Test basic MigrationPlan creation."""
        plan = MigrationPlan(
            scene_id="test",
            scene_file=Path("test.tsx"),
            original_code="const x = 100;",
            migrated_code="const x = TIMING.test.x;",
        )
        assert plan.scene_id == "test"
        assert not plan.success  # default

    def test_migration_plan_success(self):
        """Test successful MigrationPlan."""
        plan = MigrationPlan(
            scene_id="test",
            scene_file=Path("test.tsx"),
            original_code="original",
            migrated_code="migrated",
            imports_added=["import { TIMING } from './timing';"],
            constants_replaced={"100": "TIMING.test.x"},
            success=True,
            backup_path=Path("test.backup.tsx"),
        )
        assert plan.success
        assert len(plan.imports_added) == 1
        assert plan.backup_path is not None

    def test_migration_plan_failure(self):
        """Test failed MigrationPlan."""
        plan = MigrationPlan(
            scene_id="test",
            scene_file=Path("test.tsx"),
            original_code="original",
            migrated_code="",
            success=False,
            error_message="TypeScript validation failed",
        )
        assert not plan.success
        assert plan.error_message == "TypeScript validation failed"

    def test_migration_plan_serialization(self):
        """Test MigrationPlan serialization."""
        plan = MigrationPlan(
            scene_id="test",
            scene_file=Path("/project/scenes/test.tsx"),
            original_code="original",
            migrated_code="migrated",
            imports_added=["import X"],
            constants_replaced={"1": "X"},
            success=True,
            backup_path=Path("/project/backups/test.bak"),
        )
        data = plan.to_dict()

        assert data["scene_id"] == "test"
        assert data["scene_file"] == "/project/scenes/test.tsx"
        assert data["success"] is True
        assert data["backup_path"] == "/project/backups/test.bak"


class TestSyncPhaseResult:
    """Tests for SyncPhaseResult model."""

    def test_create_sync_phase_result(self):
        """Test basic SyncPhaseResult creation."""
        result = SyncPhaseResult(project_id="test")
        assert result.project_id == "test"
        assert not result.success  # default
        assert not result.sync_map_generated  # default

    def test_sync_phase_result_success(self):
        """Test successful SyncPhaseResult."""
        plan = MigrationPlan(
            scene_id="scene1",
            scene_file=Path("scene1.tsx"),
            original_code="",
            migrated_code="",
            success=True,
        )
        result = SyncPhaseResult(
            project_id="test",
            sync_map_generated=True,
            timing_file_generated=True,
            scenes_migrated=1,
            total_scenes=1,
            sync_points_found=5,
            migration_results=[plan],
            sync_map_path=Path("/test/sync/sync_map.json"),
            timing_file_path=Path("/test/scenes/timing.ts"),
            success=True,
        )
        assert result.success
        assert result.sync_map_generated
        assert result.timing_file_generated
        assert result.scenes_migrated == 1

    def test_sync_phase_result_serialization(self):
        """Test SyncPhaseResult serialization roundtrip."""
        original = SyncPhaseResult(
            project_id="test",
            sync_map_generated=True,
            timing_file_generated=True,
            scenes_migrated=2,
            total_scenes=3,
            sync_points_found=10,
            success=True,
            warnings=["warning1", "warning2"],
        )
        data = original.to_dict()
        restored = SyncPhaseResult.from_dict(data)

        assert restored.project_id == original.project_id
        assert restored.sync_map_generated == original.sync_map_generated
        assert restored.scenes_migrated == original.scenes_migrated
        assert len(restored.warnings) == 2
