"""Project loader for video explainer projects.

A project is a self-contained directory with all files needed for a video:
- config.json: Project configuration
- narration/: Scene narration scripts
- voiceover/: Generated audio files
- storyboard/: Storyboard definitions
- remotion/: Video-specific Remotion components
- output/: Generated videos and previews
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VideoConfig:
    """Video rendering configuration."""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    target_duration_seconds: int = 180


@dataclass
class TTSConfig:
    """Text-to-speech configuration."""

    provider: str = "elevenlabs"
    voice_id: str = "pNInz6obpgDQGcFmaJgB"


@dataclass
class StyleConfig:
    """Visual style configuration."""

    background_color: str = "#f4f4f5"
    primary_color: str = "#00d9ff"
    secondary_color: str = "#ff6b35"
    font_family: str = "Inter"


@dataclass
class SceneNarration:
    """Narration for a single scene."""

    scene_id: str
    title: str
    duration_seconds: int
    narration: str


@dataclass
class Project:
    """A video explainer project."""

    id: str
    title: str
    description: str
    version: str
    root_dir: Path
    video: VideoConfig
    tts: TTSConfig
    style: StyleConfig
    _config: dict = field(default_factory=dict, repr=False)

    @property
    def input_dir(self) -> Path:
        """Directory for source input files."""
        return self.root_dir / "input"

    @property
    def script_dir(self) -> Path:
        """Directory for generated scripts."""
        return self.root_dir / "script"

    @property
    def narration_dir(self) -> Path:
        """Directory for narration files."""
        return self.root_dir / "narration"

    @property
    def voiceover_dir(self) -> Path:
        """Directory for voiceover audio files."""
        return self.root_dir / "voiceover"

    @property
    def storyboard_dir(self) -> Path:
        """Directory for storyboard files."""
        return self.root_dir / "storyboard"

    @property
    def remotion_dir(self) -> Path:
        """Directory for Remotion components."""
        return self.root_dir / "remotion"

    @property
    def output_dir(self) -> Path:
        """Directory for output files."""
        return self.root_dir / "output"

    @property
    def short_dir(self) -> Path:
        """Directory for YouTube Shorts."""
        return self.root_dir / "short"

    @property
    def plan_dir(self) -> Path:
        """Directory for video plan files."""
        return self.root_dir / "plan"

    def get_short_variant_dir(self, variant: str = "default") -> Path:
        """Get directory for a specific short variant.

        Args:
            variant: Variant name (default: "default").

        Returns:
            Path to the variant directory.
        """
        return self.short_dir / variant

    def get_path(self, key: str) -> Path:
        """Get a path from the project config.

        Args:
            key: Path key from config.paths (e.g., 'script', 'narration')

        Returns:
            Absolute path to the file or directory.
        """
        paths = self._config.get("paths", {})
        relative_path = paths.get(key, key)
        return self.root_dir / relative_path

    def load_narrations(self) -> list[SceneNarration]:
        """Load narration scripts from the project.

        Returns:
            List of SceneNarration objects.
        """
        narration_path = self.get_path("narration")
        if not narration_path.exists():
            raise FileNotFoundError(f"Narration file not found: {narration_path}")

        with open(narration_path) as f:
            data = json.load(f)

        return [
            SceneNarration(
                scene_id=scene["scene_id"],
                title=scene["title"],
                duration_seconds=scene["duration_seconds"],
                narration=scene["narration"],
            )
            for scene in data.get("scenes", [])
        ]

    def load_voiceover_manifest(self) -> dict[str, Any]:
        """Load the voiceover manifest.

        Returns:
            Voiceover manifest data.
        """
        manifest_path = self.get_path("voiceover_manifest")
        if not manifest_path.exists():
            raise FileNotFoundError(f"Voiceover manifest not found: {manifest_path}")

        with open(manifest_path) as f:
            return json.load(f)

    def load_storyboard(self) -> dict[str, Any]:
        """Load the storyboard.

        Returns:
            Storyboard data.
        """
        storyboard_path = self.get_path("storyboard")
        if not storyboard_path.exists():
            raise FileNotFoundError(f"Storyboard not found: {storyboard_path}")

        with open(storyboard_path) as f:
            return json.load(f)

    def save_storyboard(self, storyboard: dict[str, Any]) -> Path:
        """Save a storyboard to the project.

        Args:
            storyboard: Storyboard data to save.

        Returns:
            Path to the saved storyboard.
        """
        storyboard_path = self.get_path("storyboard")
        storyboard_path.parent.mkdir(parents=True, exist_ok=True)

        with open(storyboard_path, "w") as f:
            json.dump(storyboard, f, indent=2)

        return storyboard_path

    def get_voiceover_files(self) -> list[Path]:
        """Get all voiceover audio files.

        Returns:
            List of paths to audio files.
        """
        voiceover_dir = self.voiceover_dir
        if not voiceover_dir.exists():
            return []

        return sorted(voiceover_dir.glob("*.mp3"))

    def get_scene_audio(self, scene_id: str) -> Path | None:
        """Get the audio file for a specific scene.

        Args:
            scene_id: Scene identifier.

        Returns:
            Path to the audio file, or None if not found.
        """
        audio_path = self.voiceover_dir / f"{scene_id}.mp3"
        return audio_path if audio_path.exists() else None

    def ensure_directories(self) -> None:
        """Ensure all project directories exist."""
        for dir_path in [
            self.input_dir,
            self.script_dir,
            self.narration_dir,
            self.voiceover_dir,
            self.storyboard_dir,
            self.remotion_dir,
            self.output_dir,
            self.output_dir / "preview",
            self.plan_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


def load_project(project_path: str | Path) -> Project:
    """Load a project from a directory.

    Args:
        project_path: Path to the project directory or config file.

    Returns:
        Loaded Project object.

    Raises:
        FileNotFoundError: If project directory or config doesn't exist.
        ValueError: If config is invalid.
    """
    project_path = Path(project_path)

    # Handle both directory and config file paths
    if project_path.is_file():
        config_path = project_path
        root_dir = project_path.parent
    else:
        root_dir = project_path
        config_path = root_dir / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Project config not found: {config_path}")

    with open(config_path) as f:
        config = json.load(f)

    # Parse video config
    video_data = config.get("video", {})
    resolution = video_data.get("resolution", {})
    video_config = VideoConfig(
        width=resolution.get("width", 1920),
        height=resolution.get("height", 1080),
        fps=video_data.get("fps", 30),
        target_duration_seconds=video_data.get("target_duration_seconds", 180),
    )

    # Parse TTS config
    tts_data = config.get("tts", {})
    tts_config = TTSConfig(
        provider=tts_data.get("provider", "elevenlabs"),
        voice_id=tts_data.get("voice_id", ""),
    )

    # Parse style config
    style_data = config.get("style", {})
    style_config = StyleConfig(
        background_color=style_data.get("background_color", "#f4f4f5"),
        primary_color=style_data.get("primary_color", "#00d9ff"),
        secondary_color=style_data.get("secondary_color", "#ff6b35"),
        font_family=style_data.get("font_family", "Inter"),
    )

    return Project(
        id=config.get("id", root_dir.name),
        title=config.get("title", "Untitled Project"),
        description=config.get("description", ""),
        version=config.get("version", "1.0.0"),
        root_dir=root_dir.resolve(),
        video=video_config,
        tts=tts_config,
        style=style_config,
        _config=config,
    )


def list_projects(projects_dir: str | Path = "projects") -> list[Project]:
    """List all available projects.

    Args:
        projects_dir: Path to the projects directory.

    Returns:
        List of loaded Project objects.
    """
    projects_dir = Path(projects_dir)
    if not projects_dir.exists():
        return []

    projects = []
    for subdir in sorted(projects_dir.iterdir()):
        if subdir.is_dir() and (subdir / "config.json").exists():
            try:
                projects.append(load_project(subdir))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load project {subdir}: {e}")

    return projects


def create_project(
    project_id: str,
    title: str,
    projects_dir: str | Path = "projects",
    description: str = "",
) -> Project:
    """Create a new project with default structure.

    Args:
        project_id: Unique identifier for the project.
        title: Human-readable title.
        projects_dir: Parent directory for projects.
        description: Optional project description.

    Returns:
        The created Project object.
    """
    projects_dir = Path(projects_dir)
    project_dir = projects_dir / project_id

    if project_dir.exists():
        raise ValueError(f"Project already exists: {project_dir}")

    # Create directory structure
    project_dir.mkdir(parents=True)

    # Create config
    config = {
        "id": project_id,
        "title": title,
        "description": description,
        "version": "1.0.0",
        "source": {"document": "input/source.md", "type": "markdown"},
        "video": {
            "resolution": {"width": 1920, "height": 1080},
            "fps": 30,
            "target_duration_seconds": 180,
        },
        "tts": {"provider": "elevenlabs", "voice_id": ""},
        "style": {
            "background_color": "#f4f4f5",
            "primary_color": "#00d9ff",
            "secondary_color": "#ff6b35",
            "font_family": "Inter",
        },
        "paths": {
            "script": "script/script.json",
            "narration": "narration/narrations.json",
            "voiceover": "voiceover/",
            "voiceover_manifest": "voiceover/manifest.json",
            "storyboard": "storyboard/storyboard.json",
            "remotion_scenes": "remotion/scenes/",
            "remotion_props": "remotion/props.json",
            "output": "output/",
            "final_video": "output/final.mp4",
        },
    }

    config_path = project_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Load and initialize the project
    project = load_project(project_dir)
    project.ensure_directories()

    return project
