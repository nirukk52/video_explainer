"""Tests for sync module orchestrator."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from src.sync import SyncOrchestrator
from src.sync.models import (
    SyncPoint,
    SyncPointType,
    SceneSyncConfig,
    SyncMap,
    SceneTimingBlock,
    SyncPhaseResult,
)


class TestSyncOrchestratorInit:
    """Tests for SyncOrchestrator initialization."""

    def test_init_basic(self):
        """Test basic orchestrator initialization."""
        project = MagicMock()
        project.root_dir = Path("/test")
        project.id = "test_project"

        orchestrator = SyncOrchestrator(project=project, verbose=False)

        assert orchestrator.project == project
        assert orchestrator.verbose is False
        assert orchestrator.fps == 30
        assert orchestrator.analyzer is not None
        assert orchestrator.timing_generator is not None
        assert orchestrator.migrator is not None

    def test_init_with_llm_provider(self):
        """Test orchestrator with custom LLM provider."""
        project = MagicMock()
        project.root_dir = Path("/test")

        llm_provider = MagicMock()

        orchestrator = SyncOrchestrator(
            project=project,
            verbose=False,
            llm_provider=llm_provider,
        )

        assert orchestrator.llm_provider == llm_provider


class TestSyncOrchestratorGenerateSyncMap:
    """Tests for SyncOrchestrator.generate_sync_map method."""

    def test_generate_sync_map_basic(self):
        """Test basic sync map generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create necessary files
            voiceover_dir = Path(tmpdir) / "voiceover"
            voiceover_dir.mkdir()
            manifest_path = voiceover_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump({"scenes": []}, f)

            project.load_storyboard.return_value = {"scenes": []}

            orchestrator = SyncOrchestrator(project=project, verbose=False)

            sync_map = orchestrator.generate_sync_map()

            assert sync_map.project_id == "test_project"

    def test_generate_sync_map_loads_existing(self):
        """Test sync map generation loads existing map."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create existing sync map
            sync_dir = Path(tmpdir) / "sync"
            sync_dir.mkdir()
            existing_map = {
                "project_id": "test_project",
                "fps": 30,
                "scenes": [
                    {
                        "scene_id": "existing_scene",
                        "scene_title": "Existing",
                        "scene_file": "test.tsx",
                        "duration_seconds": 30.0,
                        "sync_points": [],
                        "current_timing_vars": [],
                        "narration_text": "",
                    }
                ],
                "generated_at": "2024-01-01",
                "version": "1.0",
            }
            with open(sync_dir / "sync_map.json", "w") as f:
                json.dump(existing_map, f)

            orchestrator = SyncOrchestrator(project=project, verbose=False)

            sync_map = orchestrator.generate_sync_map(force=False)

            assert len(sync_map.scenes) == 1
            assert sync_map.scenes[0].scene_id == "existing_scene"


class TestSyncOrchestratorGenerateTimingFile:
    """Tests for SyncOrchestrator.generate_timing_file method."""

    def test_generate_timing_file_basic(self):
        """Test basic timing file generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create sync map
            sync_dir = Path(tmpdir) / "sync"
            sync_dir.mkdir()
            sync_map = {
                "project_id": "test_project",
                "fps": 30,
                "scenes": [
                    {
                        "scene_id": "test_scene",
                        "scene_title": "Test",
                        "scene_file": "test.tsx",
                        "duration_seconds": 30.0,
                        "sync_points": [
                            {
                                "id": "test",
                                "sync_type": "element_appear",
                                "trigger_phrase": "test",
                                "trigger_word": "test",
                                "use_word_start": True,
                                "offset_frames": -3,
                            }
                        ],
                        "current_timing_vars": [],
                        "narration_text": "",
                    }
                ],
                "generated_at": "2024-01-01",
                "version": "1.0",
            }
            with open(sync_dir / "sync_map.json", "w") as f:
                json.dump(sync_map, f)

            # Create manifest
            voiceover_dir = Path(tmpdir) / "voiceover"
            voiceover_dir.mkdir()
            manifest = {
                "scenes": [
                    {
                        "scene_id": "test_scene",
                        "word_timestamps": [
                            {"word": "test", "start_seconds": 1.0, "end_seconds": 1.5}
                        ],
                    }
                ]
            }
            with open(voiceover_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)

            orchestrator = SyncOrchestrator(project=project, verbose=False)

            timing_path = orchestrator.generate_timing_file()

            assert timing_path.exists()
            content = timing_path.read_text()
            assert "export const TIMING" in content


