"""
Timing generator for visual-voiceover sync.

This module converts sync points and word timestamps into frame-accurate
timing constants, and generates the centralized timing.ts file.
"""

import json
from pathlib import Path
from typing import Any, Optional

from .models import (
    SyncMap,
    SceneSyncConfig,
    SceneTimingBlock,
    ProjectTiming,
    SyncPointType,
)
from .utils import (
    find_word_frame_fuzzy,
    get_scene_duration_frames,
)


# Sync point types that are informational only and should NOT be used for code replacement
# These define conceptual phase changes, not animation triggers
INFORMATIONAL_SYNC_TYPES = {
    SyncPointType.PHASE_TRANSITION,
    SyncPointType.ANIMATION_PEAK,
}


def generate_scene_timing(
    scene_config: SceneSyncConfig,
    word_timestamps: list[dict],
    fps: int = 30,
) -> SceneTimingBlock:
    """Generate timing constants for a single scene.

    Args:
        scene_config: Scene sync configuration with sync points.
        word_timestamps: Word timestamps from the voiceover manifest.
        fps: Frames per second.

    Returns:
        SceneTimingBlock with calculated frame numbers.
    """
    duration_frames = get_scene_duration_frames(scene_config.duration_seconds, fps)
    timing_constants: dict[str, int] = {}
    warnings: list[str] = []
    skipped_informational: list[str] = []

    for sync_point in scene_config.sync_points:
        # Skip informational sync types - these should NOT be used for code replacement
        # Phase transitions define conceptual changes, not animation triggers
        if sync_point.sync_type in INFORMATIONAL_SYNC_TYPES:
            skipped_informational.append(
                f"Skipped '{sync_point.id}' ({sync_point.sync_type.value}) - informational only"
            )
            continue

        # Find the frame for this sync point
        frame = find_word_frame_fuzzy(
            word_timestamps=word_timestamps,
            target_word=sync_point.trigger_word,
            fps=fps,
            use_start=sync_point.use_word_start,
            offset_frames=sync_point.offset_frames,
        )

        if frame is not None:
            # Ensure frame is within valid range
            frame = max(0, min(frame, duration_frames))
            timing_constants[sync_point.id] = frame
        else:
            # Fallback to middle of scene
            fallback_frame = duration_frames // 2
            timing_constants[sync_point.id] = fallback_frame
            warnings.append(
                f"Word '{sync_point.trigger_word}' not found for '{sync_point.id}', "
                f"using fallback frame {fallback_frame}"
            )

    # Add informational skip notices to warnings for visibility
    warnings.extend(skipped_informational)

    return SceneTimingBlock(
        scene_id=scene_config.scene_id,
        duration_frames=duration_frames,
        timing_constants=timing_constants,
        warnings=warnings,
    )


def generate_project_timing(
    sync_map: SyncMap,
    manifest: dict[str, Any],
    fps: int = 30,
) -> ProjectTiming:
    """Generate timing data for all scenes in a project.

    Args:
        sync_map: Complete sync map with all scene configs.
        manifest: Voiceover manifest with word timestamps.
        fps: Frames per second.

    Returns:
        ProjectTiming with all scene timing blocks.
    """
    # Create lookup for manifest scenes
    manifest_scenes = {s["scene_id"]: s for s in manifest.get("scenes", [])}

    scene_timings: list[SceneTimingBlock] = []

    for scene_config in sync_map.scenes:
        # Get word timestamps for this scene
        manifest_scene = manifest_scenes.get(scene_config.scene_id, {})
        word_timestamps = manifest_scene.get("word_timestamps", [])

        timing_block = generate_scene_timing(
            scene_config=scene_config,
            word_timestamps=word_timestamps,
            fps=fps,
        )
        scene_timings.append(timing_block)

    return ProjectTiming(
        project_id=sync_map.project_id,
        fps=fps,
        scenes=scene_timings,
    )


def generate_timing_typescript(timing: ProjectTiming) -> str:
    """Generate TypeScript source code for timing constants.

    Args:
        timing: Project timing data.

    Returns:
        TypeScript source code as a string.
    """
    lines = [
        "/**",
        " * Auto-generated timing constants for scene synchronization.",
        " * DO NOT EDIT MANUALLY - regenerate with:",
        " *   python -m src.cli.main refine <project> --phase sync --generate-timing",
        " *",
        " * This file maps voiceover word timestamps to animation frame numbers.",
        " * When the voiceover changes, regenerate this file to update all scenes.",
        " */",
        "",
        "export const TIMING = {",
    ]

    for scene_block in timing.scenes:
        lines.append(f"  {scene_block.scene_id}: {{")
        lines.append(f"    duration: {scene_block.duration_frames},")

        # Sort timing constants for consistent output
        for name in sorted(scene_block.timing_constants.keys()):
            value = scene_block.timing_constants[name]
            lines.append(f"    {name}: {value},")

        lines.append("  },")

    lines.append("} as const;")
    lines.append("")
    lines.append("// Type helpers")
    lines.append("export type SceneTiming = typeof TIMING;")
    lines.append("export type SceneId = keyof SceneTiming;")
    lines.append("")

    return "\n".join(lines)


