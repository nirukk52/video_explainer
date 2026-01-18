"""Music generation using Meta's MusicGen model.

Generates ambient/electronic background music appropriate for technical explainer videos.
Supports Apple Silicon (MPS), CUDA, and CPU backends.
"""

import os
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal


@dataclass
class MusicConfig:
    """Configuration for music generation."""

    # Model size: "small" (~300MB), "medium" (~1.5GB), "large" (~3.3GB)
    model_size: Literal["small", "medium", "large"] = "small"

    # Duration of each segment in seconds (MusicGen max is ~30s)
    segment_duration: int = 30

    # Target total duration in seconds (will loop/extend segments)
    target_duration: Optional[int] = None

    # Music style prompt
    style: str = "ambient electronic, subtle, no vocals, professional tech documentary"

    # Output format
    sample_rate: int = 32000

    # Volume level (0.0 to 1.0) for final output
    volume: float = 0.3

    # Device: "auto", "mps", "cuda", "cpu"
    device: str = "auto"


@dataclass
class MusicGenerationResult:
    """Result of music generation."""

    success: bool
    output_path: Optional[Path] = None
    duration_seconds: float = 0.0
    prompt_used: str = ""
    error_message: Optional[str] = None
    segments_generated: int = 0


# Music style presets for different video topics
MUSIC_STYLE_PRESETS = {
    "tech": "ambient electronic, subtle synthesizers, no vocals, professional tech documentary, modern, clean",
    "science": "ambient electronic, ethereal pads, no vocals, science documentary, wonder, discovery",
    "tutorial": "lo-fi beats, calm, no vocals, background music, focused, minimal",
    "dramatic": "cinematic ambient, building tension, no vocals, documentary score, epic subtle",
    "default": "ambient electronic, subtle, no vocals, professional documentary background music",
}

# Punchy style presets for YouTube Shorts (more energetic, attention-grabbing)
SHORTS_STYLE_PRESETS = {
    "tech": "electronic beats, punchy synths, energetic, no vocals, tech explainer, modern bass, driving rhythm, 120 bpm",
    "science": "electronic, wonder, discovery vibes, punchy drums, no vocals, energetic pads, rising energy",
    "tutorial": "upbeat lo-fi, punchy beats, no vocals, energetic but focused, modern, catchy rhythm",
    "dramatic": "cinematic electronic, building intensity, punchy drums, no vocals, epic drops, tension release",
    "hook": "attention-grabbing electronic, punchy intro, energetic drop, no vocals, bold synths, impactful",
    "default": "punchy electronic beats, energetic, no vocals, modern, driving rhythm, attention-grabbing, 115 bpm",
}


def get_music_prompt(topic: str, custom_style: Optional[str] = None) -> str:
    """Generate a music prompt based on video topic.

    Args:
        topic: The video topic (e.g., "LLM Inference", "Machine Learning")
        custom_style: Optional custom style override

    Returns:
        A prompt string for the music generator
    """
    if custom_style:
        return custom_style

    # Determine best preset based on topic keywords
    topic_lower = topic.lower()

    if any(kw in topic_lower for kw in ["llm", "ai", "machine learning", "neural", "gpu", "inference"]):
        preset = "tech"
    elif any(kw in topic_lower for kw in ["science", "physics", "biology", "chemistry", "research"]):
        preset = "science"
    elif any(kw in topic_lower for kw in ["tutorial", "how to", "guide", "learn"]):
        preset = "tutorial"
    elif any(kw in topic_lower for kw in ["dramatic", "impact", "revolution", "breakthrough"]):
        preset = "dramatic"
    else:
        preset = "default"

    return MUSIC_STYLE_PRESETS[preset]


def get_shorts_music_prompt(
    topic: str,
    beats: Optional[list] = None,
    custom_style: Optional[str] = None,
) -> str:
    """Generate a punchy music prompt for YouTube Shorts.

    Analyzes the beats content to determine the best music style.

    Args:
        topic: The video topic
        beats: List of beat dictionaries from shorts storyboard
        custom_style: Optional custom style override

    Returns:
        A prompt string optimized for shorts
    """
    if custom_style:
        return custom_style

    topic_lower = topic.lower()

    # Analyze beats for content keywords if available
    beat_keywords = []
    if beats:
        for beat in beats:
            caption = beat.get("caption_text", "").lower()
            beat_keywords.extend(caption.split())

    all_text = topic_lower + " " + " ".join(beat_keywords)

    # Determine preset based on content analysis
    if any(kw in all_text for kw in ["hook", "question", "why", "how", "secret", "truth"]):
        preset = "hook"
    elif any(kw in all_text for kw in ["llm", "ai", "machine learning", "neural", "gpu", "transformer", "token"]):
        preset = "tech"
    elif any(kw in all_text for kw in ["science", "physics", "biology", "chemistry", "research"]):
        preset = "science"
    elif any(kw in all_text for kw in ["tutorial", "how to", "guide", "learn", "step"]):
        preset = "tutorial"
    elif any(kw in all_text for kw in ["dramatic", "impact", "revolution", "breakthrough", "billion", "impossible"]):
        preset = "dramatic"
    else:
        preset = "default"

    return SHORTS_STYLE_PRESETS[preset]


