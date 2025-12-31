"""Sound library for frame-accurate SFX.

This module generates high-quality sounds designed to sync with specific
animation events in explainer videos.

Sound Design Principles:
- Subtle mix (-18 to -24dB)
- Crisp and clean
- Semantically appropriate for animation events
"""

import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100

# Focused sound library for animation events
SOUND_MANIFEST = {
    "ui_pop": {
        "description": "Soft digital pop for elements appearing",
        "generator": "generate_ui_pop",
    },
    "text_tick": {
        "description": "Light keyboard-like click for text appearing",
        "generator": "generate_text_tick",
    },
    "lock_click": {
        "description": "Crisp mechanical click for things locking into place",
        "generator": "generate_lock_click",
    },
    "data_flow": {
        "description": "Subtle digital stream/whoosh for data movement",
        "generator": "generate_data_flow",
    },
    "counter_sweep": {
        "description": "Rising electronic sweep for fast counters",
        "generator": "generate_counter_sweep",
    },
    "reveal_hit": {
        "description": "Punchy impact for big reveals (87x faster, etc)",
        "generator": "generate_reveal_hit",
    },
    "warning_tone": {
        "description": "Low subtle rumble for problem states",
        "generator": "generate_warning_tone",
    },
    "success_tone": {
        "description": "Positive chime for solutions and success states",
        "generator": "generate_success_tone",
    },
    "transition_whoosh": {
        "description": "Smooth transition sweep between phases",
        "generator": "generate_transition_whoosh",
    },
    "cache_click": {
        "description": "Solid digital click for cache/memory operations",
        "generator": "generate_cache_click",
    },
}


def apply_envelope(
    samples: np.ndarray, attack: float, decay: float, sustain: float, release: float
) -> np.ndarray:
    """Apply ADSR envelope to samples."""
    total = len(samples)
    attack_samples = int(attack * total)
    decay_samples = int(decay * total)
    release_samples = int(release * total)
    sustain_samples = total - attack_samples - decay_samples - release_samples

    envelope = np.zeros(total)

    # Attack
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # Decay
    decay_start = attack_samples
    decay_end = decay_start + decay_samples
    if decay_samples > 0:
        envelope[decay_start:decay_end] = np.linspace(1, sustain, decay_samples)

    # Sustain
    sustain_start = decay_end
    sustain_end = sustain_start + sustain_samples
    if sustain_samples > 0:
        envelope[sustain_start:sustain_end] = sustain

    # Release
    release_start = sustain_end
    if release_samples > 0:
        envelope[release_start:] = np.linspace(sustain, 0, total - release_start)

    return samples * envelope


