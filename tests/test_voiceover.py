"""Tests for voiceover generation module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.voiceover.narration import (
    SceneNarration,
    load_narrations_from_file,
    load_narrations_from_project,
)
from src.voiceover.generator import (
    SceneVoiceover,
    VoiceoverResult,
    VoiceoverGenerator,
)
from src.audio import WordTimestamp
from src.config import TTSConfig


class TestNarration:
    """Tests for narration loading module."""

    @pytest.fixture
    def sample_narrations_file(self, tmp_path):
        """Create a sample narrations JSON file."""
        narrations_data = {
            "scenes": [
                {
                    "scene_id": "scene1",
                    "title": "Introduction",
                    "duration_seconds": 15,
                    "narration": "Welcome to this video.",
                },
                {
                    "scene_id": "scene2",
                    "title": "Main Content",
                    "duration_seconds": 30,
                    "narration": "Here is the main content.",
                },
                {
                    "scene_id": "scene3",
                    "title": "Conclusion",
                    "duration_seconds": 10,
                    "narration": "Thank you for watching.",
                },
            ],
            "total_duration_seconds": 55,
        }
        narration_path = tmp_path / "narrations.json"
        with open(narration_path, "w") as f:
            json.dump(narrations_data, f)
        return narration_path

    def test_load_narrations_from_file(self, sample_narrations_file):
        """Test loading narrations from a JSON file."""
        narrations = load_narrations_from_file(sample_narrations_file)

        assert len(narrations) == 3
        assert narrations[0].scene_id == "scene1"
        assert narrations[0].title == "Introduction"
        assert narrations[1].duration_seconds == 30

    def test_load_narrations_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_narrations_from_file(tmp_path / "nonexistent.json")

    def test_load_narrations_from_project(self, tmp_path):
        """Test loading narrations from a project directory."""
        # Create project structure
        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()

        narrations_data = {
            "scenes": [
                {
                    "scene_id": "test",
                    "title": "Test",
                    "duration_seconds": 10,
                    "narration": "Test narration.",
                },
            ],
        }
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump(narrations_data, f)

        narrations = load_narrations_from_project(tmp_path)
        assert len(narrations) == 1
        assert narrations[0].scene_id == "test"

    def test_scene_narration_fields(self, sample_narrations_file):
        """Verify SceneNarration has all required fields."""
        narrations = load_narrations_from_file(sample_narrations_file)

        for narration in narrations:
            assert narration.scene_id, "scene_id should not be empty"
            assert narration.title, "title should not be empty"
            assert narration.duration_seconds > 0, "duration should be positive"
            assert narration.narration, "narration text should not be empty"


class TestSceneVoiceover:
    """Tests for SceneVoiceover data class."""

    def test_to_dict(self, tmp_path):
        """Test converting SceneVoiceover to dict."""
        audio_path = tmp_path / "test.mp3"
        audio_path.touch()

        voiceover = SceneVoiceover(
            scene_id="test_scene",
            audio_path=audio_path,
            duration_seconds=10.5,
            word_timestamps=[
                WordTimestamp(word="hello", start_seconds=0.0, end_seconds=0.5),
                WordTimestamp(word="world", start_seconds=0.6, end_seconds=1.0),
            ],
        )

        data = voiceover.to_dict()
        assert data["scene_id"] == "test_scene"
        assert data["duration_seconds"] == 10.5
        assert len(data["word_timestamps"]) == 2
        assert data["word_timestamps"][0]["word"] == "hello"


class TestVoiceoverResult:
    """Tests for VoiceoverResult data class."""

    @pytest.fixture
    def sample_result(self, tmp_path):
        """Create a sample VoiceoverResult."""
        audio_path = tmp_path / "test.mp3"
        audio_path.touch()

        return VoiceoverResult(
            scenes=[
                SceneVoiceover(
                    scene_id="scene1",
                    audio_path=audio_path,
                    duration_seconds=10.0,
                    word_timestamps=[],
                ),
                SceneVoiceover(
                    scene_id="scene2",
                    audio_path=audio_path,
                    duration_seconds=15.0,
                    word_timestamps=[],
                ),
            ],
            total_duration_seconds=25.0,
            output_dir=tmp_path,
        )

    def test_to_dict(self, sample_result):
        """Test converting VoiceoverResult to dict."""
        data = sample_result.to_dict()
        assert len(data["scenes"]) == 2
        assert data["total_duration_seconds"] == 25.0
        assert "output_dir" in data

    def test_save_manifest(self, sample_result, tmp_path):
        """Test saving manifest to file."""
        manifest_path = sample_result.save_manifest()
        assert manifest_path.exists()
        assert manifest_path.name == "voiceover_manifest.json"

        # Verify content
        with open(manifest_path) as f:
            data = json.load(f)
        assert len(data["scenes"]) == 2

    def test_load_manifest(self, sample_result, tmp_path):
        """Test loading manifest from file."""
        manifest_path = sample_result.save_manifest()

        loaded = VoiceoverResult.load_manifest(manifest_path)
        assert len(loaded.scenes) == 2
        assert loaded.total_duration_seconds == 25.0
        assert loaded.scenes[0].scene_id == "scene1"


class TestVoiceoverGenerator:
    """Tests for VoiceoverGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a VoiceoverGenerator."""
        return VoiceoverGenerator(voice="en-US-GuyNeural")

    def test_init_with_default_voice(self):
        """Test initialization with default voice."""
        gen = VoiceoverGenerator()
        assert gen.voice == "en-US-GuyNeural"

    def test_init_with_custom_voice(self):
        """Test initialization with custom voice."""
        gen = VoiceoverGenerator(voice="en-US-AriaNeural")
        assert gen.voice == "en-US-AriaNeural"

    def test_generate_scene_voiceover(self, generator, tmp_path):
        """Test generating voiceover for a single scene."""
        narration = SceneNarration(
            scene_id="test",
            title="Test",
            duration_seconds=5,
            narration="This is a short test.",
        )

        async def mock_stream():
            yield {"type": "WordBoundary", "text": "This", "offset": 0, "duration": 3_000_000}
            yield {"type": "WordBoundary", "text": "is", "offset": 4_000_000, "duration": 2_000_000}
            yield {"type": "WordBoundary", "text": "a", "offset": 7_000_000, "duration": 1_000_000}
            yield {"type": "WordBoundary", "text": "short", "offset": 9_000_000, "duration": 4_000_000}
            yield {"type": "WordBoundary", "text": "test", "offset": 14_000_000, "duration": 4_000_000}
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" + b"\x00" * 100}

        mock_communicate = MagicMock()
        mock_communicate.stream = mock_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = generator.generate_scene_voiceover(narration, tmp_path)

        assert result.scene_id == "test"
        assert result.audio_path.exists()
        assert result.duration_seconds > 0
        assert len(result.word_timestamps) > 0

    def test_generate_all_voiceovers(self, generator, tmp_path):
        """Test generating all voiceovers."""
        # Use short test narrations
        test_narrations = [
            SceneNarration(
                scene_id="test1",
                title="Test 1",
                duration_seconds=5,
                narration="First test.",
            ),
            SceneNarration(
                scene_id="test2",
                title="Test 2",
                duration_seconds=5,
                narration="Second test.",
            ),
        ]

        async def mock_stream():
            yield {"type": "WordBoundary", "text": "Test", "offset": 0, "duration": 5_000_000}
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" + b"\x00" * 100}

        mock_communicate = MagicMock()
        mock_communicate.stream = mock_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = generator.generate_all_voiceovers(tmp_path, narrations=test_narrations)

        assert len(result.scenes) == 2
        assert result.total_duration_seconds > 0
        assert (tmp_path / "voiceover_manifest.json").exists()


class TestLLMInferenceProjectVoiceover:
    """Integration tests for LLM inference project voiceover files."""

    def test_project_narrations_exist(self):
        """Verify narrations file exists in project."""
        narration_path = Path("projects/llm-inference/narration/narrations.json")
        if not narration_path.exists():
            pytest.skip("LLM inference project not found")

        narrations = load_narrations_from_file(narration_path)
        assert len(narrations) == 18

    def test_project_voiceover_files_exist(self):
        """Verify voiceover files exist in project."""
        voiceover_dir = Path("projects/llm-inference/voiceover")
        if not voiceover_dir.exists():
            pytest.skip("LLM inference voiceover directory not found")

        mp3_files = list(voiceover_dir.glob("*.mp3"))
        assert len(mp3_files) == 18, f"Expected 18 mp3 files, got {len(mp3_files)}"

    def test_project_manifest_exists(self):
        """Verify manifest file exists in project."""
        manifest_path = Path("projects/llm-inference/voiceover/manifest.json")
        if not manifest_path.exists():
            pytest.skip("LLM inference manifest not found")

        with open(manifest_path) as f:
            data = json.load(f)
        assert len(data["scenes"]) == 18
        assert data["total_duration_seconds"] > 0
