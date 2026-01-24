"""Voiceover generator using TTS providers."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..audio import EdgeTTS, TTSResult, WordTimestamp, get_tts_provider
from ..config import Config, TTSConfig, load_config
from .narration import SceneNarration

if TYPE_CHECKING:
    from ..short.models import ShortScript, ShortsStoryboard


@dataclass
class SceneVoiceover:
    """Generated voiceover for a single scene."""

    scene_id: str
    audio_path: Path
    duration_seconds: float
    word_timestamps: list[WordTimestamp] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "scene_id": self.scene_id,
            "audio_path": str(self.audio_path),
            "duration_seconds": self.duration_seconds,
            "word_timestamps": [
                {
                    "word": ts.word,
                    "start_seconds": ts.start_seconds,
                    "end_seconds": ts.end_seconds,
                }
                for ts in self.word_timestamps
            ],
        }


@dataclass
class ShortVoiceover:
    """Generated voiceover for a YouTube Short."""

    audio_path: Path
    duration_seconds: float
    word_timestamps: list[WordTimestamp] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "audio_path": str(self.audio_path),
            "duration_seconds": self.duration_seconds,
            "word_timestamps": [
                {
                    "word": ts.word,
                    "start_seconds": ts.start_seconds,
                    "end_seconds": ts.end_seconds,
                }
                for ts in self.word_timestamps
            ],
        }

    def save_manifest(self, path: Path) -> Path:
        """Save voiceover manifest to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    @classmethod
    def load_manifest(cls, path: Path) -> "ShortVoiceover":
        """Load short voiceover from manifest file."""
        with open(path) as f:
            data = json.load(f)

        return cls(
            audio_path=Path(data["audio_path"]),
            duration_seconds=data["duration_seconds"],
            word_timestamps=[
                WordTimestamp(
                    word=ts["word"],
                    start_seconds=ts["start_seconds"],
                    end_seconds=ts["end_seconds"],
                )
                for ts in data["word_timestamps"]
            ],
        )


@dataclass
class VoiceoverResult:
    """Result of voiceover generation for all scenes."""

    scenes: list[SceneVoiceover]
    total_duration_seconds: float
    output_dir: Path

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenes": [s.to_dict() for s in self.scenes],
            "total_duration_seconds": self.total_duration_seconds,
            "output_dir": str(self.output_dir),
        }

    def save_manifest(self, path: Path | None = None) -> Path:
        """Save voiceover manifest to JSON file."""
        if path is None:
            path = self.output_dir / "voiceover_manifest.json"

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return path

    @classmethod
    def load_manifest(cls, path: Path) -> "VoiceoverResult":
        """Load voiceover result from manifest file."""
        with open(path) as f:
            data = json.load(f)

        scenes = [
            SceneVoiceover(
                scene_id=s["scene_id"],
                audio_path=Path(s["audio_path"]),
                duration_seconds=s["duration_seconds"],
                word_timestamps=[
                    WordTimestamp(
                        word=ts["word"],
                        start_seconds=ts["start_seconds"],
                        end_seconds=ts["end_seconds"],
                    )
                    for ts in s["word_timestamps"]
                ],
            )
            for s in data["scenes"]
        ]

        return cls(
            scenes=scenes,
            total_duration_seconds=data["total_duration_seconds"],
            output_dir=Path(data["output_dir"]),
        )