def normalize(samples: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Normalize samples to target dB level."""
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        target_amp = 10 ** (target_db / 20)
        samples = samples * (target_amp / max_val)
    return samples


def save_wav(samples: np.ndarray, filename: str, sample_rate: int = SAMPLE_RATE) -> None:
    """Save samples as 16-bit WAV file."""
    samples = normalize(samples, -3.0)
    samples_int = np.int16(samples * 32767)

    with wave.open(filename, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples_int.tobytes())


def generate_ui_pop(duration: float = 0.08) -> np.ndarray:
    """Soft digital pop for elements appearing."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    freq_start, freq_end = 1200, 400
    freq = np.linspace(freq_start, freq_end, len(t))
    samples = np.sin(2 * np.pi * freq * t)
    samples = apply_envelope(samples, 0.02, 0.3, 0.0, 0.68)

    # Add subtle click at start
    click = np.zeros_like(t)
    click_len = int(0.003 * SAMPLE_RATE)
    if click_len > 0 and click_len < len(click):
        click[:click_len] = np.sin(np.linspace(0, np.pi, click_len)) * 0.3

    return samples + click


def generate_text_tick(duration: float = 0.04) -> np.ndarray:
    """Light keyboard-like click for text appearing."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    freq = 2500
    samples = np.sin(2 * np.pi * freq * t)
    noise = np.random.uniform(-0.3, 0.3, len(t))

    combined = samples * 0.6 + noise * 0.4
    return apply_envelope(combined, 0.01, 0.2, 0.0, 0.79)


def generate_lock_click(duration: float = 0.1) -> np.ndarray:
    """Crisp mechanical click for things locking into place."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    noise = np.random.uniform(-1, 1, len(t))
    noise = apply_envelope(noise, 0.0, 0.1, 0.0, 0.9)

    freq = 800
    tone = np.sin(2 * np.pi * freq * t)
    tone = apply_envelope(tone, 0.0, 0.3, 0.1, 0.6)

    return noise * 0.5 + tone * 0.5


def generate_data_flow(duration: float = 0.4) -> np.ndarray:
    """Subtle digital stream/whoosh."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    noise = np.random.uniform(-1, 1, len(t))
    freq = np.linspace(200, 1500, len(t))
    modulator = np.sin(2 * np.pi * freq * t / SAMPLE_RATE * 100)

    samples = noise * (0.5 + 0.5 * modulator)
    return apply_envelope(samples, 0.15, 0.2, 0.4, 0.25)


def generate_counter_sweep(duration: float = 0.3) -> np.ndarray:
    """Rising electronic sweep for fast counters."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    freq_start, freq_end = 300, 2000
    freq = np.linspace(freq_start, freq_end, len(t))

    samples = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
    samples += 0.3 * np.sin(4 * np.pi * np.cumsum(freq) / SAMPLE_RATE)

    return apply_envelope(samples, 0.1, 0.3, 0.3, 0.3)


def generate_reveal_hit(duration: float = 0.5) -> np.ndarray:
    """Punchy impact for big reveals."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    # Low frequency impact
    impact_freq = 80
    impact = np.sin(2 * np.pi * impact_freq * t)
    impact = apply_envelope(impact, 0.0, 0.15, 0.0, 0.85)

    # Higher shimmer
    shimmer_freq = np.linspace(1500, 800, len(t))
    shimmer = np.sin(2 * np.pi * np.cumsum(shimmer_freq) / SAMPLE_RATE)
    shimmer = apply_envelope(shimmer, 0.05, 0.2, 0.3, 0.45)

    # Noise transient
    noise = np.random.uniform(-1, 1, len(t))
    noise = apply_envelope(noise, 0.0, 0.05, 0.0, 0.95)

    return impact * 0.5 + shimmer * 0.35 + noise * 0.15


def generate_warning_tone(duration: float = 0.4) -> np.ndarray:
    """Low subtle rumble for problem states."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    freq = 60
    samples = np.sin(2 * np.pi * freq * t)
    samples += 0.5 * np.sin(2 * np.pi * (freq * 0.5) * t)

    mod = 1 + 0.3 * np.sin(2 * np.pi * 4 * t)
    samples = samples * mod

    return apply_envelope(samples, 0.2, 0.2, 0.4, 0.2)


def generate_success_tone(duration: float = 0.3) -> np.ndarray:
    """Positive chime for solutions and success states."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    # Major chord
    freq1, freq2, freq3 = 523, 659, 784  # C5, E5, G5

    note1 = np.sin(2 * np.pi * freq1 * t)
    note2 = np.sin(2 * np.pi * freq2 * t) * (t > 0.02)
    note3 = np.sin(2 * np.pi * freq3 * t) * (t > 0.04)

    samples = (note1 + note2 * 0.8 + note3 * 0.6) / 2.4
    return apply_envelope(samples, 0.02, 0.3, 0.2, 0.48)


def generate_transition_whoosh(duration: float = 0.35) -> np.ndarray:
    """Smooth transition sweep."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    noise = np.random.uniform(-1, 1, len(t))
    center_freq = np.linspace(300, 2000, len(t))
    carrier = np.sin(2 * np.pi * np.cumsum(center_freq) / SAMPLE_RATE)

    samples = noise * 0.3 + carrier * 0.7
    return apply_envelope(samples, 0.2, 0.3, 0.2, 0.3)


def generate_cache_click(duration: float = 0.12) -> np.ndarray:
    """Solid digital click for cache/memory operations."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    freq_start, freq_end = 1000, 500
    freq = np.linspace(freq_start, freq_end, len(t))

    tone = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)

    digital = np.sign(np.sin(2 * np.pi * 3000 * t)) * 0.2
    digital = apply_envelope(digital, 0.0, 0.05, 0.0, 0.95)

    samples = tone + digital
    return apply_envelope(samples, 0.01, 0.2, 0.1, 0.69)


# Generator function mapping
GENERATORS = {
    "generate_ui_pop": generate_ui_pop,
    "generate_text_tick": generate_text_tick,
    "generate_lock_click": generate_lock_click,
    "generate_data_flow": generate_data_flow,
    "generate_counter_sweep": generate_counter_sweep,
    "generate_reveal_hit": generate_reveal_hit,
    "generate_warning_tone": generate_warning_tone,
    "generate_success_tone": generate_success_tone,
    "generate_transition_whoosh": generate_transition_whoosh,
    "generate_cache_click": generate_cache_click,
}


class SoundLibrary:
    """Manages the SFX library for a project."""

    def __init__(self, sfx_dir: Path):
        """Initialize with path to sfx directory."""
        self.sfx_dir = sfx_dir

    def generate_all(self) -> list[str]:
        """Generate all sounds in the library."""
        self.sfx_dir.mkdir(parents=True, exist_ok=True)
        generated = []

        for name, info in SOUND_MANIFEST.items():
            generator_name = info["generator"]
            generator = GENERATORS.get(generator_name)

            if generator:
                samples = generator()
                output_path = self.sfx_dir / f"{name}.wav"
                save_wav(samples, str(output_path))
                generated.append(name)

        return generated

    def list_sounds(self) -> list[str]:
        """List available sounds."""
        return list(SOUND_MANIFEST.keys())

    def get_sound_info(self, name: str) -> dict | None:
        """Get info about a specific sound."""
        return SOUND_MANIFEST.get(name)

    def sound_exists(self, name: str) -> bool:
        """Check if a sound file exists."""
        return (self.sfx_dir / f"{name}.wav").exists()

    def get_missing_sounds(self) -> list[str]:
        """Get list of sounds that haven't been generated yet."""
        return [name for name in SOUND_MANIFEST if not self.sound_exists(name)]
