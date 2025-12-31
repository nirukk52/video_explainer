"""Project service wrapping src/project/loader.py."""

import json
from pathlib import Path
from typing import Any

from ..models.responses import (
    ProjectSummary,
    ProjectDetail,
    FileStatus,
    VideoSettings,
    TTSSettings,
    StyleSettings,
    Narration,
)


class ProjectService:
    """Service for project operations.

    Wraps the existing project loader without modifying it.
    """

    def __init__(self, projects_dir: Path | str = Path("projects")):
        """Initialize the project service.

        Args:
            projects_dir: Path to the projects directory.
        """
        self.projects_dir = Path(projects_dir)

    def list_projects(self) -> list[ProjectSummary]:
        """List all projects with summary info.

        Returns:
            List of project summaries.
        """
        from src.project import list_projects

        projects = list_projects(self.projects_dir)
        return [self._to_summary(p) for p in projects]

    def get_project(self, project_id: str) -> ProjectDetail:
        """Get detailed project information.

        Args:
            project_id: The project ID.

        Returns:
            Detailed project information.

        Raises:
            FileNotFoundError: If project doesn't exist.
        """
        project = self._load_project(project_id)
        return self._to_detail(project)

    def create_project(
        self, project_id: str, title: str, description: str = ""
    ) -> ProjectDetail:
        """Create a new project.

        Args:
            project_id: Unique project identifier.
            title: Project title.
            description: Optional description.

        Returns:
            The created project details.

        Raises:
            ValueError: If project already exists.
        """
        from src.project.loader import create_project

        project = create_project(
            project_id=project_id,
            title=title,
            projects_dir=self.projects_dir,
            description=description,
        )
        return self._to_detail(project)

    def delete_project(self, project_id: str) -> None:
        """Delete a project.

        Args:
            project_id: The project ID.

        Raises:
            FileNotFoundError: If project doesn't exist.
        """
        import shutil

        project_path = self.projects_dir / project_id
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        shutil.rmtree(project_path)

    def get_narrations(self, project_id: str) -> list[Narration]:
        """Get narrations for a project.

        Args:
            project_id: The project ID.

        Returns:
            List of narrations.
        """
        project = self._load_project(project_id)
        try:
            scene_narrations = project.load_narrations()
            return [
                Narration(
                    scene_id=sn.scene_id,
                    title=sn.title,
                    duration_seconds=sn.duration_seconds,
                    narration=sn.narration,
                )
                for sn in scene_narrations
            ]
        except FileNotFoundError:
            return []

    def update_narration(
        self,
        project_id: str,
        scene_id: str,
        narration: str,
        title: str | None = None,
        duration_seconds: int | None = None,
    ) -> Narration:
        """Update a narration.

        Args:
            project_id: The project ID.
            scene_id: The scene ID.
            narration: New narration text.
            title: Optional new title.
            duration_seconds: Optional duration override.

        Returns:
            The updated narration.

        Raises:
            FileNotFoundError: If project or narration doesn't exist.
        """
        project = self._load_project(project_id)
        narration_path = project.get_path("narration")

        if not narration_path.exists():
            raise FileNotFoundError(f"Narrations file not found for project: {project_id}")

        with open(narration_path) as f:
            data = json.load(f)

        # Find and update the scene
        scene_found = False
        for scene in data.get("scenes", []):
            if scene.get("scene_id") == scene_id:
                scene["narration"] = narration
                if title is not None:
                    scene["title"] = title
                if duration_seconds is not None:
                    scene["duration_seconds"] = duration_seconds
                scene_found = True
                break

        if not scene_found:
            raise FileNotFoundError(f"Scene not found: {scene_id}")

        # Save updated narrations
        with open(narration_path, "w") as f:
            json.dump(data, f, indent=2)

        # Return the updated narration
        for scene in data["scenes"]:
            if scene["scene_id"] == scene_id:
                return Narration(
                    scene_id=scene["scene_id"],
                    title=scene["title"],
                    duration_seconds=scene["duration_seconds"],
                    narration=scene["narration"],
                )

        raise FileNotFoundError(f"Scene not found after update: {scene_id}")

    def add_narration(
        self,
        project_id: str,
        scene_id: str,
        title: str,
        narration: str,
        duration_seconds: int = 15,
    ) -> Narration:
        """Add a new narration.

        Args:
            project_id: The project ID.
            scene_id: The new scene ID.
            title: Scene title.
            narration: Narration text.
            duration_seconds: Duration in seconds.

        Returns:
            The created narration.
        """
        project = self._load_project(project_id)
        narration_path = project.get_path("narration")
        narration_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing or create new
        if narration_path.exists():
            with open(narration_path) as f:
                data = json.load(f)
        else:
            data = {"scenes": []}

        # Check if scene already exists
        for scene in data.get("scenes", []):
            if scene.get("scene_id") == scene_id:
                raise ValueError(f"Scene already exists: {scene_id}")

        # Add new scene
        new_scene = {
            "scene_id": scene_id,
            "title": title,
            "duration_seconds": duration_seconds,
            "narration": narration,
        }
        data["scenes"].append(new_scene)

        # Save
        with open(narration_path, "w") as f:
            json.dump(data, f, indent=2)

        return Narration(**new_scene)

    def delete_narration(self, project_id: str, scene_id: str) -> None:
        """Delete a narration.

        Args:
            project_id: The project ID.
            scene_id: The scene ID to delete.

        Raises:
            FileNotFoundError: If project or scene doesn't exist.
        """
        project = self._load_project(project_id)
        narration_path = project.get_path("narration")

        if not narration_path.exists():
            raise FileNotFoundError(f"Narrations file not found for project: {project_id}")

        with open(narration_path) as f:
            data = json.load(f)

        original_count = len(data.get("scenes", []))
        data["scenes"] = [s for s in data.get("scenes", []) if s.get("scene_id") != scene_id]

        if len(data["scenes"]) == original_count:
            raise FileNotFoundError(f"Scene not found: {scene_id}")

        with open(narration_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_storyboard(self, project_id: str) -> dict[str, Any]:
        """Get the storyboard for a project.

        Args:
            project_id: The project ID.

        Returns:
            The storyboard data.

        Raises:
            FileNotFoundError: If storyboard doesn't exist.
        """
        project = self._load_project(project_id)
        return project.load_storyboard()

    def update_storyboard(self, project_id: str, storyboard: dict[str, Any]) -> dict[str, Any]:
        """Update the storyboard.

        Args:
            project_id: The project ID.
            storyboard: New storyboard data.

        Returns:
            The updated storyboard.
        """
        project = self._load_project(project_id)
        project.save_storyboard(storyboard)
        return storyboard

    def _load_project(self, project_id: str):
        """Load a project by ID.

        Args:
            project_id: The project ID.

        Returns:
            The loaded Project object.

        Raises:
            FileNotFoundError: If project doesn't exist.
        """
        from src.project import load_project

        return load_project(self.projects_dir / project_id)

    def _to_summary(self, project) -> ProjectSummary:
        """Convert a Project to a ProjectSummary.

        Args:
            project: The Project object.

        Returns:
            A ProjectSummary.
        """
        narration_path = project.get_path("narration")
        storyboard_path = project.get_path("storyboard")
        output_files = list(project.output_dir.glob("*.mp4"))
        voiceover_files = project.get_voiceover_files()

        return ProjectSummary(
            id=project.id,
            title=project.title,
            description=project.description,
            has_narrations=narration_path.exists(),
            has_voiceovers=len(voiceover_files) > 0,
            has_storyboard=storyboard_path.exists(),
            has_render=len(output_files) > 0,
        )

    def _to_detail(self, project) -> ProjectDetail:
        """Convert a Project to a ProjectDetail.

        Args:
            project: The Project object.

        Returns:
            A ProjectDetail.
        """
        narration_path = project.get_path("narration")
        storyboard_path = project.get_path("storyboard")
        sfx_dir = project.root_dir / "sfx"

        # Count narrations
        narrations_count = 0
        if narration_path.exists():
            try:
                with open(narration_path) as f:
                    data = json.load(f)
                narrations_count = len(data.get("scenes", []))
            except (json.JSONDecodeError, KeyError):
                pass

        # Count voiceovers
        voiceover_files = project.get_voiceover_files()

        # List rendered videos
        output_files = list(project.output_dir.glob("*.mp4"))
        rendered_videos = [f.name for f in output_files]

        # Check SFX
        has_sfx = sfx_dir.exists() and any(sfx_dir.glob("*.wav"))

        return ProjectDetail(
            id=project.id,
            title=project.title,
            description=project.description,
            version=project.version,
            video=VideoSettings(
                width=project.video.width,
                height=project.video.height,
                fps=project.video.fps,
                target_duration_seconds=project.video.target_duration_seconds,
            ),
            tts=TTSSettings(
                provider=project.tts.provider,
                voice_id=project.tts.voice_id,
            ),
            style=StyleSettings(
                background_color=project.style.background_color,
                primary_color=project.style.primary_color,
                secondary_color=project.style.secondary_color,
                font_family=project.style.font_family,
            ),
            files=FileStatus(
                narrations_count=narrations_count,
                voiceover_count=len(voiceover_files),
                has_storyboard=storyboard_path.exists(),
                rendered_videos=rendered_videos,
                has_sfx=has_sfx,
            ),
        )
