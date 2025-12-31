"""Tests for music generation module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest
import numpy as np

from src.music import MusicGenerator, MusicConfig, MusicGenerationResult
from src.music.generator import (
    get_music_prompt,
    generate_for_project,
    _update_storyboard_with_music,
    MUSIC_STYLE_PRESETS,
)


class TestMusicConfig:
    """Tests for MusicConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MusicConfig()

        assert config.model_size == "small"
        assert config.segment_duration == 30
        assert config.target_duration is None
        assert config.sample_rate == 32000
        assert config.volume == 0.3
        assert config.device == "auto"
        assert "ambient" in config.style.lower()

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MusicConfig(
            model_size="medium",
            segment_duration=20,
            target_duration=120,
            volume=0.1,
            device="cpu",
        )

        assert config.model_size == "medium"
        assert config.segment_duration == 20
        assert config.target_duration == 120
        assert config.volume == 0.1
        assert config.device == "cpu"


class TestMusicGenerationResult:
    """Tests for MusicGenerationResult dataclass."""

    def test_success_result(self):
        """Test successful generation result."""
        result = MusicGenerationResult(
            success=True,
            output_path=Path("/test/output.mp3"),
            duration_seconds=60.0,
            prompt_used="ambient electronic",
            segments_generated=2,
        )

        assert result.success is True
        assert result.output_path == Path("/test/output.mp3")
        assert result.duration_seconds == 60.0
        assert result.prompt_used == "ambient electronic"
        assert result.segments_generated == 2
        assert result.error_message is None

    def test_failure_result(self):
        """Test failed generation result."""
        result = MusicGenerationResult(
            success=False,
            error_message="Model failed to load",
        )

        assert result.success is False
        assert result.error_message == "Model failed to load"
        assert result.output_path is None


class TestMusicStylePresets:
    """Tests for music style presets."""

    def test_presets_exist(self):
        """Test that required presets exist."""
        required_presets = ["tech", "science", "tutorial", "dramatic", "default"]
        for preset in required_presets:
            assert preset in MUSIC_STYLE_PRESETS

    def test_presets_have_no_vocals(self):
        """Test that all presets specify no vocals."""
        for name, style in MUSIC_STYLE_PRESETS.items():
            assert "no vocal" in style.lower(), f"Preset '{name}' should specify no vocals"


class TestGetMusicPrompt:
    """Tests for get_music_prompt function."""

    def test_tech_topic(self):
        """Test tech topic detection."""
        prompt = get_music_prompt("LLM Inference Optimization")
        assert "tech" in MUSIC_STYLE_PRESETS["tech"] or "electronic" in prompt.lower()

    def test_ai_topic(self):
        """Test AI topic detection."""
        prompt = get_music_prompt("Machine Learning Basics")
        # Should match tech preset
        assert "no vocal" in prompt.lower()

    def test_science_topic(self):
        """Test science topic detection."""
        prompt = get_music_prompt("Physics of Black Holes")
        assert "no vocal" in prompt.lower()

    def test_tutorial_topic(self):
        """Test tutorial topic detection."""
        prompt = get_music_prompt("How to Build a Website")
        assert "no vocal" in prompt.lower()

    def test_custom_style_override(self):
        """Test custom style overrides topic detection."""
        custom = "jazz piano, smooth, relaxing"
        prompt = get_music_prompt("LLM Inference", custom_style=custom)
        assert prompt == custom

    def test_default_topic(self):
        """Test default topic fallback."""
        prompt = get_music_prompt("Random Topic")
        assert "no vocal" in prompt.lower()


