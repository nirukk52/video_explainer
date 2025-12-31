"""Tests for the sound design module."""

import tempfile
from pathlib import Path

import pytest


class TestSoundLibrary:
    """Tests for the SoundLibrary class."""

    def test_sound_manifest_has_10_sounds(self):
        """Test that SOUND_MANIFEST has exactly 10 sounds."""
        from src.sound.library import SOUND_MANIFEST

        assert len(SOUND_MANIFEST) == 10

    def test_sound_manifest_has_required_sounds(self):
        """Test that all required sounds are in the manifest."""
        from src.sound.library import SOUND_MANIFEST

        required_sounds = [
            "ui_pop",
            "text_tick",
            "lock_click",
            "data_flow",
            "counter_sweep",
            "reveal_hit",
            "warning_tone",
            "success_tone",
            "transition_whoosh",
            "cache_click",
        ]

        for sound in required_sounds:
            assert sound in SOUND_MANIFEST
            assert "description" in SOUND_MANIFEST[sound]
            assert "generator" in SOUND_MANIFEST[sound]

    def test_library_list_sounds(self):
        """Test listing available sounds."""
        from src.sound.library import SoundLibrary

        with tempfile.TemporaryDirectory() as tmpdir:
            library = SoundLibrary(Path(tmpdir))
            sounds = library.list_sounds()

            assert len(sounds) == 10
            assert "ui_pop" in sounds
            assert "reveal_hit" in sounds

    def test_library_generate_all(self):
        """Test generating all sounds."""
        from src.sound.library import SoundLibrary

        with tempfile.TemporaryDirectory() as tmpdir:
            sfx_dir = Path(tmpdir)
            library = SoundLibrary(sfx_dir)

            generated = library.generate_all()

            assert len(generated) == 10

            # Check files were created
            for name in generated:
                assert (sfx_dir / f"{name}.wav").exists()

    def test_library_sound_exists(self):
        """Test checking if a sound file exists."""
        from src.sound.library import SoundLibrary

        with tempfile.TemporaryDirectory() as tmpdir:
            sfx_dir = Path(tmpdir)
            library = SoundLibrary(sfx_dir)

            # Initially no sounds exist
            assert not library.sound_exists("ui_pop")

            # Generate sounds
            library.generate_all()

            # Now sounds should exist
            assert library.sound_exists("ui_pop")
            assert library.sound_exists("reveal_hit")

    def test_library_get_missing_sounds(self):
        """Test getting list of missing sounds."""
        from src.sound.library import SoundLibrary

        with tempfile.TemporaryDirectory() as tmpdir:
            sfx_dir = Path(tmpdir)
            library = SoundLibrary(sfx_dir)

            # Initially all sounds are missing
            missing = library.get_missing_sounds()
            assert len(missing) == 10

            # Generate sounds
            library.generate_all()

            # Now no sounds should be missing
            missing = library.get_missing_sounds()
            assert len(missing) == 0

    def test_library_get_sound_info(self):
        """Test getting info about a specific sound."""
        from src.sound.library import SoundLibrary

        with tempfile.TemporaryDirectory() as tmpdir:
            library = SoundLibrary(Path(tmpdir))

            info = library.get_sound_info("ui_pop")
            assert info is not None
            assert "description" in info
            assert "generator" in info

            # Unknown sound returns None
            info = library.get_sound_info("nonexistent")
            assert info is None


class TestSoundGenerators:
    """Tests for individual sound generator functions."""

    def test_generate_ui_pop(self):
        """Test ui_pop generator."""
        from src.sound.library import generate_ui_pop

        samples = generate_ui_pop()
        assert len(samples) > 0
        # Note: samples are normalized when saved, not when generated

    def test_generate_text_tick(self):
        """Test text_tick generator."""
        from src.sound.library import generate_text_tick

        samples = generate_text_tick()
        assert len(samples) > 0

    def test_generate_lock_click(self):
        """Test lock_click generator."""
        from src.sound.library import generate_lock_click

        samples = generate_lock_click()
        assert len(samples) > 0

    def test_generate_data_flow(self):
        """Test data_flow generator."""
        from src.sound.library import generate_data_flow

        samples = generate_data_flow()
        assert len(samples) > 0

    def test_generate_counter_sweep(self):
        """Test counter_sweep generator."""
        from src.sound.library import generate_counter_sweep

        samples = generate_counter_sweep()
        assert len(samples) > 0

    def test_generate_reveal_hit(self):
        """Test reveal_hit generator."""
        from src.sound.library import generate_reveal_hit

        samples = generate_reveal_hit()
        assert len(samples) > 0

    def test_generate_warning_tone(self):
        """Test warning_tone generator."""
        from src.sound.library import generate_warning_tone

        samples = generate_warning_tone()
        assert len(samples) > 0

    def test_generate_success_tone(self):
        """Test success_tone generator."""
        from src.sound.library import generate_success_tone

        samples = generate_success_tone()
        assert len(samples) > 0

    def test_generate_transition_whoosh(self):
        """Test transition_whoosh generator."""
        from src.sound.library import generate_transition_whoosh

        samples = generate_transition_whoosh()
        assert len(samples) > 0

    def test_generate_cache_click(self):
        """Test cache_click generator."""
        from src.sound.library import generate_cache_click

        samples = generate_cache_click()
        assert len(samples) > 0


class TestAudioUtilities:
    """Tests for audio utility functions."""

    def test_apply_envelope(self):
        """Test ADSR envelope application."""
        import numpy as np
        from src.sound.library import apply_envelope

        # Create a simple sine wave
        samples = np.sin(np.linspace(0, 4 * np.pi, 1000))

        # Apply envelope
        result = apply_envelope(samples, 0.1, 0.2, 0.5, 0.2)

        assert len(result) == len(samples)
        # Envelope should start at 0
        assert abs(result[0]) < 0.01

    def test_normalize(self):
        """Test normalization function."""
        import numpy as np
        from src.sound.library import normalize

        samples = np.array([0.1, 0.5, -0.3, 0.2])
        result = normalize(samples, -3.0)

        # Max should be close to target dB
        max_val = np.max(np.abs(result))
        target = 10 ** (-3.0 / 20)
        assert abs(max_val - target) < 0.01

    def test_save_wav(self):
        """Test WAV file saving."""
        import numpy as np
        import wave
        from src.sound.library import save_wav

        with tempfile.TemporaryDirectory() as tmpdir:
            samples = np.sin(np.linspace(0, 4 * np.pi, 44100))
            output_path = Path(tmpdir) / "test.wav"

            save_wav(samples, str(output_path))

            assert output_path.exists()

            # Verify WAV file properties
            with wave.open(str(output_path), "r") as wav:
                assert wav.getnchannels() == 1
                assert wav.getsampwidth() == 2
                assert wav.getframerate() == 44100


class TestCLIIntegration:
    """Tests for CLI sound command integration."""

    def test_cli_sound_parser_exists(self):
        """Test that the sound CLI command exists."""
        from src.cli.main import cmd_sound

        assert callable(cmd_sound)
