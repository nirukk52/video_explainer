"""Video generation pipeline orchestrator."""

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..animation.renderer import (
    AnimationRenderer,
    RemotionRenderer,
    MockRenderer,
    RenderResult,
    get_renderer,
)
from ..audio.tts import get_tts_provider
from ..composition.composer import CompositionResult, VideoComposer
from ..config import Config, load_config
from ..ingestion import parse_document
from ..models import ParsedDocument, Script, ContentAnalysis
from ..script import ScriptGenerator
from ..understanding import ContentAnalyzer


@dataclass
class PipelineResult:
    """Result of the video generation pipeline."""

    success: bool
    output_path: Path | None
    duration_seconds: float
    stages_completed: list[str]
    error_message: str | None = None
    metadata: dict = field(default_factory=dict)


class VideoPipeline:
    """Orchestrate the complete video generation pipeline.

    The pipeline follows the configured providers:
    - LLM: Uses config.llm.provider (mock or real)
    - TTS: Uses config.tts.provider (mock or elevenlabs)
    - Animation: Uses Remotion for real rendering, or mock for testing
    """

    def __init__(
        self,
        config: Config | None = None,
        output_dir: Path | str = "output",
        use_remotion: bool = True,
    ):
        """Initialize the pipeline.

        Args:
            config: Configuration object. If None, loads from config.yaml.
            output_dir: Directory for output files.
            use_remotion: If True, use Remotion for animation. If False, use mock.
        """
        self.config = config or load_config()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components based on config
        self.analyzer = ContentAnalyzer(self.config)
        self.script_gen = ScriptGenerator(self.config)
        self.tts = get_tts_provider(self.config)
        self.composer = VideoComposer(self.config)

        # Initialize renderer
        self.use_remotion = use_remotion
        if use_remotion:
            try:
                self.renderer: AnimationRenderer = RemotionRenderer(self.config)
            except RuntimeError:
                # Fall back to mock if Remotion not available
                self.renderer = MockRenderer(self.config)
                self.use_remotion = False
        else:
            self.renderer = MockRenderer(self.config)

        # Progress callback
        self._progress_callback: Callable[[str, float], None] | None = None

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set a callback for progress updates.

        Args:
            callback: Function that receives (stage_name, progress_percent)
        """
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: float) -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(stage, progress)

    def _get_video_duration(self, video_path: Path) -> float:
        """Get duration of a video file."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (ValueError, subprocess.SubprocessError):
            pass
        return 0.0

    def generate_from_document(
        self,
        source_path: Path | str,
        target_duration: int = 180,
    ) -> PipelineResult:
        """Generate a complete video from a source document.

        Uses configured providers:
        - LLM provider from config for content analysis
        - TTS provider from config for audio generation
        - Remotion for animation rendering (with script-based visual cues)

        Args:
            source_path: Path to the source document
            target_duration: Target video duration in seconds

        Returns:
            PipelineResult with output info
        """
        stages_completed = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"video_{timestamp}"

        try:
            # Stage 1: Parse document
            self._report_progress("parsing", 0)
            document = parse_document(source_path)
            stages_completed.append("parsing")
            self._report_progress("parsing", 100)

            # Stage 2: Analyze content (uses configured LLM provider)
            self._report_progress("analysis", 0)
            analysis = self.analyzer.analyze(document)
            stages_completed.append("analysis")
            self._report_progress("analysis", 100)

            # Stage 3: Generate script (uses configured LLM provider)
            self._report_progress("script", 0)
            script = self.script_gen.generate(document, analysis, target_duration)
            stages_completed.append("script")
            self._report_progress("script", 100)

            # Save script for review/debugging
            script_path = self.output_dir / "scripts" / f"{project_name}.json"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            self.script_gen.save_script(script, str(script_path))

            # Stage 4: Generate audio (uses configured TTS provider)
            self._report_progress("audio", 0)
            audio_dir = self.output_dir / "audio" / project_name
            audio_dir.mkdir(parents=True, exist_ok=True)

            audio_files = []
            for i, scene in enumerate(script.scenes):
                audio_path = audio_dir / f"scene_{scene.scene_id:02d}.mp3"
                self.tts.generate(scene.voiceover, audio_path)
                audio_files.append(audio_path)
                progress = (i + 1) / len(script.scenes) * 100
                self._report_progress("audio", progress)

            stages_completed.append("audio")

            # Stage 5: Render animation from script
            self._report_progress("animation", 0)
            video_dir = self.output_dir / "video" / project_name
            video_dir.mkdir(parents=True, exist_ok=True)

            animation_path = video_dir / "animation.mp4"

            # Use Remotion to render from script (generates visuals from visual cues)
            render_result = self.renderer.render_from_script(script, animation_path)

            if not render_result.success:
                return PipelineResult(
                    success=False,
                    output_path=None,
                    duration_seconds=0,
                    stages_completed=stages_completed,
                    error_message=f"Animation failed: {render_result.error_message}",
                )

            stages_completed.append("animation")
            self._report_progress("animation", 100)

            # Stage 6: Compose final video (combine animation + audio)
            self._report_progress("composition", 0)

            # Combine all audio files into one
            combined_audio = video_dir / "combined_audio.mp3"
            self._combine_audio_files(audio_files, combined_audio)

            # Overlay audio on animation
            final_output = video_dir / "final.mp4"
            composition_result = self.composer.compose_with_audio_overlay(
                animation_path,
                combined_audio,
                final_output,
            )

            stages_completed.append("composition")
            self._report_progress("composition", 100)

            return PipelineResult(
                success=True,
                output_path=final_output,
                duration_seconds=composition_result.duration_seconds,
                stages_completed=stages_completed,
                metadata={
                    "script_path": str(script_path),
                    "audio_dir": str(audio_dir),
                    "scene_count": len(script.scenes),
                    "file_size_bytes": composition_result.file_size_bytes,
                    "animation_renderer": "remotion" if self.use_remotion else "mock",
                    "tts_provider": self.config.tts.provider,
                    "llm_provider": self.config.llm.provider,
                },
            )

        except Exception as e:
            return PipelineResult(
                success=False,
                output_path=None,
                duration_seconds=0,
                stages_completed=stages_completed,
                error_message=str(e),
            )

    def generate_from_script(
        self,
        script_path: Path | str,
    ) -> PipelineResult:
        """Generate a video from an existing script.

        Skips parsing and analysis stages, uses the provided script directly.

        Args:
            script_path: Path to the script JSON file

        Returns:
            PipelineResult with output info
        """
        script = ScriptGenerator.load_script(str(script_path))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"video_{timestamp}"
        stages_completed = []

        try:
            # Stage 1: Generate audio (uses configured TTS provider)
            self._report_progress("audio", 0)
            audio_dir = self.output_dir / "audio" / project_name
            audio_dir.mkdir(parents=True, exist_ok=True)

            audio_files = []
            for i, scene in enumerate(script.scenes):
                audio_path = audio_dir / f"scene_{scene.scene_id:02d}.mp3"
                self.tts.generate(scene.voiceover, audio_path)
                audio_files.append(audio_path)
                progress = (i + 1) / len(script.scenes) * 100
                self._report_progress("audio", progress)

            stages_completed.append("audio")

            # Stage 2: Render animation from script
            self._report_progress("animation", 0)
            video_dir = self.output_dir / "video" / project_name
            video_dir.mkdir(parents=True, exist_ok=True)

            animation_path = video_dir / "animation.mp4"
            render_result = self.renderer.render_from_script(script, animation_path)

            if not render_result.success:
                return PipelineResult(
                    success=False,
                    output_path=None,
                    duration_seconds=0,
                    stages_completed=stages_completed,
                    error_message=f"Animation failed: {render_result.error_message}",
                )

            stages_completed.append("animation")
            self._report_progress("animation", 100)

            # Stage 3: Compose final video
            self._report_progress("composition", 0)

            combined_audio = video_dir / "combined_audio.mp3"
            self._combine_audio_files(audio_files, combined_audio)

            final_output = video_dir / "final.mp4"
            composition_result = self.composer.compose_with_audio_overlay(
                animation_path,
                combined_audio,
                final_output,
            )

            stages_completed.append("composition")
            self._report_progress("composition", 100)

            return PipelineResult(
                success=True,
                output_path=final_output,
                duration_seconds=composition_result.duration_seconds,
                stages_completed=stages_completed,
                metadata={
                    "script_path": str(script_path),
                    "scene_count": len(script.scenes),
                    "file_size_bytes": composition_result.file_size_bytes,
                    "animation_renderer": "remotion" if self.use_remotion else "mock",
                },
            )

        except Exception as e:
            return PipelineResult(
                success=False,
                output_path=None,
                duration_seconds=0,
                stages_completed=stages_completed,
                error_message=str(e),
            )

    def _combine_audio_files(self, audio_files: list[Path], output_path: Path) -> None:
        """Combine multiple audio files into one using FFmpeg."""
        if not audio_files:
            raise ValueError("No audio files to combine")

        if len(audio_files) == 1:
            shutil.copy(audio_files[0], output_path)
            return

        # Create concat file for FFmpeg
        concat_file = output_path.parent / "audio_concat.txt"
        with open(concat_file, "w") as f:
            for audio_path in audio_files:
                f.write(f"file '{audio_path.absolute()}'\n")

        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"Audio concatenation failed: {result.stderr}")

        finally:
            concat_file.unlink(missing_ok=True)

    def quick_test(self) -> PipelineResult:
        """Run a quick test of the pipeline with minimal settings.

        Uses current configuration but with a simple test document.

        Returns:
            PipelineResult with test output info
        """
        test_content = """# Test Video

## Introduction

This is a test video generated by the video explainer system.
It demonstrates the complete pipeline from parsing to final video.

## Key Concepts

The pipeline processes documents through multiple stages:
- Parsing extracts structure
- Analysis identifies key concepts
- Scripts are generated with visual cues
- Audio is synthesized
- Animations are rendered
- Everything is composed into final video
"""
        test_dir = self.output_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_doc = test_dir / "test_document.md"
        test_doc.write_text(test_content)

        return self.generate_from_document(
            test_doc,
            target_duration=30,
        )
