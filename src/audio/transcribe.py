"""Audio transcription with word-level timestamps using Whisper."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .tts import WordTimestamp


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""

    text: str
    word_timestamps: list[WordTimestamp]
    duration_seconds: float
    language: str = "en"


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper for word-level timestamps."""

    def __init__(self, model: str = "base", device: str = "auto"):
        """Initialize Whisper transcriber.

        Args:
            model: Whisper model size. Options: tiny, base, small, medium, large
                   Larger models are more accurate but slower.
                   - tiny: ~1GB VRAM, fastest
                   - base: ~1GB VRAM, good balance
                   - small: ~2GB VRAM, better accuracy
                   - medium: ~5GB VRAM, high accuracy
                   - large: ~10GB VRAM, best accuracy
            device: Device to run on. "auto", "cpu", "cuda", or "mps"
        """
        self.model_name = model
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy load the Whisper model."""
        if self._model is not None:
            return self._model

        try:
            import whisper
        except ImportError:
            raise ImportError(
                "openai-whisper is required for transcription. "
                "Install it with: pip install openai-whisper"
            )

        # Determine device
        # Note: MPS has issues with float64, so we use CPU for Apple Silicon
        device = self.device
        if device == "auto":
            import torch
            if torch.cuda.is_available():
                device = "cuda"
            else:
                # MPS has dtype issues with Whisper, use CPU instead
                device = "cpu"

        self._model = whisper.load_model(self.model_name, device=device)
        return self._model

    def transcribe(self, audio_path: Path | str) -> TranscriptionResult:
        """Transcribe audio file and extract word-level timestamps.

        Args:
            audio_path: Path to the audio file (mp3, wav, etc.)

        Returns:
            TranscriptionResult with text, word timestamps, and duration
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()

        # Transcribe with word-level timestamps
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="en",
        )

        # Extract word timestamps from segments
        word_timestamps = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                word_timestamps.append(
                    WordTimestamp(
                        word=word_info["word"].strip(),
                        start_seconds=word_info["start"],
                        end_seconds=word_info["end"],
                    )
                )

        # Calculate duration from last word or segments
        duration = 0.0
        if word_timestamps:
            duration = word_timestamps[-1].end_seconds
        elif result.get("segments"):
            duration = result["segments"][-1]["end"]

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            word_timestamps=word_timestamps,
            duration_seconds=duration,
            language=result.get("language", "en"),
        )


class FasterWhisperTranscriber:
    """Transcribe audio using faster-whisper for improved performance."""

    def __init__(self, model: str = "base", device: str = "auto"):
        """Initialize faster-whisper transcriber.

        Args:
            model: Model size. Options: tiny, base, small, medium, large-v2
            device: Device to run on. "auto", "cpu", or "cuda"
        """
        self.model_name = model
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy load the faster-whisper model."""
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper is required for transcription. "
                "Install it with: pip install faster-whisper"
            )

        # Determine device and compute type
        device = self.device
        compute_type = "float16"

        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                else:
                    device = "cpu"
                    compute_type = "int8"
            except ImportError:
                device = "cpu"
                compute_type = "int8"

        if device == "cpu":
            compute_type = "int8"

        self._model = WhisperModel(
            self.model_name,
            device=device,
            compute_type=compute_type,
        )
        return self._model

    def transcribe(self, audio_path: Path | str) -> TranscriptionResult:
        """Transcribe audio file and extract word-level timestamps.

        Args:
            audio_path: Path to the audio file

        Returns:
            TranscriptionResult with text, word timestamps, and duration
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()

        # Transcribe with word-level timestamps
        segments, info = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="en",
        )

        # Extract word timestamps
        word_timestamps = []
        full_text_parts = []
        duration = 0.0

        for segment in segments:
            full_text_parts.append(segment.text)
            duration = max(duration, segment.end)

            if segment.words:
                for word in segment.words:
                    word_timestamps.append(
                        WordTimestamp(
                            word=word.word.strip(),
                            start_seconds=word.start,
                            end_seconds=word.end,
                        )
                    )

        return TranscriptionResult(
            text=" ".join(full_text_parts).strip(),
            word_timestamps=word_timestamps,
            duration_seconds=duration,
            language=info.language if info else "en",
        )


def get_audio_duration(audio_path: Path | str) -> float:
    """Get audio duration using ffprobe.

    Args:
        audio_path: Path to the audio file

    Returns:
        Duration in seconds
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        raise RuntimeError(f"Failed to get audio duration: {e}")

    raise RuntimeError(f"ffprobe failed for {audio_path}")


def get_transcriber(
    backend: str = "auto",
    model: str = "base",
    device: str = "auto",
) -> WhisperTranscriber | FasterWhisperTranscriber:
    """Get a transcriber instance.

    Args:
        backend: Which backend to use. "auto", "whisper", or "faster-whisper"
        model: Model size to use
        device: Device to run on

    Returns:
        A transcriber instance
    """
    if backend == "auto":
        # Try faster-whisper first, fall back to whisper
        try:
            import faster_whisper
            backend = "faster-whisper"
        except ImportError:
            try:
                import whisper
                backend = "whisper"
            except ImportError:
                raise ImportError(
                    "No Whisper backend available. Install one with:\n"
                    "  pip install openai-whisper\n"
                    "or:\n"
                    "  pip install faster-whisper"
                )

    if backend == "faster-whisper":
        return FasterWhisperTranscriber(model=model, device=device)
    elif backend == "whisper":
        return WhisperTranscriber(model=model, device=device)
    else:
        raise ValueError(f"Unknown transcription backend: {backend}")
