"""Audio service for voiceover generation."""

import json
from pathlib import Path
from typing import Any

from .job_manager import JobManager, JobType


class AudioService:
    """Service for audio/voiceover operations.

    Wraps the existing audio module without modifying it.
    """

    def __init__(self, job_manager: JobManager, projects_dir: Path | str = Path("projects")):
        """Initialize the audio service.

        Args:
            job_manager: Job manager for background tasks.
            projects_dir: Path to the projects directory.
        """
        self.job_manager = job_manager
        self.projects_dir = Path(projects_dir)

    def generate_voiceovers(
        self,
        project_id: str,
        provider: str = "edge",
        mock: bool = False,
    ) -> str:
        """Start voiceover generation job.

        Args:
            project_id: The project ID.
            provider: TTS provider name.
            mock: Whether to use mock provider.

        Returns:
            The job ID.
        """
        from src.project import load_project

        # Validate prerequisites before submitting job
        project = load_project(self.projects_dir / project_id)
        try:
            narrations = project.load_narrations()
            if not narrations:
                raise ValueError("No narrations found. Please add narrations first.")
        except FileNotFoundError:
            raise ValueError("No narrations found. Please add narrations first.")

        def task(job_manager: JobManager, job_id: str) -> dict[str, Any]:
            from src.project import load_project
            from src.audio import get_tts_provider
            from src.config import Config

            # Load project
            project = load_project(self.projects_dir / project_id)
            narrations = project.load_narrations()

            # Setup TTS provider
            config = Config()
            config.tts.provider = "mock" if mock else provider
            if project.tts.voice_id:
                config.tts.voice_id = project.tts.voice_id

            tts = get_tts_provider(config)

            # Generate voiceovers
            output_dir = project.voiceover_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            results = []
            total_duration = 0.0

            for i, narration in enumerate(narrations):
                job_manager.update_progress(
                    job_id,
                    progress=(i / len(narrations)),
                    message=f"Processing {narration.scene_id} ({i + 1}/{len(narrations)})",
                )

                output_path = output_dir / f"{narration.scene_id}.mp3"

                result = tts.generate_with_timestamps(narration.narration, output_path)

                results.append(
                    {
                        "scene_id": narration.scene_id,
                        "audio_path": str(output_path),
                        "duration_seconds": result.duration_seconds,
                        "word_timestamps": [
                            {
                                "word": ts.word,
                                "start_seconds": ts.start_seconds,
                                "end_seconds": ts.end_seconds,
                            }
                            for ts in result.word_timestamps
                        ],
                    }
                )
                total_duration += result.duration_seconds

            # Save manifest
            manifest = {
                "scenes": results,
                "total_duration_seconds": total_duration,
                "output_dir": str(output_dir),
            }

            manifest_path = output_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            # Auto-sync storyboard durations
            self._sync_storyboard_durations(project, results)

            return {
                "scenes_processed": len(results),
                "total_duration_seconds": total_duration,
                "manifest_path": str(manifest_path),
            }

        return self.job_manager.submit_job(JobType.VOICEOVER, project_id, task)

    def _sync_storyboard_durations(self, project, voiceover_results: list[dict]) -> int:
        """Sync storyboard scene durations with actual voiceover durations.

        Args:
            project: The project.
            voiceover_results: List of voiceover results.

        Returns:
            Number of scenes updated.
        """
        storyboard_path = project.get_path("storyboard")
        if not storyboard_path.exists():
            return 0

        try:
            with open(storyboard_path) as f:
                storyboard = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return 0

        # Create lookup for voiceover durations
        vo_durations = {vo["scene_id"]: vo["duration_seconds"] for vo in voiceover_results}

        # Update storyboard scene durations
        updated_count = 0
        for scene in storyboard.get("scenes", []):
            scene_id = scene.get("id") or scene.get("scene_id")
            if scene_id and scene_id in vo_durations:
                old_dur = scene.get("audio_duration_seconds", 0)
                # Add a small buffer (0.5s)
                new_dur = round(vo_durations[scene_id] + 0.5, 2)

                if abs(new_dur - old_dur) > 0.5:
                    scene["audio_duration_seconds"] = new_dur
                    updated_count += 1

        if updated_count > 0:
            # Update total duration
            total_duration = sum(
                scene.get("audio_duration_seconds", 0) for scene in storyboard.get("scenes", [])
            )
            storyboard["total_duration_seconds"] = round(total_duration, 2)

            with open(storyboard_path, "w") as f:
                json.dump(storyboard, f, indent=2)

        return updated_count

    def list_voiceovers(self, project_id: str) -> list[dict[str, Any]]:
        """List voiceover files for a project.

        Args:
            project_id: The project ID.

        Returns:
            List of voiceover file info.
        """
        from src.project import load_project

        project = load_project(self.projects_dir / project_id)
        voiceover_files = project.get_voiceover_files()

        # Try to load manifest for duration info
        manifest_path = project.voiceover_dir / "manifest.json"
        durations = {}
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                for scene in manifest.get("scenes", []):
                    durations[scene["scene_id"]] = scene.get("duration_seconds")
            except (json.JSONDecodeError, KeyError):
                pass

        return [
            {
                "scene_id": f.stem,
                "path": str(f),
                "exists": True,
                "duration_seconds": durations.get(f.stem),
            }
            for f in voiceover_files
        ]

    def get_voiceover_path(self, project_id: str, scene_id: str) -> Path | None:
        """Get the path to a voiceover file.

        Args:
            project_id: The project ID.
            scene_id: The scene ID.

        Returns:
            Path to the audio file, or None if not found.
        """
        from src.project import load_project

        project = load_project(self.projects_dir / project_id)
        audio_path = project.voiceover_dir / f"{scene_id}.mp3"
        return audio_path if audio_path.exists() else None