class VoiceoverGenerator:
    """Generates voiceover audio for video scenes."""

    def __init__(
        self,
        config: Config | None = None,
        voice: str = "en-US-GuyNeural",
        provider: str | None = None,
    ):
        """Initialize voiceover generator.

        Args:
            config: Configuration object. If None, uses default config.
            voice: Voice to use for TTS (Edge TTS voice name).
            provider: TTS provider to use (elevenlabs, edge, mock). Defaults to edge.
        """
        self.config = config or load_config()
        self.voice = voice

        # Set provider in config if specified
        provider_name = provider or "edge"
        self.config.tts.provider = provider_name
        self.config.tts.voice_id = voice

        # Get the appropriate TTS provider
        self.tts = get_tts_provider(self.config)

    def generate_scene_voiceover(
        self,
        narration: SceneNarration,
        output_dir: Path,
    ) -> SceneVoiceover:
        """Generate voiceover for a single scene.

        Args:
            narration: Scene narration data.
            output_dir: Directory to save audio files.

        Returns:
            SceneVoiceover with audio path and timestamps.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"{narration.scene_id}.mp3"

        result = self.tts.generate_with_timestamps(
            narration.narration,
            audio_path,
        )

        return SceneVoiceover(
            scene_id=narration.scene_id,
            audio_path=result.audio_path,
            duration_seconds=result.duration_seconds,
            word_timestamps=result.word_timestamps,
        )

    def generate_all_voiceovers(
        self,
        output_dir: Path,
        narrations: list[SceneNarration],
    ) -> VoiceoverResult:
        """Generate voiceovers for all scenes.

        Args:
            output_dir: Directory to save audio files.
            narrations: List of narrations to generate voiceovers for.

        Returns:
            VoiceoverResult with all generated audio.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        scenes = []
        total_duration = 0.0

        for narration in narrations:
            print(f"Generating voiceover for: {narration.title}...")
            scene_voiceover = self.generate_scene_voiceover(narration, output_dir)
            scenes.append(scene_voiceover)
            total_duration += scene_voiceover.duration_seconds
            print(f"  Duration: {scene_voiceover.duration_seconds:.2f}s")

        result = VoiceoverResult(
            scenes=scenes,
            total_duration_seconds=total_duration,
            output_dir=output_dir,
        )

        # Save manifest
        manifest_path = result.save_manifest()
        print(f"\nVoiceover manifest saved to: {manifest_path}")
        print(f"Total duration: {total_duration:.2f}s ({total_duration/60:.1f} min)")

        return result

    def generate_short_voiceover(
        self,
        short_script: "ShortScript",
        output_dir: Path,
        filename: str = "short_voiceover.mp3",
    ) -> ShortVoiceover:
        """Generate voiceover for a YouTube Short.

        Combines all scene narrations and CTA into a single audio file
        with word-level timestamps for caption sync.

        Args:
            short_script: The short script with condensed narrations.
            output_dir: Directory to save audio files.
            filename: Name of the output audio file.

        Returns:
            ShortVoiceover with audio path and word timestamps.
        """
        from ..short.models import ShortScript  # Import here to avoid circular

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / filename

        # Build full narration from ShortScript.condensed_narration + CTA
        narration_parts = []

        # Use the condensed narration from the script level
        if short_script.condensed_narration:
            narration_parts.append(short_script.condensed_narration.strip())

        # Add CTA narration at the end
        if short_script.cta_narration:
            narration_parts.append(short_script.cta_narration.strip())

        # Join with pauses (TTS will add natural pauses at periods)
        full_narration = " ".join(narration_parts)

        print(f"Generating short voiceover ({len(full_narration)} chars)...")

        # Generate with timestamps
        result = self.tts.generate_with_timestamps(
            full_narration,
            audio_path,
        )

        short_voiceover = ShortVoiceover(
            audio_path=result.audio_path,
            duration_seconds=result.duration_seconds,
            word_timestamps=result.word_timestamps,
        )

        # Save manifest
        manifest_path = output_dir / "short_voiceover_manifest.json"
        short_voiceover.save_manifest(manifest_path)

        print(f"  Audio: {audio_path}")
        print(f"  Duration: {result.duration_seconds:.2f}s")
        print(f"  Words: {len(result.word_timestamps)}")

        return short_voiceover

    def process_manual_short_voiceover(
        self,
        audio_path: Path | str,
        output_dir: Path,
        whisper_model: str = "base",
    ) -> ShortVoiceover:
        """Process a manually recorded short voiceover.

        Uses Whisper to transcribe and generate word timestamps from
        a user-recorded audio file.

        Args:
            audio_path: Path to the recorded audio file.
            output_dir: Directory to save manifest and copy audio.
            whisper_model: Whisper model size for transcription.

        Returns:
            ShortVoiceover with audio path and word timestamps.
        """
        from ..audio.transcribe import get_transcriber

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy audio to output directory if not already there
        output_audio = output_dir / "short_voiceover.mp3"
        if audio_path.resolve() != output_audio.resolve():
            import shutil
            # Convert to mp3 if needed, or just copy
            if audio_path.suffix.lower() != ".mp3":
                # Use ffmpeg to convert
                import subprocess
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(audio_path), "-codec:a", "libmp3lame", "-q:a", "2", str(output_audio)],
                    check=True,
                    capture_output=True,
                )
                print(f"  Converted {audio_path.suffix} to mp3")
            else:
                shutil.copy(audio_path, output_audio)

        print(f"Processing manual voiceover: {audio_path.name}")
        print(f"  Using Whisper model: {whisper_model}")

        # Transcribe with Whisper
        transcriber = get_transcriber(model=whisper_model)
        result = transcriber.transcribe(output_audio)

        short_voiceover = ShortVoiceover(
            audio_path=output_audio,
            duration_seconds=result.duration_seconds,
            word_timestamps=result.word_timestamps,
        )

        # Save manifest
        manifest_path = output_dir / "short_voiceover_manifest.json"
        short_voiceover.save_manifest(manifest_path)

        print(f"  Audio: {output_audio}")
        print(f"  Duration: {result.duration_seconds:.2f}s")
        print(f"  Words transcribed: {len(result.word_timestamps)}")

        return short_voiceover

    @staticmethod
    def export_short_recording_script(
        short_script: "ShortScript",
        output_path: Path | str,
        with_tags: bool = False,
    ) -> Path:
        """Export a recording script for manual voiceover recording.

        Creates a text file with the full narration text that a voice
        actor can read to record the short's audio.

        Args:
            short_script: The short script with condensed narrations.
            output_path: Path to save the recording script.
            with_tags: Include delivery tags for voice direction.

        Returns:
            Path to the saved recording script.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Recording Script: {short_script.title}",
            f"# Duration target: ~{short_script.total_duration_seconds}s",
            "",
            "=" * 60,
            "FULL NARRATION",
            "=" * 60,
            "",
        ]

        # Add main narration from script level
        if short_script.condensed_narration:
            if with_tags:
                lines.append("[Main Narration]")
            lines.append(short_script.condensed_narration.strip())
            lines.append("")

        # Add CTA
        if short_script.cta_narration:
            if with_tags:
                lines.append("[CTA - Call to Action]")
            lines.append(short_script.cta_narration.strip())
            lines.append("")

        lines.extend([
            "",
            "=" * 60,
            "RECORDING TIPS",
            "=" * 60,
            "",
            "1. Speak clearly and at a natural pace",
            "2. Keep energy high - this is a short-form video",
            "3. Pause briefly between sections for natural breaks",
            f"4. Total duration should be around {short_script.total_duration_seconds}s",
            "",
            "Save the recording as: short_voiceover.mp3 (or .wav, .m4a)",
        ])

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return output_path