def analyze_shorts_mood(beats: list) -> dict:
    """Analyze shorts beats to understand the emotional arc.

    Args:
        beats: List of beat dictionaries from shorts storyboard

    Returns:
        Dictionary with mood analysis
    """
    if not beats:
        return {"primary_mood": "energetic", "has_hook": False, "has_cta": False}

    # Keywords for different moods
    problem_keywords = ["problem", "issue", "impossible", "billion", "million", "complex", "difficult"]
    solution_keywords = ["solution", "answer", "solve", "insight", "elegant", "simple"]
    hook_keywords = ["?", "how", "why", "what", "secret", "truth", "actually"]
    cta_keywords = ["description", "link", "subscribe", "full video", "watch"]

    has_problem = False
    has_solution = False
    has_hook = False
    has_cta = False

    for beat in beats:
        caption = beat.get("caption_text", "").lower()

        if any(kw in caption for kw in problem_keywords):
            has_problem = True
        if any(kw in caption for kw in solution_keywords):
            has_solution = True
        if any(kw in caption for kw in hook_keywords):
            has_hook = True
        if any(kw in caption for kw in cta_keywords):
            has_cta = True

    # Determine primary mood
    if has_problem and has_solution:
        primary_mood = "journey"  # Problem → Solution arc
    elif has_problem:
        primary_mood = "tension"
    elif has_solution:
        primary_mood = "triumphant"
    else:
        primary_mood = "energetic"

    return {
        "primary_mood": primary_mood,
        "has_hook": has_hook,
        "has_cta": has_cta,
        "has_problem": has_problem,
        "has_solution": has_solution,
    }