class TestSyncOrchestratorMigrateScenes:
    """Tests for SyncOrchestrator.migrate_scenes method."""

    def test_migrate_scenes_dry_run(self):
        """Test scene migration in dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create directories
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            sync_dir = Path(tmpdir) / "sync"
            sync_dir.mkdir()

            # Create scene file
            scene_file = scenes_dir / "TestScene.tsx"
            scene_file.write_text("// Test scene")

            # Create sync map
            sync_map = {
                "project_id": "test_project",
                "fps": 30,
                "scenes": [
                    {
                        "scene_id": "test_scene",
                        "scene_title": "Test",
                        "scene_file": str(scene_file),
                        "duration_seconds": 30.0,
                        "sync_points": [],
                        "current_timing_vars": [],
                        "narration_text": "",
                    }
                ],
                "generated_at": "2024-01-01",
                "version": "1.0",
            }
            with open(sync_dir / "sync_map.json", "w") as f:
                json.dump(sync_map, f)

            # Create timing file
            timing_file = scenes_dir / "timing.ts"
            timing_file.write_text("export const TIMING = { test_scene: { duration: 900 } } as const;")

            # Mock the migrator's LLM
            orchestrator = SyncOrchestrator(project=project, verbose=False)
            orchestrator.migrator.llm_provider = MagicMock()
            orchestrator.migrator.llm_provider.generate.return_value = "import { TIMING } from './timing';\n// Test"

            results = orchestrator.migrate_scenes(dry_run=True)

            # Scene file should not be modified in dry run
            assert scene_file.read_text() == "// Test scene"

    def test_migrate_single_scene(self):
        """Test migrating a single scene by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create directories
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            sync_dir = Path(tmpdir) / "sync"
            sync_dir.mkdir()

            # Create scene files
            scene1 = scenes_dir / "Scene1.tsx"
            scene1.write_text("// Scene 1")
            scene2 = scenes_dir / "Scene2.tsx"
            scene2.write_text("// Scene 2")

            # Create sync map
            sync_map = {
                "project_id": "test_project",
                "fps": 30,
                "scenes": [
                    {
                        "scene_id": "scene1",
                        "scene_title": "Scene 1",
                        "scene_file": str(scene1),
                        "duration_seconds": 30.0,
                        "sync_points": [],
                        "current_timing_vars": [],
                        "narration_text": "",
                    },
                    {
                        "scene_id": "scene2",
                        "scene_title": "Scene 2",
                        "scene_file": str(scene2),
                        "duration_seconds": 25.0,
                        "sync_points": [],
                        "current_timing_vars": [],
                        "narration_text": "",
                    },
                ],
            }
            with open(sync_dir / "sync_map.json", "w") as f:
                json.dump(sync_map, f)

            # Create timing file
            timing_file = scenes_dir / "timing.ts"
            timing_file.write_text("""
export const TIMING = {
  scene1: { duration: 900 },
  scene2: { duration: 750 },
} as const;
""")

            orchestrator = SyncOrchestrator(project=project, verbose=False)
            orchestrator.migrator.llm_provider = MagicMock()
            orchestrator.migrator.llm_provider.generate.return_value = "import { TIMING } from './timing';\n// Scene"

            results = orchestrator.migrate_scenes(scene_id="scene1", dry_run=True)

            assert len(results) == 1
            assert "scene1" in results


