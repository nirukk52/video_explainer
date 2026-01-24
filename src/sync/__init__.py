"""
Visual-Voiceover Sync Module.

This module provides automatic synchronization between visual animations
and voiceover timing in Remotion video projects.

Main components:
- SyncAnalyzer: LLM-based analysis of scene code to identify sync points
- TimingGenerator: Converts sync points to frame-accurate timing constants
- SceneMigrator: Transforms scene code to use centralized timing
- SyncOrchestrator: Coordinates the full sync workflow

Usage:
    from src.sync import SyncOrchestrator

    orchestrator = SyncOrchestrator(project)
    result = orchestrator.run_full_sync()
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    SyncPoint,
    SyncPointType,
    SceneSyncConfig,
    SyncMap,
    SceneTimingBlock,
    ProjectTiming,
    MigrationPlan,
    SyncPhaseResult,
    SyncStepStatus,
)
from .analyzer import SyncAnalyzer
from .timing_generator import TimingGenerator, generate_timing_file
from .scene_migrator import SceneMigrator
from .utils import (
    find_word_frame,
    find_word_frame_fuzzy,
    extract_timing_vars,
    validate_trigger_word,
)


__all__ = [
    # Models
    "SyncPoint",
    "SyncPointType",
    "SceneSyncConfig",
    "SyncMap",
    "SceneTimingBlock",
    "ProjectTiming",
    "MigrationPlan",
    "SyncPhaseResult",
    "SyncStepStatus",
    # Components
    "SyncAnalyzer",
    "TimingGenerator",
    "SceneMigrator",
    "SyncOrchestrator",
    # Utils
    "find_word_frame",
    "find_word_frame_fuzzy",
    "extract_timing_vars",
    "validate_trigger_word",
]


class SyncOrchestrator:
    """Orchestrator for the full visual-voiceover sync workflow."""

    def __init__(
        self,
        project,
        verbose: bool = True,
        llm_provider=None,
    ):
        """Initialize the sync orchestrator.

        Args:
            project: The Project instance.
            verbose: Whether to print progress messages.
            llm_provider: Optional LLM provider for analysis.
        """
        self.project = project
        self.verbose = verbose
        self.llm_provider = llm_provider
        self.fps = 30

        # Initialize components
        self.analyzer = SyncAnalyzer(
            project=project,
            verbose=verbose,
            llm_provider=llm_provider,
        )
        self.timing_generator = TimingGenerator(
            project=project,
            verbose=verbose,
        )
        self.migrator = SceneMigrator(
            project=project,
            verbose=verbose,
            llm_provider=llm_provider,
        )

    def generate_sync_map(self, force: bool = False) -> SyncMap:
        """Generate sync map by analyzing all scenes.

        Args:
            force: If True, regenerate even if sync_map exists.

        Returns:
            Generated SyncMap.
        """
        if self.verbose:
            print("\n📊 Step 1: Generating Sync Map")
            print("   " + "=" * 40)

        sync_map = self.analyzer.analyze_project(force=force)
        self.analyzer.save_sync_map(sync_map)

        return sync_map

    def generate_timing_file(
        self,
        sync_map: Optional[SyncMap] = None,
        force: bool = False,
    ) -> Path:
        """Generate timing.ts file from sync map.

        Args:
            sync_map: Optional sync map. If None, loads from file.
            force: If True, regenerate even if timing.ts exists.

        Returns:
            Path to generated timing.ts file.
        """
        if self.verbose:
            print("\n⏱️ Step 2: Generating Timing File")
            print("   " + "=" * 40)

        return self.timing_generator.generate(sync_map=sync_map, force=force)

    def migrate_scenes(
        self,
        sync_map: Optional[SyncMap] = None,
        dry_run: bool = False,
        scene_id: Optional[str] = None,
    ) -> dict[str, MigrationPlan]:
        """Migrate scenes to use centralized timing.

        Args:
            sync_map: Optional sync map. If None, loads from file.
            dry_run: If True, don't write changes.
            scene_id: Optional specific scene to migrate.

        Returns:
            Dict mapping scene_id to MigrationPlan.
        """
        if self.verbose:
            print("\n🔄 Step 3: Migrating Scenes")
            print("   " + "=" * 40)

        if scene_id:
            # Migrate single scene
            if sync_map is None:
                sync_map = self._load_sync_map()

            scene_config = sync_map.get_scene(scene_id)
            if not scene_config:
                if self.verbose:
                    print(f"  ❌ Scene not found: {scene_id}")
                return {}

            timing_data = self.migrator._parse_timing_file()
            timing_block = timing_data.get(scene_id)

            if not timing_block:
                if self.verbose:
                    print(f"  ❌ No timing data for scene: {scene_id}")
                return {}

            plan = self.migrator.migrate_scene(
                scene_config=scene_config,
                timing_block=timing_block,
                dry_run=dry_run,
            )
            return {scene_id: plan}

        # Migrate all scenes
        return self.migrator.migrate_all_scenes(
            sync_map=sync_map,
            dry_run=dry_run,
        )

    def run_full_sync(
        self,
        dry_run: bool = False,
        force: bool = False,
        scene_id: Optional[str] = None,
    ) -> SyncPhaseResult:
        """Run the complete sync workflow.

        Args:
            dry_run: If True, don't write changes.
            force: If True, regenerate all files.
            scene_id: Optional specific scene to process.

        Returns:
            SyncPhaseResult with complete status.
        """
        if self.verbose:
            print("\n" + "=" * 60)
            print("🔄 VISUAL-VOICEOVER SYNC")
            print("=" * 60)

        result = SyncPhaseResult(project_id=self.project.id)

        try:
            # Step 1: Generate sync map
            sync_map = self.generate_sync_map(force=force)
            result.sync_map_generated = True
            result.sync_map_path = self.project.root_dir / "sync" / "sync_map.json"
            result.total_scenes = len(sync_map.scenes)
            result.sync_points_found = sum(
                len(s.sync_points) for s in sync_map.scenes
            )

            # Step 2: Generate timing file
            timing_path = self.generate_timing_file(sync_map=sync_map, force=force)
            result.timing_file_generated = True
            result.timing_file_path = timing_path

            # Step 3: Migrate scenes
            migration_results = self.migrate_scenes(
                sync_map=sync_map,
                dry_run=dry_run,
                scene_id=scene_id,
            )
            result.migration_results = list(migration_results.values())
            result.scenes_migrated = sum(
                1 for p in migration_results.values() if p.success
            )

            # Collect warnings
            for plan in result.migration_results:
                if plan.error_message:
                    result.warnings.append(
                        f"{plan.scene_id}: {plan.error_message}"
                    )

            result.success = True

        except Exception as e:
            result.error_message = str(e)
            result.success = False
            if self.verbose:
                print(f"\n❌ Error: {e}")

        # Save result
        self._save_result(result)

        # Print summary
        if self.verbose:
            self._print_summary(result)

        return result

    def _load_sync_map(self) -> SyncMap:
        """Load sync map from project directory.

        Returns:
            SyncMap instance.
        """
        sync_map_path = self.project.root_dir / "sync" / "sync_map.json"
        if not sync_map_path.exists():
            raise FileNotFoundError(f"Sync map not found: {sync_map_path}")

        with open(sync_map_path) as f:
            data = json.load(f)

        return SyncMap.from_dict(data)

    def _save_result(self, result: SyncPhaseResult) -> Path:
        """Save sync result to project directory.

        Args:
            result: The SyncPhaseResult to save.

        Returns:
            Path to saved file.
        """
        sync_dir = self.project.root_dir / "sync"
        sync_dir.mkdir(parents=True, exist_ok=True)

        result_path = sync_dir / "sync_result.json"
        with open(result_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        return result_path

    def _print_summary(self, result: SyncPhaseResult) -> None:
        """Print sync result summary.

        Args:
            result: The SyncPhaseResult to summarize.
        """
        print("\n" + "=" * 60)
        print("📋 SYNC SUMMARY")
        print("=" * 60)

        status = "✅" if result.success else "❌"
        print(f"\n   {status} Overall Status: {'Success' if result.success else 'Failed'}")

        print(f"\n   Sync Map: {'✅ Generated' if result.sync_map_generated else '❌ Not generated'}")
        if result.sync_map_path:
            print(f"   Path: {result.sync_map_path}")

        print(f"\n   Timing File: {'✅ Generated' if result.timing_file_generated else '❌ Not generated'}")
        if result.timing_file_path:
            print(f"   Path: {result.timing_file_path}")

        print(f"\n   Scenes: {result.total_scenes}")
        print(f"   Sync Points Found: {result.sync_points_found}")
        print(f"   Scenes Migrated: {result.scenes_migrated}/{result.total_scenes}")

        if result.warnings:
            print(f"\n   ⚠️ Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:5]:
                print(f"      - {warning}")
            if len(result.warnings) > 5:
                print(f"      ... and {len(result.warnings) - 5} more")

        if result.error_message:
            print(f"\n   ❌ Error: {result.error_message}")

        print("\n" + "=" * 60)

        if result.success:
            print("\n💡 Next steps:")
            print("   1. Review sync/sync_map.json for accuracy")
            print("   2. Check scenes/timing.ts for correct frame numbers")
            print("   3. Run 'npx tsc --noEmit' in remotion/ to validate")
            print("   4. Render video to verify animations sync with voiceover")