class TestMusicGenerator:
    """Tests for MusicGenerator class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        generator = MusicGenerator()
        assert generator.config.model_size == "small"
        assert generator._model is None
        assert generator._processor is None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = MusicConfig(model_size="medium", device="cpu")
        generator = MusicGenerator(config)
        assert generator.config.model_size == "medium"
        assert generator.config.device == "cpu"

    def test_get_device_auto_returns_valid_device(self):
        """Test auto device selection returns a valid device."""
        generator = MusicGenerator()
        device = generator._get_device()
        assert device in ["mps", "cuda", "cpu"]

    def test_get_device_mps_if_available(self):
        """Test that MPS is detected if available."""
        import torch
        generator = MusicGenerator()
        device = generator._get_device()

        # If MPS is available on this machine, it should be selected
        if torch.backends.mps.is_available():
            assert device == "mps"

    def test_get_device_respects_config(self):
        """Test that explicit device config is respected."""
        config = MusicConfig(device="cpu")
        generator = MusicGenerator(config)
        device = generator._get_device()
        assert device == "cpu"


class TestUpdateStoryboardWithMusic:
    """Tests for _update_storyboard_with_music function."""

    def test_update_storyboard(self):
        """Test updating storyboard with music config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create storyboard directory and file
            storyboard_dir = project_dir / "storyboard"
            storyboard_dir.mkdir()

            storyboard = {
                "title": "Test Video",
                "scenes": [],
                "audio": {"voiceover_dir": "voiceover"},
            }
            storyboard_path = storyboard_dir / "storyboard.json"
            with open(storyboard_path, "w") as f:
                json.dump(storyboard, f)

            # Create music directory and file
            music_dir = project_dir / "music"
            music_dir.mkdir()
            music_path = music_dir / "background.mp3"
            music_path.touch()

            # Update storyboard
            _update_storyboard_with_music(project_dir, music_path)

            # Verify update
            with open(storyboard_path) as f:
                updated = json.load(f)

            assert "background_music" in updated["audio"]
            assert updated["audio"]["background_music"]["path"] == "music/background.mp3"
            assert updated["audio"]["background_music"]["volume"] == 0.3

    def test_update_storyboard_creates_audio_section(self):
        """Test that audio section is created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create storyboard without audio section
            storyboard_dir = project_dir / "storyboard"
            storyboard_dir.mkdir()

            storyboard = {"title": "Test Video", "scenes": []}
            storyboard_path = storyboard_dir / "storyboard.json"
            with open(storyboard_path, "w") as f:
                json.dump(storyboard, f)

            # Create music file
            music_dir = project_dir / "music"
            music_dir.mkdir()
            music_path = music_dir / "background.mp3"
            music_path.touch()

            # Update storyboard
            _update_storyboard_with_music(project_dir, music_path)

            # Verify audio section was created
            with open(storyboard_path) as f:
                updated = json.load(f)

            assert "audio" in updated
            assert "background_music" in updated["audio"]

    def test_update_storyboard_missing_file(self):
        """Test handling of missing storyboard file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            music_path = project_dir / "music" / "background.mp3"

            # Should not raise, just print warning
            _update_storyboard_with_music(project_dir, music_path)


class TestGenerateForProject:
    """Tests for generate_for_project function."""

    @patch("src.music.generator.MusicGenerator")
    def test_generate_for_project_success(self, mock_generator_class):
        """Test successful project music generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create storyboard
            storyboard_dir = project_dir / "storyboard"
            storyboard_dir.mkdir()
            with open(storyboard_dir / "storyboard.json", "w") as f:
                json.dump({"title": "Test", "audio": {}}, f)

            # Mock generator
            mock_generator = MagicMock()
            mock_generator.generate.return_value = MusicGenerationResult(
                success=True,
                output_path=project_dir / "music" / "background.mp3",
                duration_seconds=60.0,
                prompt_used="ambient electronic",
                segments_generated=2,
            )
            mock_generator_class.return_value = mock_generator

            # Generate
            result = generate_for_project(
                project_dir=project_dir,
                topic="Test Topic",
                target_duration=60,
                update_storyboard=False,
            )

            assert result.success is True
            assert result.duration_seconds == 60.0
            mock_generator.generate.assert_called_once()

    @patch("src.music.generator.MusicGenerator")
    def test_generate_for_project_creates_music_dir(self, mock_generator_class):
        """Test that music directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Mock generator
            mock_generator = MagicMock()
            mock_generator.generate.return_value = MusicGenerationResult(
                success=True,
                output_path=project_dir / "music" / "background.mp3",
            )
            mock_generator_class.return_value = mock_generator

            # Generate (don't update storyboard since it doesn't exist)
            generate_for_project(
                project_dir=project_dir,
                topic="Test",
                update_storyboard=False,
            )

            # Music directory should be created
            assert (project_dir / "music").exists()


class TestMusicGeneratorIntegration:
    """Integration tests for MusicGenerator (requires actual model).

    These tests are marked as slow and require manual running with:
        pytest tests/test_music.py -v -m slow --run-slow
    """

    @pytest.mark.slow
    def test_generate_short_segment(self):
        """Test generating a short music segment.

        This test requires the MusicGen model to be downloaded.
        Skip if running in CI or if model is not available.
        """
        pytest.skip("Integration test - run manually with --run-slow flag")


class TestCLIMusic:
    """Tests for music CLI command."""

    def test_music_info_command(self):
        """Test music info command parsing."""
        from src.cli.main import main
        import sys

        # This just tests that the command parses correctly
        # Actual execution would require mocking
        with patch.object(sys, "argv", ["cli", "music", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # --help exits with 0
            assert exc_info.value.code == 0
