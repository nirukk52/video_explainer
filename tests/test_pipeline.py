"""Tests for video pipeline orchestrator."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Config
from src.pipeline import VideoPipeline, PipelineResult


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_pipeline_result_success(self, tmp_path):
        """Test successful pipeline result."""
        result = PipelineResult(
            success=True,
            output_path=tmp_path / "video.mp4",
            duration_seconds=120.5,
            stages_completed=["parsing", "analysis", "script", "audio", "animation", "composition"],
        )

        assert result.success
        assert result.output_path == tmp_path / "video.mp4"
        assert len(result.stages_completed) == 6

    def test_pipeline_result_failure(self):
        """Test failed pipeline result."""
        result = PipelineResult(
            success=False,
            output_path=None,
            duration_seconds=0,
            stages_completed=["parsing"],
            error_message="Analysis failed",
        )

        assert not result.success
        assert result.error_message == "Analysis failed"


class TestVideoPipeline:
    """Tests for VideoPipeline class."""

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for FFmpeg calls."""
        with patch("subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                result.stdout = '{"format": {"duration": "10.0"}}'
                result.stderr = ""

                # Create output file if specified
                cmd = args[0] if args else kwargs.get("args", [])
                for i, arg in enumerate(cmd):
                    if isinstance(arg, str) and arg.endswith(".mp4"):
                        Path(arg).parent.mkdir(parents=True, exist_ok=True)
                        Path(arg).write_bytes(b"fake video")
                    elif isinstance(arg, str) and arg.endswith(".mp3"):
                        Path(arg).parent.mkdir(parents=True, exist_ok=True)
                        Path(arg).write_bytes(b"fake audio")

                return result

            mock_run.side_effect = side_effect
            yield mock_run

    @pytest.fixture
    def config(self):
        """Create mock config."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    @pytest.fixture
    def pipeline(self, config, mock_subprocess, tmp_path):
        """Create pipeline with mocked dependencies."""
        return VideoPipeline(config=config, output_dir=tmp_path)

    def test_pipeline_init(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline.config is not None
        assert pipeline.analyzer is not None
        assert pipeline.script_gen is not None
        assert pipeline.renderer is not None
        assert pipeline.tts is not None
        assert pipeline.composer is not None

    def test_set_progress_callback(self, pipeline):
        """Test setting progress callback."""
        progress_updates = []

        def callback(stage, progress):
            progress_updates.append((stage, progress))

        pipeline.set_progress_callback(callback)
        pipeline._report_progress("test", 50)

        assert len(progress_updates) == 1
        assert progress_updates[0] == ("test", 50)

    def test_quick_test(self, pipeline, mock_subprocess):
        """Test quick_test generates output."""
        result = pipeline.quick_test()

        # Should complete at least parsing
        assert "parsing" in result.stages_completed

    def test_combine_audio_files_single(self, pipeline, tmp_path):
        """Test combining a single audio file."""
        audio_file = tmp_path / "audio1.mp3"
        audio_file.write_bytes(b"audio data")

        output_path = tmp_path / "combined.mp3"
        pipeline._combine_audio_files([audio_file], output_path)

        assert output_path.exists()

    def test_combine_audio_files_empty_raises(self, pipeline, tmp_path):
        """Test that empty audio list raises error."""
        with pytest.raises(ValueError, match="No audio files"):
            pipeline._combine_audio_files([], tmp_path / "output.mp3")


class TestPipelineIntegration:
    """Integration tests for pipeline (require FFmpeg)."""

    @pytest.fixture
    def check_ffmpeg(self):
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
            )
            if result.returncode != 0:
                pytest.skip("FFmpeg not available")
        except FileNotFoundError:
            pytest.skip("FFmpeg not available")

    @pytest.fixture
    def config(self):
        """Create mock config."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    def test_full_pipeline_mock(self, check_ffmpeg, config, tmp_path):
        """Test full pipeline with mock data."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        result = pipeline.quick_test()

        assert result.success or "parsing" in result.stages_completed

    def test_pipeline_with_document(self, check_ffmpeg, config, tmp_path):
        """Test pipeline with a real document."""
        # Create test document
        doc_path = tmp_path / "test_doc.md"
        doc_path.write_text("""# Test Document

## Introduction

This is a test document for video generation.

## Main Content

Here we explain the key concepts:
- Concept 1: Something important
- Concept 2: Another thing

## Conclusion

That wraps up our explanation.
""")

        pipeline = VideoPipeline(config=config, output_dir=tmp_path)
        result = pipeline.generate_from_document(
            doc_path,
            target_duration=30,
        )

        assert "parsing" in result.stages_completed
        assert "analysis" in result.stages_completed
