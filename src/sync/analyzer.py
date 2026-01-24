"""
LLM-based sync point analyzer for visual-voiceover synchronization.

This module analyzes scene code and word timestamps to generate sync points
that map visual animations to specific words in the voiceover.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from .models import (
    SyncPoint,
    SyncPointType,
    SceneSyncConfig,
    SyncMap,
)
from .utils import (
    extract_timing_vars,
    find_word_frame_fuzzy,
    validate_trigger_word,
    get_scene_duration_frames,
)
from .prompts import (
    SYNC_ANALYSIS_SYSTEM_PROMPT,
    SYNC_ANALYSIS_USER_PROMPT,
    format_word_timestamps,
    format_timing_vars,
)


class SyncAnalyzer:
    """Analyzer for generating sync points from scene code and voiceover timestamps."""

    def __init__(
        self,
        project,
        verbose: bool = True,
        llm_provider: Optional[Any] = None,
    ):
        """Initialize the sync analyzer.

        Args:
            project: The Project instance.
            verbose: Whether to print progress messages.
            llm_provider: Optional LLM provider for analysis. If None, uses default.
        """
        self.project = project
        self.verbose = verbose
        self.llm_provider = llm_provider
        self.fps = 30

    def analyze_scene(
        self,
        scene_id: str,
        scene_file: Path,
        word_timestamps: list[dict],
        narration_text: str,
        scene_title: str = "",
        duration_seconds: float = 0.0,
    ) -> SceneSyncConfig:
        """Analyze a single scene to generate sync points.

        Args:
            scene_id: The scene identifier.
            scene_file: Path to the scene .tsx file.
            word_timestamps: List of word timestamp dicts from manifest.
            narration_text: Full narration text for the scene.
            scene_title: Human-readable scene title.
            duration_seconds: Scene duration in seconds.

        Returns:
            SceneSyncConfig with identified sync points.
        """
        if self.verbose:
            print(f"  📊 Analyzing scene: {scene_title or scene_id}")

        # Read scene code
        if not scene_file.exists():
            if self.verbose:
                print(f"    ⚠️ Scene file not found: {scene_file}")
            return SceneSyncConfig(
                scene_id=scene_id,
                scene_title=scene_title,
                scene_file=str(scene_file),
                duration_seconds=duration_seconds,
                sync_points=[],
                narration_text=narration_text,
            )

        scene_code = scene_file.read_text()

        # Extract existing timing variables
        timing_vars = extract_timing_vars(scene_code)
        timing_var_names = [v["name"] for v in timing_vars]

        if self.verbose:
            print(f"    Found {len(timing_vars)} timing variables in code")

        # Calculate duration in frames
        duration_frames = get_scene_duration_frames(duration_seconds, self.fps)

        # Format prompt inputs
        word_timestamps_formatted = format_word_timestamps(word_timestamps)
        timing_vars_formatted = format_timing_vars(timing_vars)

        # Generate sync points using LLM
        sync_points = self._analyze_with_llm(
            scene_id=scene_id,
            scene_title=scene_title,
            scene_code=scene_code,
            narration_text=narration_text,
            word_timestamps=word_timestamps,
            word_timestamps_formatted=word_timestamps_formatted,
            timing_vars_formatted=timing_vars_formatted,
            duration_seconds=duration_seconds,
            duration_frames=duration_frames,
        )

        # Validate sync points
        validated_sync_points = self._validate_sync_points(
            sync_points, word_timestamps
        )

        if self.verbose:
            print(f"    ✅ Generated {len(validated_sync_points)} sync points")

        return SceneSyncConfig(
            scene_id=scene_id,
            scene_title=scene_title,
            scene_file=str(scene_file),
            duration_seconds=duration_seconds,
            sync_points=validated_sync_points,
            current_timing_vars=timing_var_names,
            narration_text=narration_text,
        )

    def analyze_project(self, force: bool = False) -> SyncMap:
        """Analyze all scenes in the project.

        Args:
            force: If True, regenerate even if sync_map exists.

        Returns:
            SyncMap with all scene configurations.
        """
        if self.verbose:
            print(f"\n🔍 Analyzing project: {self.project.id}")

        # Check for existing sync map
        sync_dir = self.project.root_dir / "sync"
        sync_map_path = sync_dir / "sync_map.json"

        if sync_map_path.exists() and not force:
            if self.verbose:
                print(f"  📄 Loading existing sync map from {sync_map_path}")
            with open(sync_map_path) as f:
                data = json.load(f)
            return SyncMap.from_dict(data)

        # Load manifest for word timestamps
        manifest_path = self.project.root_dir / "voiceover" / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Voiceover manifest not found: {manifest_path}")

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Load storyboard for scene info
        storyboard = self.project.load_storyboard()
        storyboard_scenes = storyboard.get("scenes", [])

        # Map manifest scenes by ID for easy lookup
        manifest_scenes = {s["scene_id"]: s for s in manifest.get("scenes", [])}

        # Analyze each scene
        scene_configs = []
        for sb_scene in storyboard_scenes:
            scene_id = sb_scene.get("id", "")
            scene_title = sb_scene.get("title", "")

            # Find matching manifest entry
            manifest_scene = manifest_scenes.get(scene_id, {})
            word_timestamps = manifest_scene.get("word_timestamps", [])
            duration_seconds = manifest_scene.get("duration_seconds", 0.0)

            # Get narration text
            narration_text = sb_scene.get("narration", "")

            # Find scene file
            scene_file = self._find_scene_file(scene_id, scene_title)

            if scene_file:
                config = self.analyze_scene(
                    scene_id=scene_id,
                    scene_file=scene_file,
                    word_timestamps=word_timestamps,
                    narration_text=narration_text,
                    scene_title=scene_title,
                    duration_seconds=duration_seconds,
                )
                scene_configs.append(config)
            else:
                if self.verbose:
                    print(f"  ⚠️ Scene file not found for: {scene_title}")

        # Create sync map
        from datetime import datetime
        sync_map = SyncMap(
            project_id=self.project.id,
            fps=self.fps,
            scenes=scene_configs,
            generated_at=datetime.now().isoformat(),
        )

        if self.verbose:
            total_points = sum(len(s.sync_points) for s in scene_configs)
            print(f"\n  ✅ Analyzed {len(scene_configs)} scenes, {total_points} sync points")

        return sync_map

    def save_sync_map(self, sync_map: SyncMap) -> Path:
        """Save sync map to project directory.

        Args:
            sync_map: The SyncMap to save.

        Returns:
            Path to the saved file.
        """
        sync_dir = self.project.root_dir / "sync"
        sync_dir.mkdir(parents=True, exist_ok=True)

        output_path = sync_dir / "sync_map.json"
        with open(output_path, "w") as f:
            json.dump(sync_map.to_dict(), f, indent=2)

        if self.verbose:
            print(f"  📄 Saved sync map to: {output_path}")

        return output_path

    def _find_scene_file(self, scene_id: str, scene_title: str) -> Optional[Path]:
        """Find the scene .tsx file.

        Args:
            scene_id: Scene ID (snake_case).
            scene_title: Scene title.

        Returns:
            Path to the scene file or None if not found.
        """
        scenes_dir = self.project.root_dir / "scenes"
        if not scenes_dir.exists():
            return None

        # Try different naming conventions
        candidates = []

        # Convert title to PascalCase for filename
        # "The Impossible Leap" -> "TheImpossibleLeapScene.tsx"
        pascal_name = "".join(word.title() for word in scene_title.split()) + "Scene.tsx"
        candidates.append(scenes_dir / pascal_name)

        # Try with scene_id
        # "the_impossible_leap" -> "TheImpossibleLeapScene.tsx"
        id_pascal = "".join(word.title() for word in scene_id.split("_")) + "Scene.tsx"
        candidates.append(scenes_dir / id_pascal)

        # Check each candidate
        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Fallback: search for any file containing the first word
        first_word = scene_title.split()[0] if scene_title else scene_id.split("_")[0]
        for file in scenes_dir.glob("*Scene.tsx"):
            if first_word.lower() in file.name.lower():
                return file

        return None

    def _analyze_with_llm(
        self,
        scene_id: str,
        scene_title: str,
        scene_code: str,
        narration_text: str,
        word_timestamps: list[dict],
        word_timestamps_formatted: str,
        timing_vars_formatted: str,
        duration_seconds: float,
        duration_frames: int,
    ) -> list[SyncPoint]:
        """Use LLM to analyze scene and generate sync points.

        Args:
            scene_id: Scene identifier.
            scene_title: Human-readable title.
            scene_code: Scene TypeScript code.
            narration_text: Narration text.
            word_timestamps: Raw word timestamp data.
            word_timestamps_formatted: Formatted for prompt.
            timing_vars_formatted: Formatted timing vars.
            duration_seconds: Scene duration.
            duration_frames: Duration in frames.

        Returns:
            List of SyncPoint objects.
        """
        # Format the user prompt
        user_prompt = SYNC_ANALYSIS_USER_PROMPT.format(
            scene_id=scene_id,
            scene_title=scene_title,
            duration_seconds=duration_seconds,
            duration_frames=duration_frames,
            fps=self.fps,
            narration_text=narration_text,
            word_timestamps_formatted=word_timestamps_formatted,
            scene_code=scene_code,
            timing_vars_formatted=timing_vars_formatted,
        )

        # Call LLM
        if self.llm_provider:
            response = self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=SYNC_ANALYSIS_SYSTEM_PROMPT,
            )
        else:
            # Use default LLM provider
            from ..understanding.llm_provider import get_llm_provider
            provider = get_llm_provider()
            response = provider.generate(
                prompt=user_prompt,
                system_prompt=SYNC_ANALYSIS_SYSTEM_PROMPT,
            )

        # Parse response
        return self._parse_sync_points_response(response)

    def _parse_sync_points_response(self, response: str) -> list[SyncPoint]:
        """Parse LLM response into SyncPoint objects.

        Args:
            response: Raw LLM response text.

        Returns:
            List of SyncPoint objects.
        """
        # Extract JSON from response
        json_match = re.search(r"\[[\s\S]*\]", response)
        if not json_match:
            if self.verbose:
                print("    ⚠️ Could not parse sync points from LLM response")
            return []

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"    ⚠️ JSON parse error: {e}")
            return []

        sync_points = []
        for item in data:
            try:
                # Map sync_type string to enum
                sync_type_str = item.get("sync_type", "element_appear")
                try:
                    sync_type = SyncPointType(sync_type_str)
                except ValueError:
                    sync_type = SyncPointType.ELEMENT_APPEAR

                sp = SyncPoint(
                    id=item.get("id", ""),
                    sync_type=sync_type,
                    trigger_phrase=item.get("trigger_phrase", ""),
                    trigger_word=item.get("trigger_word", ""),
                    use_word_start=item.get("use_word_start", True),
                    offset_frames=item.get("offset_frames", -3),
                    visual_element=item.get("visual_element", ""),
                    notes=item.get("notes", ""),
                )
                if sp.id and sp.trigger_word:
                    sync_points.append(sp)
            except Exception as e:
                if self.verbose:
                    print(f"    ⚠️ Error parsing sync point: {e}")
                continue

        return sync_points

    def _validate_sync_points(
        self,
        sync_points: list[SyncPoint],
        word_timestamps: list[dict],
    ) -> list[SyncPoint]:
        """Validate and fix sync points.

        Args:
            sync_points: List of sync points to validate.
            word_timestamps: Word timestamps for validation.

        Returns:
            List of validated sync points.
        """
        validated = []

        for sp in sync_points:
            is_valid, suggestion = validate_trigger_word(
                sp.trigger_word, word_timestamps
            )

            if is_valid:
                validated.append(sp)
            elif suggestion:
                # Use the suggested word instead
                if self.verbose:
                    print(f"    ⚠️ Fixed trigger word: '{sp.trigger_word}' → '{suggestion}'")
                sp.trigger_word = suggestion
                validated.append(sp)
            else:
                if self.verbose:
                    print(f"    ⚠️ Skipping invalid sync point: '{sp.id}' (word '{sp.trigger_word}' not found)")

        return validated
