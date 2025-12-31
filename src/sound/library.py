"""Sound library for frame-accurate SFX.

This module generates high-quality sounds designed to sync with specific
animation events in explainer videos.

Sound Design Principles:
- Professional synthesis with harmonic layering
- Exponential envelopes for natural decay
- Filtered noise for texture (not harsh)
- Soft saturation for warmth
- Musical frequency relationships
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


# =============================================================================
# Core Audio Utilities (Professional Quality)
# =============================================================================


def exp_decay(length: int, decay_time: float = 0.5) -> np.ndarray:
    """Create exponential decay envelope (natural sounding)."""
    t = np.linspace(0, 1, length)
    return np.exp(-t * (1 / decay_time) * 5)


def exp_attack_decay(length: int, attack: float = 0.01, decay: float = 0.5) -> np.ndarray:
    """Attack then exponential decay - sounds more natural than linear ADSR."""
    t = np.linspace(0, 1, length)
    attack_samples = int(attack * length)
    env = np.zeros(length)

    # Sharp attack
    if attack_samples > 0:
        env[:attack_samples] = np.linspace(0, 1, attack_samples) ** 0.5  # sqrt for punch

    # Exponential decay
    decay_samples = length - attack_samples
    if decay_samples > 0:
        env[attack_samples:] = np.exp(-np.linspace(0, 5 / decay, decay_samples))

    return env


def soft_clip(samples: np.ndarray, threshold: float = 0.8) -> np.ndarray:
    """Soft clipping for warmth (tanh saturation)."""
    return np.tanh(samples / threshold) * threshold


def bandpass_noise(length: int, low_freq: float, high_freq: float) -> np.ndarray:
    """Generate bandpass filtered noise using FFT."""
    noise = np.random.randn(length)

    # FFT filtering
    fft = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(length, 1 / SAMPLE_RATE)

    # Create bandpass mask with smooth rolloff
    mask = np.zeros_like(freqs)
    in_band = (freqs >= low_freq) & (freqs <= high_freq)
    mask[in_band] = 1.0

    # Smooth the edges
    rolloff_width = (high_freq - low_freq) * 0.1
    for i, f in enumerate(freqs):
        if low_freq - rolloff_width < f < low_freq:
            mask[i] = (f - (low_freq - rolloff_width)) / rolloff_width
        elif high_freq < f < high_freq + rolloff_width:
            mask[i] = 1 - (f - high_freq) / rolloff_width

    filtered = np.fft.irfft(fft * mask, length)
    return filtered / (np.max(np.abs(filtered)) + 1e-10)


def lowpass_noise(length: int, cutoff: float) -> np.ndarray:
    """Generate lowpass filtered noise."""
    return bandpass_noise(length, 20, cutoff)


def highpass_noise(length: int, cutoff: float) -> np.ndarray:
    """Generate highpass filtered noise."""
    return bandpass_noise(length, cutoff, SAMPLE_RATE // 2 - 100)


def harmonic_tone(t: np.ndarray, freq: float, harmonics: list[tuple[int, float]]) -> np.ndarray:
    """Generate tone with specified harmonics. harmonics = [(multiplier, amplitude), ...]"""
    tone = np.sin(2 * np.pi * freq * t)
    for mult, amp in harmonics:
        tone += amp * np.sin(2 * np.pi * freq * mult * t)
    return tone / (1 + sum(amp for _, amp in harmonics))


def pitch_sweep(t: np.ndarray, start_freq: float, end_freq: float, curve: str = "log") -> np.ndarray:
    """Generate frequency sweep with log or linear curve."""
    if curve == "log":
        freq = start_freq * (end_freq / start_freq) ** (t / t[-1])
    else:
        freq = np.linspace(start_freq, end_freq, len(t))

    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    return np.sin(phase)


def apply_envelope(
    samples: np.ndarray, attack: float, decay: float, sustain: float, release: float
) -> np.ndarray:
    """Apply ADSR envelope to samples (kept for backwards compatibility)."""
    total = len(samples)
    attack_samples = int(attack * total)
    decay_samples = int(decay * total)
    release_samples = int(release * total)
    sustain_samples = total - attack_samples - decay_samples - release_samples

    envelope = np.zeros(total)

    # Attack (use sqrt curve for punch)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples) ** 0.5

    # Decay (exponential)
    decay_start = attack_samples
    decay_end = decay_start + decay_samples
    if decay_samples > 0:
        envelope[decay_start:decay_end] = 1 - (1 - sustain) * (
            1 - np.exp(-np.linspace(0, 4, decay_samples))
        ) / (1 - np.exp(-4))

    # Sustain
    sustain_start = decay_end
    sustain_end = sustain_start + sustain_samples
    if sustain_samples > 0:
        envelope[sustain_start:sustain_end] = sustain

    # Release (exponential)
    release_start = sustain_end
    if release_samples > 0:
        release_len = total - release_start
        envelope[release_start:] = sustain * np.exp(-np.linspace(0, 5, release_len))

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


# =============================================================================
# Sound Generators (Punchy, High-Impact)
# =============================================================================


def sharp_transient(length: int, intensity: float = 1.0) -> np.ndarray:
    """Create a sharp attack transient - the 'snap' that makes sounds punchy.

    Uses a burst of full-spectrum noise with instant attack and ultra-fast decay.
    """
    # Ultra-short noise burst (1-3ms)
    burst_samples = min(int(0.002 * SAMPLE_RATE), length)

    transient = np.zeros(length)
    if burst_samples > 0:
        # White noise burst
        burst = np.random.randn(burst_samples)
        # Instant attack, exponential decay
        burst_env = np.exp(-np.linspace(0, 8, burst_samples))
        transient[:burst_samples] = burst * burst_env * intensity

    return transient


def hard_clip(samples: np.ndarray, threshold: float = 0.7) -> np.ndarray:
    """Hard clipping for aggressive transients."""
    return np.clip(samples, -threshold, threshold)


def generate_ui_pop(duration: float = 0.1) -> np.ndarray:
    """Punchy digital pop - snappy with immediate impact.

    Sharp transient + descending tone + sub thump.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # SHARP TRANSIENT - the snap
    snap = sharp_transient(n_samples, 1.2)
    snap = hard_clip(snap, 0.8)

    # Punchy descending tone - fast pitch drop
    freq = 1200 * np.exp(-t * 25)  # Very fast exponential drop
    body = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
    body += 0.4 * np.sin(4 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
    body *= np.exp(-t * 30)  # Fast decay

    # Sub thump for weight
    sub = np.sin(2 * np.pi * 80 * t)
    sub *= np.exp(-t * 20)
    sub *= 0.5

    samples = snap * 0.7 + body * 0.8 + sub
    return hard_clip(samples, 0.85)


def generate_text_tick(duration: float = 0.035) -> np.ndarray:
    """Sharp keyboard click - crisp and immediate.

    Pure transient with minimal tail.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # SHARP CLICK - instant attack
    click = sharp_transient(n_samples, 1.5)

    # High-frequency ping - very short
    ping_freq = 4500
    ping = np.sin(2 * np.pi * ping_freq * t)
    ping += 0.6 * np.sin(2 * np.pi * ping_freq * 1.4 * t)  # Inharmonic
    ping *= np.exp(-t * 80)  # Ultra-fast decay

    # Mid body - subtle
    body = np.sin(2 * np.pi * 1800 * t)
    body *= np.exp(-t * 50)
    body *= 0.3

    samples = click + ping * 0.8 + body
    return hard_clip(samples, 0.9)


def generate_lock_click(duration: float = 0.12) -> np.ndarray:
    """Mechanical snap - satisfying latch with sharp attack.

    Hard transient + metallic ring + low thunk.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # HARD SNAP - the mechanical impact
    snap = sharp_transient(n_samples, 1.8)
    snap = hard_clip(snap, 0.7)

    # Metallic ping - detuned for realism
    freq1, freq2 = 2200, 2250
    metal = np.sin(2 * np.pi * freq1 * t) + np.sin(2 * np.pi * freq2 * t)
    metal += 0.4 * np.sin(2 * np.pi * freq1 * 2.7 * t)  # Inharmonic overtone
    metal *= np.exp(-t * 25)
    metal *= 0.5

    # Low thunk - the body
    thunk = np.sin(2 * np.pi * 150 * t)
    thunk *= np.exp(-t * 30)
    thunk *= 0.6

    samples = snap + metal + thunk
    return hard_clip(samples, 0.85)


def generate_data_flow(duration: float = 0.4) -> np.ndarray:
    """Digital data stream - punchy attack, flowing body.

    Sharp start + swept texture + rhythmic pulses.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # PUNCHY START
    attack = sharp_transient(n_samples, 1.0)

    # Swept filtered noise
    noise = bandpass_noise(n_samples, 400, 2000)

    # Add rhythmic pulses for "data packet" feel
    pulse_freq = 15  # 15 Hz pulses
    pulses = 0.5 + 0.5 * np.sin(2 * np.pi * pulse_freq * t)
    noise *= pulses

    # Envelope - punchy attack, sustain, fade
    env = np.ones(n_samples)
    attack_len = int(0.02 * SAMPLE_RATE)
    env[:attack_len] = np.linspace(0, 1, attack_len) ** 0.3  # Fast attack
    fade_start = int(0.7 * n_samples)
    env[fade_start:] = np.exp(-np.linspace(0, 4, n_samples - fade_start))

    noise *= env * 0.6

    # Digital texture
    digital = np.sin(2 * np.pi * 800 * t + 2 * np.sin(2 * np.pi * 50 * t))
    digital *= env * 0.25

    samples = attack * 0.5 + noise + digital
    return soft_clip(samples, 0.85)


def generate_counter_sweep(duration: float = 0.3) -> np.ndarray:
    """Rising sweep with punch - energetic, driving.

    Sharp attack + accelerating sweep + bright finish.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # PUNCHY START
    attack = sharp_transient(n_samples, 1.2)

    # Accelerating sweep - exponential feels more energetic
    start_freq, end_freq = 150, 3000
    sweep = pitch_sweep(t, start_freq, end_freq, "log")
    sweep2 = pitch_sweep(t, start_freq * 2, end_freq * 2, "log") * 0.4

    # Envelope with punch
    env = np.ones(n_samples)
    env *= np.exp(-t * 2)  # Gradual fade
    env[:int(0.02 * n_samples)] = np.linspace(0, 1, int(0.02 * n_samples)) ** 0.3

    tone = (sweep + sweep2) * env

    # Bright finish - noise burst at end
    end_burst = highpass_noise(n_samples, 3000)
    end_env = np.linspace(0, 1, n_samples) ** 3
    end_burst *= end_env * np.exp(-np.linspace(0, 2, n_samples)[::-1]) * 0.3

    samples = attack * 0.6 + tone + end_burst
    return hard_clip(samples, 0.9)


def generate_reveal_hit(duration: float = 0.5) -> np.ndarray:
    """Cinematic impact - hard-hitting reveal moment.

    Massive transient + sub drop + shimmer tail.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # MASSIVE TRANSIENT - the hit
    hit = sharp_transient(n_samples, 2.5)
    hit = hard_clip(hit, 0.6)

    # Additional mid-freq punch
    punch = bandpass_noise(n_samples, 800, 2500)
    punch *= np.exp(-t * 40)
    punch *= 0.8

    # Sub drop - pitch falling
    sub_freq = 80 + 60 * np.exp(-t * 20)
    sub = np.sin(2 * np.pi * np.cumsum(sub_freq) / SAMPLE_RATE)
    sub *= np.exp(-t * 8)
    sub *= 0.9

    # Mid body
    mid = harmonic_tone(t, 120, [(2, 0.5), (3, 0.25)])
    mid *= np.exp(-t * 12)
    mid *= 0.5

    # Shimmer tail
    shimmer_freq = 1500 * np.exp(-t * 3)
    shimmer = np.sin(2 * np.pi * np.cumsum(shimmer_freq) / SAMPLE_RATE)
    shimmer *= np.exp(-t * 5)
    shimmer *= 0.25

    samples = hit + punch + sub + mid + shimmer
    return hard_clip(samples, 0.75)


def generate_warning_tone(duration: float = 0.4) -> np.ndarray:
    """Urgent warning - punchy, attention-grabbing.

    Sharp attack + low growl + tremolo.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # PUNCHY START
    attack = sharp_transient(n_samples, 1.3)

    # Low growl with harmonics
    freq = 65
    tone = harmonic_tone(t, freq, [(2, 0.7), (3, 0.4), (4, 0.2), (5, 0.1)])

    # Fast tremolo for urgency
    tremolo = 0.6 + 0.4 * np.sin(2 * np.pi * 8 * t)
    tone *= tremolo

    # Sub bass
    sub = np.sin(2 * np.pi * 32 * t)
    sub *= 0.5

    # Envelope
    env = np.exp(-t * 4)
    env[:int(0.01 * n_samples)] = np.linspace(0, 1, int(0.01 * n_samples)) ** 0.3

    samples = attack * 0.5 + (tone + sub) * env
    return hard_clip(samples, 0.8)


def generate_success_tone(duration: float = 0.35) -> np.ndarray:
    """Bright success chime - punchy and uplifting.

    Sharp attack + quick arpeggio + sparkle.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # PUNCHY START
    attack = sharp_transient(n_samples, 1.0)

    # Major chord - quick staggered entry
    freqs = [523.25, 659.25, 783.99]  # C5, E5, G5
    delays = [0, 0.015, 0.03]  # Faster arpeggio

    chord = np.zeros(n_samples)
    for freq, delay in zip(freqs, delays):
        delay_samples = int(delay * SAMPLE_RATE)
        note_len = n_samples - delay_samples

        if note_len > 0:
            note_t = np.linspace(0, note_len / SAMPLE_RATE, note_len)
            # Bell harmonics
            note = np.sin(2 * np.pi * freq * note_t)
            note += 0.35 * np.sin(2 * np.pi * freq * 2.0 * note_t)
            note += 0.15 * np.sin(2 * np.pi * freq * 3.0 * note_t)
            note *= np.exp(-note_t * 8)  # Faster decay
            chord[delay_samples:] += note * 0.45

    # High sparkle
    sparkle = highpass_noise(n_samples, 4000)
    sparkle *= np.exp(-t * 15)
    sparkle *= 0.2

    samples = attack * 0.4 + chord + sparkle
    return hard_clip(samples, 0.9)


def generate_transition_whoosh(duration: float = 0.35) -> np.ndarray:
    """Punchy whoosh - sharp attack, smooth sweep.

    Hard transient + swept noise + doppler tone.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # PUNCHY START
    attack = sharp_transient(n_samples, 1.4)

    # Swept noise - fewer bands, more punch
    whoosh = np.zeros(n_samples)
    n_bands = 15
    for i in range(n_bands):
        band_center = i / n_bands
        band_env = np.exp(-((t / duration - band_center) ** 2) / 0.02)
        freq_center = 400 + i * 200
        band = bandpass_noise(n_samples, freq_center * 0.7, freq_center * 1.3)
        whoosh += band * band_env

    whoosh *= 0.6

    # Doppler tone
    doppler_freq = 300 + 1000 * np.sin(np.pi * t / duration)
    doppler = np.sin(2 * np.pi * np.cumsum(doppler_freq) / SAMPLE_RATE)
    doppler *= np.sin(np.pi * t / duration)
    doppler *= 0.3

    # Envelope - punchy start
    env = np.sin(np.pi * t / duration) ** 0.4
    env[:int(0.05 * n_samples)] = np.linspace(0, env[int(0.05 * n_samples)], int(0.05 * n_samples)) ** 0.3

    samples = attack * 0.5 + (whoosh + doppler) * env
    return soft_clip(samples, 0.85)


def generate_cache_click(duration: float = 0.1) -> np.ndarray:
    """Digital cache click - sharp, electronic, precise.

    Hard transient + digital blip + resonant body.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples)

    # HARD CLICK
    click = sharp_transient(n_samples, 1.6)
    click = hard_clip(click, 0.75)

    # Digital blip - fast pitch drop
    blip_freq = 2000 * np.exp(-t * 40)
    blip = np.sin(2 * np.pi * np.cumsum(blip_freq) / SAMPLE_RATE)
    blip *= np.exp(-t * 35)
    blip *= 0.7

    # Resonant mid
    mid = np.sin(2 * np.pi * 900 * t)
    mid += 0.4 * np.sin(2 * np.pi * 1800 * t)
    mid *= np.exp(-t * 25)
    mid *= 0.4

    # Sub click
    sub = np.sin(2 * np.pi * 120 * t)
    sub *= np.exp(-t * 30)
    sub *= 0.35

    samples = click + blip + mid + sub
    return hard_clip(samples, 0.85)


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