class MusicGenerator:
    """Generates background music using Meta's MusicGen model."""

    def __init__(self, config: Optional[MusicConfig] = None):
        """Initialize the music generator.

        Args:
            config: Music generation configuration
        """
        self.config = config or MusicConfig()
        self._model = None
        self._processor = None
        self._device = None

    def _get_device(self) -> str:
        """Determine the best available device."""
        import torch

        if self.config.device != "auto":
            return self.config.device

        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _load_model(self):
        """Load the MusicGen model (lazy loading)."""
        if self._model is not None:
            return

        from transformers import AutoProcessor, MusicgenForConditionalGeneration
        import torch

        self._device = self._get_device()
        model_name = f"facebook/musicgen-{self.config.model_size}"

        print(f"Loading MusicGen model: {model_name}")
        print(f"Device: {self._device}")

        self._processor = AutoProcessor.from_pretrained(model_name)
        self._model = MusicgenForConditionalGeneration.from_pretrained(model_name)

        # Move model to device
        if self._device == "mps":
            # MPS requires float32 for some operations
            self._model = self._model.to(self._device)
        elif self._device == "cuda":
            self._model = self._model.to(self._device)
        # CPU stays as default

        print("Model loaded successfully")

    def generate_segment(self, prompt: str, duration_seconds: int = 30) -> tuple:
        """Generate a single music segment.

        Args:
            prompt: Text description of the desired music
            duration_seconds: Duration of the segment (max ~30s for MusicGen)

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        import torch

        self._load_model()

        # Prepare inputs
        inputs = self._processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )

        # Move inputs to device
        if self._device in ["mps", "cuda"]:
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

        # Calculate max new tokens based on duration
        # MusicGen generates at ~50 tokens per second of audio
        max_new_tokens = int(duration_seconds * 50)

        # Generate
        print(f"Generating {duration_seconds}s segment...")
        with torch.no_grad():
            audio_values = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                guidance_scale=3.0,
            )

        # Move back to CPU for processing
        audio_array = audio_values[0, 0].cpu().numpy()

        return audio_array, self.config.sample_rate

    def generate(
        self,
        output_path: Path,
        topic: str,
        target_duration: Optional[int] = None,
        custom_style: Optional[str] = None,
    ) -> MusicGenerationResult:
        """Generate background music for a video.

        Args:
            output_path: Path to save the output MP3 file
            topic: Video topic (used to determine music style)
            target_duration: Target duration in seconds (loops if needed)
            custom_style: Optional custom style prompt

        Returns:
            MusicGenerationResult with generation details
        """
        import numpy as np

        try:
            # Determine prompt
            prompt = get_music_prompt(topic, custom_style)

            # Determine target duration
            duration = target_duration or self.config.target_duration or 60

            # Calculate how many segments we need
            segment_duration = min(self.config.segment_duration, 30)  # MusicGen max is ~30s
            num_segments = max(1, (duration + segment_duration - 1) // segment_duration)

            print(f"Generating {duration}s of music ({num_segments} segment(s))")
            print(f"Prompt: {prompt}")

            # Generate segments
            all_audio = []
            for i in range(num_segments):
                seg_duration = min(segment_duration, duration - i * segment_duration)
                if seg_duration <= 0:
                    break

                audio, sr = self.generate_segment(prompt, seg_duration)
                all_audio.append(audio)

            # Concatenate segments
            if len(all_audio) > 1:
                # Add crossfade between segments for smooth transitions
                crossfade_samples = int(sr * 0.5)  # 0.5s crossfade
                combined = all_audio[0]

                for next_audio in all_audio[1:]:
                    # Simple crossfade
                    if len(combined) > crossfade_samples and len(next_audio) > crossfade_samples:
                        fade_out = np.linspace(1, 0, crossfade_samples)
                        fade_in = np.linspace(0, 1, crossfade_samples)

                        combined[-crossfade_samples:] *= fade_out
                        next_audio[:crossfade_samples] *= fade_in
                        combined[-crossfade_samples:] += next_audio[:crossfade_samples]
                        combined = np.concatenate([combined, next_audio[crossfade_samples:]])
                    else:
                        combined = np.concatenate([combined, next_audio])

                final_audio = combined
            else:
                final_audio = all_audio[0]

            # Trim or loop to exact target duration
            target_samples = int(duration * sr)
            if len(final_audio) > target_samples:
                final_audio = final_audio[:target_samples]
            elif len(final_audio) < target_samples:
                # Loop the audio to fill duration
                loops_needed = (target_samples // len(final_audio)) + 1
                final_audio = np.tile(final_audio, loops_needed)[:target_samples]

            # Apply fade in/out
            fade_in_samples = int(sr * 2)  # 2s fade in
            fade_out_samples = int(sr * 3)  # 3s fade out

            if len(final_audio) > fade_in_samples:
                fade_in = np.linspace(0, 1, fade_in_samples)
                final_audio[:fade_in_samples] *= fade_in

            if len(final_audio) > fade_out_samples:
                fade_out = np.linspace(1, 0, fade_out_samples)
                final_audio[-fade_out_samples:] *= fade_out

            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_audio(final_audio, sr, output_path)

            actual_duration = len(final_audio) / sr

            return MusicGenerationResult(
                success=True,
                output_path=output_path,
                duration_seconds=actual_duration,
                prompt_used=prompt,
                segments_generated=len(all_audio),
            )

        except Exception as e:
            return MusicGenerationResult(
                success=False,
                error_message=str(e),
                prompt_used=prompt if 'prompt' in dir() else "",
            )

    def _save_audio(self, audio: "np.ndarray", sample_rate: int, output_path: Path):
        """Save audio array to MP3 file.

        Args:
            audio: Audio samples as numpy array
            sample_rate: Sample rate in Hz
            output_path: Output file path
        """
        import scipy.io.wavfile as wavfile

        # Normalize audio to prevent clipping
        audio = audio / (np.abs(audio).max() + 1e-8)

        # Apply volume
        audio = audio * self.config.volume

        # Scale to int16 range
        audio_int16 = (audio * 32767).astype("int16")

        # Save as WAV first (scipy doesn't support MP3)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            wavfile.write(tmp_path, sample_rate, audio_int16)

        # Convert to MP3 using ffmpeg
        output_path_str = str(output_path)
        if not output_path_str.endswith(".mp3"):
            output_path_str += ".mp3"

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", tmp_path,
                    "-acodec", "libmp3lame",
                    "-b:a", "192k",
                    output_path_str,
                ],
                check=True,
                capture_output=True,
            )
        finally:
            # Clean up temp file
            os.unlink(tmp_path)

        print(f"Saved to: {output_path_str}")


def generate_for_project(
    project_dir: Path,
    topic: str,
    target_duration: Optional[int] = None,
    update_storyboard: bool = True,
) -> MusicGenerationResult:
    """Generate background music for a project.

    Args:
        project_dir: Path to project directory
        topic: Video topic for style selection
        target_duration: Target duration in seconds
        update_storyboard: Whether to update storyboard.json with music config

    Returns:
        MusicGenerationResult
    """
    # Create music directory
    music_dir = project_dir / "music"
    music_dir.mkdir(parents=True, exist_ok=True)

    output_path = music_dir / "background.mp3"

    # Generate music
    generator = MusicGenerator()
    result = generator.generate(
        output_path=output_path,
        topic=topic,
        target_duration=target_duration,
    )

    # Update storyboard if requested and generation succeeded
    if result.success and update_storyboard:
        _update_storyboard_with_music(project_dir, output_path)

    return result


def _update_storyboard_with_music(project_dir: Path, music_path: Path):
    """Update storyboard.json to include background music.

    Args:
        project_dir: Path to project directory
        music_path: Path to the generated music file
    """
    storyboard_path = project_dir / "storyboard" / "storyboard.json"

    if not storyboard_path.exists():
        print(f"Warning: Storyboard not found at {storyboard_path}")
        return

    try:
        with open(storyboard_path) as f:
            storyboard = json.load(f)

        # Get relative path from project root
        relative_path = music_path.relative_to(project_dir)

        # Update audio config
        if "audio" not in storyboard:
            storyboard["audio"] = {}

        storyboard["audio"]["background_music"] = {
            "path": str(relative_path),
            "volume": 0.3,
        }

        # Save updated storyboard
        with open(storyboard_path, "w") as f:
            json.dump(storyboard, f, indent=2)

        print(f"Updated storyboard with background music config")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not update storyboard: {e}")


def generate_for_short(
    project_dir: Path,
    topic: str,
    variant: str = "default",
    target_duration: Optional[int] = None,
    custom_style: Optional[str] = None,
    update_storyboard: bool = True,
) -> MusicGenerationResult:
    """Generate punchy background music for a YouTube Short.

    Analyzes the shorts storyboard to understand content and generates
    appropriate energetic music.

    Args:
        project_dir: Path to project directory
        topic: Video topic for style selection
        variant: Short variant name (default: "default")
        target_duration: Target duration in seconds (reads from storyboard if not provided)
        custom_style: Optional custom style override
        update_storyboard: Whether to update shorts_storyboard.json with music config

    Returns:
        MusicGenerationResult
    """
    # Load shorts storyboard
    storyboard_path = project_dir / "short" / variant / "storyboard" / "shorts_storyboard.json"

    beats = []
    if storyboard_path.exists():
        try:
            with open(storyboard_path) as f:
                storyboard = json.load(f)
            beats = storyboard.get("beats", [])

            # Get duration from storyboard if not provided
            if not target_duration:
                target_duration = int(storyboard.get("total_duration_seconds", 60))
                print(f"Duration from storyboard: {target_duration}s")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not read storyboard: {e}")

    if not target_duration:
        target_duration = 60

    # Analyze mood
    mood_analysis = analyze_shorts_mood(beats)
    print(f"Mood analysis: {mood_analysis}")

    # Get shorts-optimized prompt
    prompt = get_shorts_music_prompt(topic, beats, custom_style)

    # Enhance prompt based on mood analysis
    if mood_analysis["primary_mood"] == "journey":
        prompt += ", building energy, tension to release, satisfying progression"
    elif mood_analysis["primary_mood"] == "tension":
        prompt += ", building tension, dramatic, suspenseful undertones"
    elif mood_analysis["primary_mood"] == "triumphant":
        prompt += ", triumphant feel, uplifting, positive energy"

    print(f"Generated prompt: {prompt}")

    # Create music directory in short variant
    music_dir = project_dir / "short" / variant / "music"
    music_dir.mkdir(parents=True, exist_ok=True)

    output_path = music_dir / "background.mp3"

    # Configure for shorts: slightly higher volume, shorter fades
    config = MusicConfig(
        volume=0.35,  # Slightly louder for shorts
    )

    # Generate music
    generator = MusicGenerator(config)
    result = generator.generate(
        output_path=output_path,
        topic=topic,
        target_duration=target_duration,
        custom_style=prompt,
    )

    # Update storyboard if requested and generation succeeded
    if result.success and update_storyboard:
        _update_shorts_storyboard_with_music(project_dir, variant, output_path)

    return result


def _update_shorts_storyboard_with_music(project_dir: Path, variant: str, music_path: Path):
    """Update shorts_storyboard.json to include background music.

    Args:
        project_dir: Path to project directory
        variant: Short variant name
        music_path: Path to the generated music file
    """
    storyboard_path = project_dir / "short" / variant / "storyboard" / "shorts_storyboard.json"

    if not storyboard_path.exists():
        print(f"Warning: Shorts storyboard not found at {storyboard_path}")
        return

    try:
        with open(storyboard_path) as f:
            storyboard = json.load(f)

        # Get relative path from short variant root
        short_variant_dir = project_dir / "short" / variant
        relative_path = music_path.relative_to(short_variant_dir)

        # Update audio config
        if "audio" not in storyboard:
            storyboard["audio"] = {}

        storyboard["audio"]["background_music"] = {
            "path": str(relative_path),
            "volume": 0.35,
        }

        # Save updated storyboard
        with open(storyboard_path, "w") as f:
            json.dump(storyboard, f, indent=2)

        print(f"Updated shorts storyboard with background music config")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not update shorts storyboard: {e}")


# Import numpy for type hints
import numpy as np