def generate_timing_file(
    sync_map: SyncMap,
    manifest: dict[str, Any],
    output_path: Path,
    fps: int = 30,
    verbose: bool = True,
) -> ProjectTiming:
    """Generate timing.ts file from sync map and manifest.

    Args:
        sync_map: Complete sync map with all scene configs.
        manifest: Voiceover manifest with word timestamps.
        output_path: Path to write the timing.ts file.
        fps: Frames per second.
        verbose: Whether to print progress messages.

    Returns:
        The generated ProjectTiming data.
    """
    # Generate timing data
    timing = generate_project_timing(sync_map, manifest, fps)

    # Generate TypeScript code
    typescript_code = generate_timing_typescript(timing)

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path.write_text(typescript_code)

    if verbose:
        total_constants = sum(len(s.timing_constants) for s in timing.scenes)
        print(f"  📄 Generated timing file: {output_path}")
        print(f"     Scenes: {len(timing.scenes)}")
        print(f"     Constants: {total_constants}")

        # Report any warnings
        for scene_block in timing.scenes:
            for warning in scene_block.warnings:
                print(f"     ⚠️ {warning}")

    return timing


class TimingGenerator:
    """Generator for centralized timing files."""

    def __init__(
        self,
        project,
        verbose: bool = True,
    ):
        """Initialize the timing generator.

        Args:
            project: The Project instance.
            verbose: Whether to print progress messages.
        """
        self.project = project
        self.verbose = verbose
        self.fps = 30

    def generate(self, sync_map: Optional[SyncMap] = None, force: bool = False) -> Path:
        """Generate timing.ts file for the project.

        Args:
            sync_map: Optional sync map. If None, loads from file.
            force: If True, regenerate even if timing.ts exists.

        Returns:
            Path to the generated timing.ts file.
        """
        output_path = self.project.root_dir / "scenes" / "timing.ts"

        if output_path.exists() and not force:
            if self.verbose:
                print(f"  📄 Timing file already exists: {output_path}")
                print("     Use --force to regenerate")
            return output_path

        # Load sync map if not provided
        if sync_map is None:
            sync_map = self._load_sync_map()

        # Load manifest
        manifest = self._load_manifest()

        # Generate timing file
        generate_timing_file(
            sync_map=sync_map,
            manifest=manifest,
            output_path=output_path,
            fps=self.fps,
            verbose=self.verbose,
        )

        return output_path

    def _load_sync_map(self) -> SyncMap:
        """Load sync map from project directory.

        Returns:
            SyncMap instance.

        Raises:
            FileNotFoundError: If sync map doesn't exist.
        """
        sync_map_path = self.project.root_dir / "sync" / "sync_map.json"
        if not sync_map_path.exists():
            raise FileNotFoundError(
                f"Sync map not found: {sync_map_path}\n"
                "Run with --generate-map first."
            )

        with open(sync_map_path) as f:
            data = json.load(f)

        return SyncMap.from_dict(data)

    def _load_manifest(self) -> dict:
        """Load voiceover manifest.

        Returns:
            Manifest dict.

        Raises:
            FileNotFoundError: If manifest doesn't exist.
        """
        manifest_path = self.project.root_dir / "voiceover" / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Voiceover manifest not found: {manifest_path}")

        with open(manifest_path) as f:
            return json.load(f)

    def validate_timing(self) -> list[str]:
        """Validate the generated timing.ts file.

        Returns:
            List of validation issues (empty if valid).
        """
        timing_path = self.project.root_dir / "scenes" / "timing.ts"
        issues = []

        if not timing_path.exists():
            issues.append("timing.ts file not found")
            return issues

        content = timing_path.read_text()

        # Check for basic structure
        if "export const TIMING" not in content:
            issues.append("Missing TIMING export")

        if "as const" not in content:
            issues.append("Missing 'as const' assertion")

        # Check for negative frame numbers
        import re
        negative_pattern = re.compile(r":\s*-\d+")
        if negative_pattern.search(content):
            issues.append("Found negative frame numbers")

        return issues