class TestSyncOrchestratorRunFullSync:
    """Tests for SyncOrchestrator.run_full_sync method."""

    def test_run_full_sync_success(self):
        """Test full sync workflow succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Create directories
            scenes_dir = Path(tmpdir) / "scenes"
            scenes_dir.mkdir()
            voiceover_dir = Path(tmpdir) / "voiceover"
            voiceover_dir.mkdir()

            # Create scene file
            scene_file = scenes_dir / "TestScene.tsx"
            scene_file.write_text("// Test")

            # Create manifest
            manifest = {
                "scenes": [
                    {
                        "scene_id": "test_scene",
                        "duration_seconds": 30.0,
                        "word_timestamps": [
                            {"word": "test", "start_seconds": 1.0, "end_seconds": 1.5}
                        ],
                    }
                ]
            }
            with open(voiceover_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)

            # Mock storyboard
            project.load_storyboard.return_value = {
                "scenes": [
                    {
                        "id": "test_scene",
                        "title": "Test Scene",
                        "narration": "This is a test.",
                    }
                ]
            }

            # Create orchestrator with mocked components
            orchestrator = SyncOrchestrator(project=project, verbose=False)

            # Mock LLM
            llm_provider = MagicMock()
            llm_provider.generate.return_value = "[]"  # Empty sync points
            orchestrator.analyzer.llm_provider = llm_provider
            orchestrator.migrator.llm_provider = llm_provider

            result = orchestrator.run_full_sync(dry_run=True)

            assert isinstance(result, SyncPhaseResult)
            assert result.project_id == "test_project"

    def test_run_full_sync_error_handling(self):
        """Test full sync handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)
            project.id = "test_project"

            # Don't create any files - should cause error

            orchestrator = SyncOrchestrator(project=project, verbose=False)

            result = orchestrator.run_full_sync()

            assert not result.success
            assert result.error_message is not None


class TestSyncOrchestratorSaveResult:
    """Tests for SyncOrchestrator._save_result method."""

    def test_save_result_creates_file(self):
        """Test that result is saved to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            orchestrator = SyncOrchestrator(project=project, verbose=False)

            result = SyncPhaseResult(
                project_id="test",
                sync_map_generated=True,
                timing_file_generated=True,
                scenes_migrated=2,
                total_scenes=3,
                success=True,
            )

            output_path = orchestrator._save_result(result)

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            assert data["project_id"] == "test"
            assert data["success"] is True

    def test_save_result_creates_directory(self):
        """Test that sync directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = MagicMock()
            project.root_dir = Path(tmpdir)

            orchestrator = SyncOrchestrator(project=project, verbose=False)

            result = SyncPhaseResult(project_id="test")

            orchestrator._save_result(result)

            sync_dir = Path(tmpdir) / "sync"
            assert sync_dir.exists()


class TestModuleExports:
    """Tests for sync module exports."""

    def test_exports_orchestrator(self):
        """Test SyncOrchestrator is exported."""
        from src.sync import SyncOrchestrator
        assert SyncOrchestrator is not None

    def test_exports_models(self):
        """Test models are exported."""
        from src.sync import (
            SyncPoint,
            SyncPointType,
            SceneSyncConfig,
            SyncMap,
            SceneTimingBlock,
            ProjectTiming,
            MigrationPlan,
            SyncPhaseResult,
        )
        assert SyncPoint is not None
        assert SyncPointType is not None

    def test_exports_components(self):
        """Test component classes are exported."""
        from src.sync import SyncAnalyzer, TimingGenerator, SceneMigrator
        assert SyncAnalyzer is not None
        assert TimingGenerator is not None
        assert SceneMigrator is not None

    def test_exports_utils(self):
        """Test utility functions are exported."""
        from src.sync import (
            find_word_frame,
            find_word_frame_fuzzy,
            extract_timing_vars,
            validate_trigger_word,
        )
        assert find_word_frame is not None
        assert find_word_frame_fuzzy is not None
