"""
Scene migrator for converting scenes to use centralized timing.

This module handles the transformation of scene code to import and use
timing constants from the centralized timing.ts file.
"""

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .models import (
    SyncMap,
    SceneSyncConfig,
    SceneTimingBlock,
    MigrationPlan,
)
from .prompts import (
    SCENE_MIGRATION_SYSTEM_PROMPT,
    SCENE_MIGRATION_USER_PROMPT,
    format_timing_constants,
    format_sync_points,
)


class SceneMigrator:
    """Migrator for converting scene code to use centralized timing."""

    def __init__(
        self,
        project,
        verbose: bool = True,
        llm_provider: Optional[Any] = None,
        skip_validation: bool = False,
    ):
        """Initialize the scene migrator.

        Args:
            project: The Project instance.
            verbose: Whether to print progress messages.
            llm_provider: Optional LLM provider. If None, uses default.
            skip_validation: If True, skip TypeScript validation after migration.
        """
        self.project = project
        self.verbose = verbose
        self.llm_provider = llm_provider
        self.skip_validation = skip_validation
        self.backup_dir = project.root_dir / "scenes" / ".backups"

    def migrate_scene(
        self,
        scene_config: SceneSyncConfig,
        timing_block: SceneTimingBlock,
        dry_run: bool = False,
    ) -> MigrationPlan:
        """Migrate a single scene to use centralized timing.

        Args:
            scene_config: Scene configuration with sync points.
            timing_block: Timing block with calculated frame numbers.
            dry_run: If True, don't write changes, just show what would happen.

        Returns:
            MigrationPlan with results.
        """
        scene_file = Path(scene_config.scene_file)
        if not scene_file.is_absolute():
            scene_file = self.project.root_dir / scene_config.scene_file

        if self.verbose:
            print(f"  🔄 Migrating: {scene_config.scene_title}")

        # Check if file exists
        if not scene_file.exists():
            return MigrationPlan(
                scene_id=scene_config.scene_id,
                scene_file=scene_file,
                original_code="",
                migrated_code="",
                success=False,
                error_message=f"Scene file not found: {scene_file}",
            )

        # Read original code
        original_code = scene_file.read_text()

        # Check if already migrated
        if self._is_already_migrated(original_code):
            if self.verbose:
                print(f"    ⏭️ Already uses TIMING import, skipping")
            return MigrationPlan(
                scene_id=scene_config.scene_id,
                scene_file=scene_file,
                original_code=original_code,
                migrated_code=original_code,
                success=True,
                error_message=None,
            )

        # Generate migrated code using LLM
        migrated_code = self._migrate_with_llm(
            scene_config=scene_config,
            timing_block=timing_block,
            original_code=original_code,
        )

        if not migrated_code:
            return MigrationPlan(
                scene_id=scene_config.scene_id,
                scene_file=scene_file,
                original_code=original_code,
                migrated_code="",
                success=False,
                error_message="LLM migration failed to generate code",
            )

        # Extract what was changed
        imports_added = self._extract_imports_added(original_code, migrated_code)
        constants_replaced = self._extract_constants_replaced(
            scene_config.scene_id, timing_block.timing_constants
        )

        plan = MigrationPlan(
            scene_id=scene_config.scene_id,
            scene_file=scene_file,
            original_code=original_code,
            migrated_code=migrated_code,
            imports_added=imports_added,
            constants_replaced=constants_replaced,
            success=False,
        )

        if dry_run:
            if self.verbose:
                print(f"    📝 [DRY RUN] Would migrate {len(constants_replaced)} constants")
            plan.success = True
            return plan

        # Create backup
        backup_path = self._create_backup(scene_file)
        plan.backup_path = backup_path

        # Write migrated code
        try:
            scene_file.write_text(migrated_code)
            if self.verbose:
                print(f"    ✅ Migrated successfully")
        except Exception as e:
            plan.error_message = f"Failed to write file: {e}"
            return plan

        # Validate TypeScript syntax
        validation_ok, validation_error = self._validate_typescript(scene_file)
        if not validation_ok:
            # Restore backup
            if backup_path and backup_path.exists():
                shutil.copy(backup_path, scene_file)
            plan.error_message = f"TypeScript validation failed: {validation_error}"
            if self.verbose:
                print(f"    ❌ Validation failed, restored backup")
            return plan

        plan.success = True
        return plan

    def migrate_all_scenes(
        self,
        sync_map: Optional[SyncMap] = None,
        timing_data: Optional[dict[str, SceneTimingBlock]] = None,
        dry_run: bool = False,
    ) -> dict[str, MigrationPlan]:
        """Migrate all scenes in the project.

        Args:
            sync_map: Optional sync map. If None, loads from file.
            timing_data: Optional timing data. If None, loads from file.
            dry_run: If True, don't write changes.

        Returns:
            Dict mapping scene_id to MigrationPlan.
        """
        if self.verbose:
            print(f"\n🔄 Migrating scenes for project: {self.project.id}")

        # Load sync map if not provided
        if sync_map is None:
            sync_map = self._load_sync_map()

        # Load timing data if not provided
        if timing_data is None:
            timing_data = self._parse_timing_file()

        results: dict[str, MigrationPlan] = {}

        for scene_config in sync_map.scenes:
            scene_id = scene_config.scene_id

            # Get timing block for this scene
            timing_block = timing_data.get(scene_id)
            if timing_block is None:
                if self.verbose:
                    print(f"  ⚠️ No timing data for scene: {scene_id}")
                results[scene_id] = MigrationPlan(
                    scene_id=scene_id,
                    scene_file=Path(scene_config.scene_file),
                    original_code="",
                    migrated_code="",
                    success=False,
                    error_message="No timing data found",
                )
                continue

            plan = self.migrate_scene(
                scene_config=scene_config,
                timing_block=timing_block,
                dry_run=dry_run,
            )
            results[scene_id] = plan

        # Summary
        if self.verbose:
            success_count = sum(1 for p in results.values() if p.success)
            print(f"\n  ✅ Migrated {success_count}/{len(results)} scenes")

        return results

    def _is_already_migrated(self, code: str) -> bool:
        """Check if scene code already imports TIMING.

        Args:
            code: Scene source code.

        Returns:
            True if already migrated.
        """
        return "import { TIMING }" in code or "import {TIMING}" in code

    def _migrate_with_llm(
        self,
        scene_config: SceneSyncConfig,
        timing_block: SceneTimingBlock,
        original_code: str,
    ) -> Optional[str]:
        """Use LLM to migrate scene code.

        Args:
            scene_config: Scene configuration.
            timing_block: Timing block with frame numbers.
            original_code: Original scene code.

        Returns:
            Migrated code or None if failed.
        """
        # Format timing constants
        timing_constants_formatted = format_timing_constants(timing_block.timing_constants)

        # Format sync points with calculated frames
        sync_points_with_frames = []
        for sp in scene_config.sync_points:
            sp_dict = sp.to_dict()
            sp_dict["calculated_frame"] = timing_block.timing_constants.get(sp.id, "?")
            sync_points_with_frames.append(sp_dict)

        sync_points_formatted = format_sync_points(sync_points_with_frames)

        # Format user prompt
        user_prompt = SCENE_MIGRATION_USER_PROMPT.format(
            scene_id=scene_config.scene_id,
            scene_title=scene_config.scene_title,
            duration_frames=timing_block.duration_frames,
            timing_constants_formatted=timing_constants_formatted,
            scene_code=original_code,
            sync_points_formatted=sync_points_formatted,
        )

        # Call LLM
        if self.llm_provider:
            response = self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=SCENE_MIGRATION_SYSTEM_PROMPT,
            )
        else:
            from ..understanding.llm_provider import get_llm_provider
            provider = get_llm_provider()
            response = provider.generate(
                prompt=user_prompt,
                system_prompt=SCENE_MIGRATION_SYSTEM_PROMPT,
            )

        # Extract code from response
        return self._extract_code_from_response(response)

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract TypeScript code from LLM response.

        Args:
            response: Raw LLM response.

        Returns:
            Extracted code or None.
        """
        # Try to find code block
        code_match = re.search(r"```(?:tsx?|typescript|javascript)?\s*\n([\s\S]*?)\n```", response)
        if code_match:
            return code_match.group(1)

        # If no code block, assume entire response is code (if it looks like code)
        if "import" in response and "export" in response:
            return response.strip()

        return None

    def _extract_imports_added(self, original: str, migrated: str) -> list[str]:
        """Extract list of imports added during migration.

        Args:
            original: Original code.
            migrated: Migrated code.

        Returns:
            List of import statements added.
        """
        original_imports = set(re.findall(r"import\s+.*?from\s+['\"].*?['\"];?", original))
        migrated_imports = set(re.findall(r"import\s+.*?from\s+['\"].*?['\"];?", migrated))

        added = migrated_imports - original_imports
        return list(added)

    def _extract_constants_replaced(
        self,
        scene_id: str,
        timing_constants: dict[str, int],
    ) -> dict[str, str]:
        """Extract mapping of replaced constants.

        Args:
            scene_id: Scene identifier.
            timing_constants: Timing constants that were used.

        Returns:
            Dict mapping old pattern to new pattern.
        """
        replaced = {}
        for name, value in timing_constants.items():
            replaced[str(value)] = f"TIMING.{scene_id}.{name}"
        return replaced

    def _create_backup(self, scene_file: Path) -> Path:
        """Create backup of scene file.

        Args:
            scene_file: Path to scene file.

        Returns:
            Path to backup file.
        """
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{scene_file.stem}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        shutil.copy(scene_file, backup_path)

        if self.verbose:
            print(f"    📦 Backup created: {backup_path.name}")

        return backup_path

    def _validate_typescript(self, scene_file: Path) -> tuple[bool, Optional[str]]:
        """Validate TypeScript syntax using basic checks.

        We use a lightweight validation approach instead of running tsc,
        which can be slow and have issues with module resolution.
        The user should run `npm run build` for full validation.

        Args:
            scene_file: Path to scene file.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            content = scene_file.read_text()

            # Basic syntax checks
            errors = []

            # Check for balanced braces
            if content.count('{') != content.count('}'):
                errors.append("Unbalanced curly braces")

            # Check for balanced parentheses
            if content.count('(') != content.count(')'):
                errors.append("Unbalanced parentheses")

            # Check for balanced brackets
            if content.count('[') != content.count(']'):
                errors.append("Unbalanced brackets")

            # Check for required exports
            if 'export' not in content:
                errors.append("Missing export statement")

            # Check for required imports
            if 'import' not in content:
                errors.append("Missing import statements")

            # Check that TIMING import was added if we're migrating
            if 'TIMING' in content and "import { TIMING }" not in content and "import {TIMING}" not in content:
                errors.append("TIMING used but not imported")

            if errors:
                return False, "; ".join(errors)

            return True, None

        except Exception as e:
            return False, str(e)

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

    def _parse_timing_file(self) -> dict[str, SceneTimingBlock]:
        """Parse timing.ts file into timing blocks.

        Returns:
            Dict mapping scene_id to SceneTimingBlock.
        """
        timing_path = self.project.root_dir / "scenes" / "timing.ts"
        if not timing_path.exists():
            raise FileNotFoundError(f"Timing file not found: {timing_path}")

        content = timing_path.read_text()
        timing_data: dict[str, SceneTimingBlock] = {}

        # Parse the TypeScript object structure
        # Look for patterns like: scene_id: { duration: 900, constant1: 120, ... }
        scene_pattern = re.compile(
            r"(\w+):\s*\{\s*([^}]+)\s*\}",
            re.MULTILINE
        )

        for scene_match in scene_pattern.finditer(content):
            scene_id = scene_match.group(1)
            props_str = scene_match.group(2)

            # Parse properties
            prop_pattern = re.compile(r"(\w+):\s*(\d+)")
            timing_constants = {}
            duration_frames = 0

            for prop_match in prop_pattern.finditer(props_str):
                prop_name = prop_match.group(1)
                prop_value = int(prop_match.group(2))

                if prop_name == "duration":
                    duration_frames = prop_value
                else:
                    timing_constants[prop_name] = prop_value

            timing_data[scene_id] = SceneTimingBlock(
                scene_id=scene_id,
                duration_frames=duration_frames,
                timing_constants=timing_constants,
            )

        return timing_data

    def restore_backup(self, scene_id: str) -> bool:
        """Restore scene from most recent backup.

        Args:
            scene_id: Scene identifier.

        Returns:
            True if restored successfully.
        """
        if not self.backup_dir.exists():
            return False

        # Find most recent backup for this scene
        pattern = f"*{scene_id}*.bak"
        backups = sorted(self.backup_dir.glob(pattern), reverse=True)

        if not backups:
            # Try finding by scene file name patterns
            sync_map = self._load_sync_map()
            scene_config = sync_map.get_scene(scene_id)
            if scene_config:
                stem = Path(scene_config.scene_file).stem
                backups = sorted(self.backup_dir.glob(f"{stem}.*.bak"), reverse=True)

        if not backups:
            if self.verbose:
                print(f"  ❌ No backup found for scene: {scene_id}")
            return False

        backup_path = backups[0]

        # Determine original file path
        sync_map = self._load_sync_map()
        scene_config = sync_map.get_scene(scene_id)
        if not scene_config:
            return False

        scene_file = Path(scene_config.scene_file)
        if not scene_file.is_absolute():
            scene_file = self.project.root_dir / scene_config.scene_file

        shutil.copy(backup_path, scene_file)

        if self.verbose:
            print(f"  ✅ Restored {scene_id} from {backup_path.name}")

        return True
