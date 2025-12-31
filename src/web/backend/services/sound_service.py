"""Sound service for SFX library management."""

from pathlib import Path
from typing import Any

from .job_manager import JobManager, JobType
from ..models.responses import SoundInfo


class SoundService:
    """Service for sound effects management.

    Wraps the existing sound module without modifying it.
    """

    def __init__(self, job_manager: JobManager, projects_dir: Path | str = Path("projects")):
        """Initialize the sound service.

        Args:
            job_manager: Job manager for background tasks.
            projects_dir: Path to the projects directory.
        """
        self.job_manager = job_manager
        self.projects_dir = Path(projects_dir)

    def list_sounds(self, project_id: str) -> list[SoundInfo]:
        """List all sounds with their status.

        Args:
            project_id: The project ID.

        Returns:
            List of sound info.
        """
        from src.project import load_project
        from src.sound.library import SoundLibrary, SOUND_MANIFEST

        project = load_project(self.projects_dir / project_id)
        sfx_dir = project.root_dir / "sfx"
        library = SoundLibrary(sfx_dir)

        return [
            SoundInfo(
                name=name,
                description=info["description"],
                exists=library.sound_exists(name),
            )
            for name, info in SOUND_MANIFEST.items()
        ]

    def generate_sounds(self, project_id: str) -> str:
        """Start sound generation job.

        Args:
            project_id: The project ID.

        Returns:
            The job ID.
        """

        def task(job_manager: JobManager, job_id: str) -> dict[str, Any]:
            from src.project import load_project
            from src.sound.library import SoundLibrary, SOUND_MANIFEST

            job_manager.update_progress(job_id, 0.1, "Loading project...")

            project = load_project(self.projects_dir / project_id)
            sfx_dir = project.root_dir / "sfx"

            job_manager.update_progress(job_id, 0.2, "Generating sounds...")

            library = SoundLibrary(sfx_dir)
            generated = library.generate_all()

            job_manager.update_progress(job_id, 1.0, "Sound generation complete")

            return {
                "generated": generated,
                "total_sounds": len(SOUND_MANIFEST),
                "output_dir": str(sfx_dir),
            }

        return self.job_manager.submit_job(JobType.SOUND, project_id, task)

    def get_sound_path(self, project_id: str, sound_name: str) -> Path | None:
        """Get the path to a sound file.

        Args:
            project_id: The project ID.
            sound_name: The sound name.

        Returns:
            Path to the sound file, or None if not found.
        """
        from src.project import load_project

        project = load_project(self.projects_dir / project_id)
        sound_path = project.root_dir / "sfx" / f"{sound_name}.wav"
        return sound_path if sound_path.exists() else None
