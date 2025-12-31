"""Render service for video generation."""

import subprocess
from pathlib import Path
from typing import Any

from .job_manager import JobManager, JobType


# Resolution presets (same as CLI)
RESOLUTION_PRESETS = {
    "4k": (3840, 2160),
    "1440p": (2560, 1440),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "480p": (854, 480),
}


class RenderService:
    """Service for video rendering.

    Wraps the Remotion render subprocess.
    """

    def __init__(self, job_manager: JobManager, projects_dir: Path | str = Path("projects")):
        """Initialize the render service.

        Args:
            job_manager: Job manager for background tasks.
            projects_dir: Path to the projects directory.
        """
        self.job_manager = job_manager
        self.projects_dir = Path(projects_dir)
        # Find remotion directory relative to this file
        self.remotion_dir = Path(__file__).parent.parent.parent.parent.parent / "remotion"

    def start_render(
        self,
        project_id: str,
        resolution: str = "1080p",
        preview: bool = False,
    ) -> str:
        """Start a video render job.

        Args:
            project_id: The project ID.
            resolution: Output resolution preset.
            preview: Whether this is a preview render.

        Returns:
            The job ID.
        """
        from src.project import load_project

        if resolution not in RESOLUTION_PRESETS:
            raise ValueError(f"Unknown resolution: {resolution}. Valid: {list(RESOLUTION_PRESETS.keys())}")

        # Validate prerequisites before submitting job
        project = load_project(self.projects_dir / project_id)
        storyboard_path = project.get_path("storyboard")
        if not storyboard_path.exists():
            raise FileNotFoundError(f"Storyboard not found. Please generate a storyboard first.")

        render_script = self.remotion_dir / "scripts" / "render.mjs"
        if not render_script.exists():
            raise FileNotFoundError(f"Render script not found: {render_script}")

        def task(job_manager: JobManager, job_id: str) -> dict[str, Any]:
            from src.project import load_project

            job_manager.update_progress(job_id, 0.1, "Loading project...")

            project = load_project(self.projects_dir / project_id)

            # Determine output path
            width, height = RESOLUTION_PRESETS[resolution]
            if preview:
                output_path = project.output_dir / "preview" / "preview.mp4"
            elif resolution != "1080p":
                output_path = project.output_dir / f"final-{resolution}.mp4"
            else:
                output_path = project.get_path("final_video")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            job_manager.update_progress(job_id, 0.2, "Starting Remotion render...")

            # Build render command
            cmd = [
                "node",
                str(render_script),
                "--project",
                str(project.root_dir),
                "--output",
                str(output_path),
                "--width",
                str(width),
                "--height",
                str(height),
                "--voiceover-path",
                "voiceover",
            ]

            # Run render
            result = subprocess.run(
                cmd,
                cwd=str(self.remotion_dir),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown render error"
                raise RuntimeError(f"Render failed: {error_msg}")

            job_manager.update_progress(job_id, 1.0, "Render complete")

            return {
                "output_path": str(output_path),
                "resolution": resolution,
                "width": width,
                "height": height,
            }

        return self.job_manager.submit_job(JobType.RENDER, project_id, task)

    def list_renders(self, project_id: str) -> list[dict[str, Any]]:
        """List rendered videos for a project.

        Args:
            project_id: The project ID.

        Returns:
            List of rendered video info.
        """
        from src.project import load_project

        project = load_project(self.projects_dir / project_id)
        output_files = list(project.output_dir.glob("*.mp4"))
        preview_files = list((project.output_dir / "preview").glob("*.mp4"))

        results = []
        for f in output_files + preview_files:
            results.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                    "is_preview": "preview" in str(f.parent),
                }
            )

        return results

    def get_video_path(self, project_id: str, filename: str) -> Path | None:
        """Get the path to a rendered video.

        Args:
            project_id: The project ID.
            filename: The video filename.

        Returns:
            Path to the video file, or None if not found.
        """
        from src.project import load_project

        project = load_project(self.projects_dir / project_id)

        # Check main output directory
        video_path = project.output_dir / filename
        if video_path.exists():
            return video_path

        # Check preview directory
        preview_path = project.output_dir / "preview" / filename
        if preview_path.exists():
            return preview_path

        return None
