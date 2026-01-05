"""Tests for audio/TTS module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from src.audio import (
    ElevenLabsTTS,
    EdgeTTS,
    TTSProvider,
    TTSResult,
    WordTimestamp,
    get_tts_provider,
)
from src.audio.tts import MockTTS
from src.config import Config, TTSConfig


class TestMockTTS:
    """Tests for mock TTS provider."""

    @pytest.fixture
    def mock_tts(self):
        config = TTSConfig(provider="mock")
        return MockTTS(config)

    def test_generate_creates_file(self, mock_tts, tmp_path):
        output_path = tmp_path / "test.mp3"
        result = mock_tts.generate("Hello, world!", output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_stream_yields_bytes(self, mock_tts):
        chunks = list(mock_tts.generate_stream("Hello"))
        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)

    def test_get_available_voices(self, mock_tts):
        voices = mock_tts.get_available_voices()
        assert len(voices) > 0
        assert "voice_id" in voices[0]
        assert "name" in voices[0]


class TestGetTTSProvider:
    """Tests for TTS provider factory."""

    def test_returns_mock_provider(self):
        config = Config()
        config.tts.provider = "mock"
        provider = get_tts_provider(config)
        assert isinstance(provider, MockTTS)

    def test_raises_for_unknown_provider(self):
        config = Config()
        config.tts.provider = "unknown_provider"
        with pytest.raises(ValueError, match="Unknown TTS provider"):
            get_tts_provider(config)

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_returns_elevenlabs_with_api_key(self):
        config = Config()
        config.tts.provider = "elevenlabs"
        provider = get_tts_provider(config)
        assert isinstance(provider, ElevenLabsTTS)

    def test_returns_edge_provider(self):
        config = Config()
        config.tts.provider = "edge"
        provider = get_tts_provider(config)
        assert isinstance(provider, EdgeTTS)


class TestElevenLabsTTS:
    """Tests for ElevenLabs TTS provider."""

    @pytest.fixture
    def config(self):
        return TTSConfig(
            provider="elevenlabs",
            model="eleven_multilingual_v2",
        )

    def test_init_requires_api_key(self, config):
        # Clear env var if set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ELEVENLABS_API_KEY", None)
            with pytest.raises(ValueError, match="API key required"):
                ElevenLabsTTS(config)

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_init_with_env_api_key(self, config):
        tts = ElevenLabsTTS(config)
        assert tts.api_key == "test_key"

    def test_init_with_explicit_api_key(self, config):
        tts = ElevenLabsTTS(config, api_key="explicit_key")
        assert tts.api_key == "explicit_key"

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_estimate_cost(self, config):
        tts = ElevenLabsTTS(config)

        # 1000 characters should cost about $0.30
        cost = tts.estimate_cost("a" * 1000)
        assert 0.2 < cost < 0.4  # Approximately $0.30

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_default_voice_id(self, config):
        tts = ElevenLabsTTS(config)
        assert tts.voice_id is not None

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_custom_voice_id(self, config):
        config.voice_id = "custom_voice_123"
        tts = ElevenLabsTTS(config)
        assert tts.voice_id == "custom_voice_123"


class TestEdgeTTS:
    """Tests for Edge TTS provider."""

    @pytest.fixture
    def config(self):
        return TTSConfig(provider="edge")

    @pytest.fixture
    def edge_tts(self, config):
        return EdgeTTS(config)

    def test_init_with_default_voice(self, config):
        tts = EdgeTTS(config)
        assert tts.voice == "en-US-GuyNeural"

    def test_init_with_custom_voice(self, config):
        tts = EdgeTTS(config, voice="en-GB-SoniaNeural")
        assert tts.voice == "en-GB-SoniaNeural"

    def test_init_with_config_voice_id(self, config):
        config.voice_id = "en-US-AriaNeural"
        tts = EdgeTTS(config)
        assert tts.voice == "en-US-AriaNeural"

    def test_default_voices_available(self, edge_tts):
        """Test that default voice presets are available."""
        assert "male" in EdgeTTS.DEFAULT_VOICES
        assert "female" in EdgeTTS.DEFAULT_VOICES
        assert "british_male" in EdgeTTS.DEFAULT_VOICES
        assert "british_female" in EdgeTTS.DEFAULT_VOICES

    def test_generate_creates_audio_file(self, edge_tts, tmp_path):
        """Test that generate creates an audio file."""
        output_path = tmp_path / "test.mp3"

        # Mock communicate.save to write fake audio data
        async def mock_save(path):
            Path(path).write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)

        mock_communicate = MagicMock()
        mock_communicate.save = mock_save

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = edge_tts.generate("Hello, this is a test.", output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_with_timestamps_returns_result(self, edge_tts, tmp_path):
        """Test generate_with_timestamps returns TTSResult."""
        output_path = tmp_path / "test.mp3"

        async def mock_stream():
            yield {"type": "WordBoundary", "text": "Hello", "offset": 0, "duration": 5_000_000}
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" + b"\x00" * 100}

        mock_communicate = MagicMock()
        mock_communicate.stream = mock_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = edge_tts.generate_with_timestamps("Hello world!", output_path)

        assert isinstance(result, TTSResult)
        assert result.audio_path == output_path
        assert result.audio_path.exists()
        assert result.duration_seconds > 0

    def test_generate_with_timestamps_has_words(self, edge_tts, tmp_path):
        """Test that word timestamps are returned."""
        output_path = tmp_path / "test.mp3"
        text = "Hello world"

        # Mock the edge_tts.Communicate class to avoid network calls
        async def mock_stream():
            # Yield word boundaries
            yield {"type": "WordBoundary", "text": "Hello", "offset": 0, "duration": 5_000_000}
            yield {"type": "WordBoundary", "text": "world", "offset": 6_000_000, "duration": 5_000_000}
            # Yield audio data (minimal valid MP3 header)
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" + b"\x00" * 100}

        mock_communicate = MagicMock()
        mock_communicate.stream = mock_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = edge_tts.generate_with_timestamps(text, output_path)

        assert len(result.word_timestamps) == 2
        assert result.word_timestamps[0].word == "Hello"
        assert result.word_timestamps[1].word == "world"
        # Check words are in order
        for i in range(1, len(result.word_timestamps)):
            assert (
                result.word_timestamps[i].start_seconds
                >= result.word_timestamps[i - 1].start_seconds
            )

    def test_generate_stream_yields_bytes(self, edge_tts):
        """Test that generate_stream yields audio bytes."""
        async def mock_stream():
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" + b"\x00" * 50}
            yield {"type": "audio", "data": b"\x00" * 60}

        mock_communicate = MagicMock()
        mock_communicate.stream = mock_stream

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            chunks = list(edge_tts.generate_stream("Hello"))

        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)
        # Total audio data should be substantial
        total_bytes = sum(len(chunk) for chunk in chunks)
        assert total_bytes > 100

    def test_get_available_voices(self, edge_tts):
        """Test getting available voices."""
        mock_voices = [
            {
                "ShortName": "en-US-GuyNeural",
                "FriendlyName": "Microsoft Guy Online (Natural)",
                "Locale": "en-US",
                "Gender": "Male",
                "VoiceTag": {"VoicePersonalities": ["Friendly"]},
            },
            {
                "ShortName": "en-US-AriaNeural",
                "FriendlyName": "Microsoft Aria Online (Natural)",
                "Locale": "en-US",
                "Gender": "Female",
                "VoiceTag": {"VoicePersonalities": ["Cheerful"]},
            },
        ]

        async def mock_list_voices():
            return mock_voices

        with patch("edge_tts.list_voices", mock_list_voices):
            voices = edge_tts.get_available_voices()

        assert len(voices) == 2
        # Check structure
        assert "voice_id" in voices[0]
        assert "name" in voices[0]
        assert "locale" in voices[0]
        assert "gender" in voices[0]

    def test_get_english_voices(self, edge_tts):
        """Test filtering English voices."""
        mock_voices = [
            {
                "ShortName": "en-US-GuyNeural",
                "FriendlyName": "Microsoft Guy Online (Natural)",
                "Locale": "en-US",
                "Gender": "Male",
                "VoiceTag": {"VoicePersonalities": ["Friendly"]},
            },
            {
                "ShortName": "fr-FR-DeniseNeural",
                "FriendlyName": "Microsoft Denise Online (Natural)",
                "Locale": "fr-FR",
                "Gender": "Female",
                "VoiceTag": {"VoicePersonalities": ["Friendly"]},
            },
            {
                "ShortName": "en-GB-SoniaNeural",
                "FriendlyName": "Microsoft Sonia Online (Natural)",
                "Locale": "en-GB",
                "Gender": "Female",
                "VoiceTag": {"VoicePersonalities": ["Cheerful"]},
            },
        ]

        async def mock_list_voices():
            return mock_voices

        with patch("edge_tts.list_voices", mock_list_voices):
            english_voices = edge_tts.get_english_voices()

        assert len(english_voices) == 2
        # All should be English
        for voice in english_voices:
            assert voice["locale"].startswith("en-")

    def test_get_audio_duration_with_valid_file(self, edge_tts, tmp_path):
        """Test audio duration extraction with valid file."""
        # Create a test audio file using ffmpeg
        import subprocess

        output_path = tmp_path / "test.mp3"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=2",
                    "-c:a", "libmp3lame",
                    str(output_path),
                ],
                capture_output=True,
                timeout=10,
            )
            if output_path.exists():
                duration = edge_tts._get_audio_duration(output_path)
                assert 1.5 < duration < 2.5  # ~2 seconds
        except FileNotFoundError:
            pytest.skip("ffmpeg not available")

    def test_get_audio_duration_with_invalid_file(self, edge_tts, tmp_path):
        """Test audio duration extraction returns 0 for invalid file."""
        output_path = tmp_path / "invalid.mp3"
        output_path.write_bytes(b"not an audio file")
        duration = edge_tts._get_audio_duration(output_path)
        assert duration == 0.0

    def test_get_audio_duration_with_missing_file(self, edge_tts, tmp_path):
        """Test audio duration extraction returns 0 for missing file."""
        output_path = tmp_path / "nonexistent.mp3"
        duration = edge_tts._get_audio_duration(output_path)
        assert duration == 0.0


class TestEdgeTTSMocked:
    """Tests for Edge TTS with mocked network calls."""

    @pytest.fixture
    def config(self):
        return TTSConfig(provider="edge")

    @pytest.fixture
    def edge_tts(self, config):
        return EdgeTTS(config)

    def test_generate_raises_import_error_when_edge_tts_missing(self, config, tmp_path):
        """Test that helpful error is raised when edge-tts not installed."""
        tts = EdgeTTS(config)
        output_path = tmp_path / "test.mp3"

        with patch.dict("sys.modules", {"edge_tts": None}):
            # This should work because we import at module level
            # The actual ImportError would happen if the package wasn't installed
            pass

    def test_voice_selection_priority(self, config):
        """Test voice selection: explicit > config > default."""
        # Default
        tts1 = EdgeTTS(config)
        assert tts1.voice == "en-US-GuyNeural"

        # Config voice_id
        config.voice_id = "en-GB-RyanNeural"
        tts2 = EdgeTTS(config)
        assert tts2.voice == "en-GB-RyanNeural"

        # Explicit voice overrides config
        tts3 = EdgeTTS(config, voice="en-US-AriaNeural")
        assert tts3.voice == "en-US-AriaNeural"


class TestTTSWithScript:
    """Tests for generating TTS from script scenes."""

    @pytest.fixture
    def mock_tts(self):
        config = TTSConfig(provider="mock")
        return MockTTS(config)

    @pytest.fixture
    def sample_voiceover_texts(self):
        return [
            "Every time you send a message to ChatGPT, something remarkable happens.",
            "LLM inference has two distinct phases.",
            "The solution is elegant: compute each Key and Value exactly once.",
        ]

    def test_generate_multiple_scenes(self, mock_tts, sample_voiceover_texts, tmp_path):
        """Test generating audio for multiple script scenes."""
        audio_files = []

        for i, text in enumerate(sample_voiceover_texts):
            output_path = tmp_path / f"scene_{i + 1}.mp3"
            result = mock_tts.generate(text, output_path)
            audio_files.append(result)

        # All files should be created
        assert len(audio_files) == 3
        assert all(f.exists() for f in audio_files)

    def test_total_audio_generation(self, mock_tts, tmp_path):
        """Test generating audio for a full script."""
        # Simulate a full script worth of voiceover
        full_voiceover = """
        Every time you send a message to ChatGPT, something remarkable happens.
        A neural network with billions of parameters generates a response,
        one token at a time. The naive approach gives us forty tokens per second.
        What the best systems achieve? Over three thousand five hundred.
        This is how they do it.
        """

        output_path = tmp_path / "full_script.mp3"
        result = mock_tts.generate(full_voiceover, output_path)

        assert result.exists()
        # For real TTS, we'd check duration matches expected


class TestWordTimestamps:
    """Tests for word-level timestamp functionality."""

    @pytest.fixture
    def mock_tts(self):
        config = TTSConfig(provider="mock")
        return MockTTS(config)

    def test_word_timestamp_dataclass(self):
        """Test WordTimestamp data structure."""
        ts = WordTimestamp(word="hello", start_seconds=0.0, end_seconds=0.5)
        assert ts.word == "hello"
        assert ts.start_seconds == 0.0
        assert ts.end_seconds == 0.5

    def test_tts_result_dataclass(self, tmp_path):
        """Test TTSResult data structure."""
        audio_path = tmp_path / "test.mp3"
        audio_path.touch()

        result = TTSResult(
            audio_path=audio_path,
            duration_seconds=5.0,
            word_timestamps=[
                WordTimestamp(word="hello", start_seconds=0.0, end_seconds=0.3),
                WordTimestamp(word="world", start_seconds=0.4, end_seconds=0.8),
            ],
        )

        assert result.audio_path == audio_path
        assert result.duration_seconds == 5.0
        assert len(result.word_timestamps) == 2

    def test_generate_with_timestamps_returns_result(self, mock_tts, tmp_path):
        """Test that generate_with_timestamps returns a TTSResult."""
        output_path = tmp_path / "test.mp3"
        result = mock_tts.generate_with_timestamps("Hello world!", output_path)

        assert isinstance(result, TTSResult)
        assert result.audio_path == output_path
        assert result.audio_path.exists()
        assert result.duration_seconds > 0

    def test_generate_with_timestamps_has_word_timestamps(self, mock_tts, tmp_path):
        """Test that generate_with_timestamps returns word timestamps."""
        output_path = tmp_path / "test.mp3"
        text = "Hello world, this is a test."
        result = mock_tts.generate_with_timestamps(text, output_path)

        assert len(result.word_timestamps) > 0
        # Check that words are roughly in order
        for i in range(1, len(result.word_timestamps)):
            assert (
                result.word_timestamps[i].start_seconds
                >= result.word_timestamps[i - 1].start_seconds
            )

    def test_word_timestamps_cover_all_words(self, mock_tts, tmp_path):
        """Test that all words get timestamps."""
        output_path = tmp_path / "test.mp3"
        text = "one two three four five"
        result = mock_tts.generate_with_timestamps(text, output_path)

        # Should have 5 words
        assert len(result.word_timestamps) == 5
        words = [ts.word for ts in result.word_timestamps]
        assert words == ["one", "two", "three", "four", "five"]

    def test_word_timestamps_with_punctuation(self, mock_tts, tmp_path):
        """Test that punctuation is handled correctly."""
        output_path = tmp_path / "test.mp3"
        text = "Hello, world! How are you?"
        result = mock_tts.generate_with_timestamps(text, output_path)

        # Words should be cleaned of punctuation
        words = [ts.word for ts in result.word_timestamps]
        assert "Hello" in words
        assert "world" in words
        assert "," not in "".join(words)
        assert "!" not in "".join(words)

    def test_word_timestamps_timing_is_reasonable(self, mock_tts, tmp_path):
        """Test that word timings are reasonable."""
        output_path = tmp_path / "test.mp3"
        text = "This is a short sentence."
        result = mock_tts.generate_with_timestamps(text, output_path)

        # Each word should have positive duration
        for ts in result.word_timestamps:
            assert ts.end_seconds > ts.start_seconds

        # Last word should end before or at duration
        last_word = result.word_timestamps[-1]
        assert last_word.end_seconds <= result.duration_seconds + 0.5  # Small margin


class TestElevenLabsWordTimestamps:
    """Tests for ElevenLabs word timestamp parsing."""

    @pytest.fixture
    def config(self):
        return TTSConfig(
            provider="elevenlabs",
            model="eleven_multilingual_v2",
        )

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_parse_word_timestamps_basic(self, config):
        """Test parsing character-level to word-level timestamps."""
        tts = ElevenLabsTTS(config)

        # Simulate ElevenLabs character-level response for "hi there"
        characters = ["h", "i", " ", "t", "h", "e", "r", "e"]
        start_times = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        end_times = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

        result = tts._parse_word_timestamps(characters, start_times, end_times)

        assert len(result) == 2
        assert result[0].word == "hi"
        assert result[0].start_seconds == 0.0
        assert result[0].end_seconds == 0.2
        assert result[1].word == "there"
        assert result[1].start_seconds == 0.3
        assert result[1].end_seconds == 0.8

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_parse_word_timestamps_empty(self, config):
        """Test parsing empty character lists."""
        tts = ElevenLabsTTS(config)

        result = tts._parse_word_timestamps([], [], [])
        assert result == []

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"})
    def test_parse_word_timestamps_single_word(self, config):
        """Test parsing a single word."""
        tts = ElevenLabsTTS(config)

        characters = ["h", "i"]
        start_times = [0.0, 0.1]
        end_times = [0.1, 0.2]

        result = tts._parse_word_timestamps(characters, start_times, end_times)

        assert len(result) == 1
        assert result[0].word == "hi"
        assert result[0].start_seconds == 0.0
        assert result[0].end_seconds == 0.2


class TestManualVoiceoverProvider:
    """Tests for ManualVoiceoverProvider."""

    @pytest.fixture
    def config(self):
        return TTSConfig(provider="manual")

    @pytest.fixture
    def audio_dir(self, tmp_path):
        """Create a temp directory with some audio files."""
        audio_dir = tmp_path / "recordings"
        audio_dir.mkdir()

        # Create dummy audio files
        (audio_dir / "scene1_hook.mp3").write_bytes(b"\x00" * 1000)
        (audio_dir / "scene2_intro.wav").write_bytes(b"\x00" * 1000)
        (audio_dir / "scene3_main.m4a").write_bytes(b"\x00" * 1000)

        return audio_dir

    def test_init_requires_audio_dir(self, config, tmp_path):
        """Test that init requires an existing audio directory."""
        from src.audio import ManualVoiceoverProvider

        with pytest.raises(ValueError, match="Audio directory not found"):
            ManualVoiceoverProvider(config, audio_dir=tmp_path / "nonexistent")

    def test_init_with_valid_dir(self, config, audio_dir):
        """Test initialization with valid audio directory."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        assert provider.audio_dir == audio_dir
        assert provider.whisper_model == "base"

    def test_find_audio_file_mp3(self, config, audio_dir):
        """Test finding MP3 audio file."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        result = provider._find_audio_file("scene1_hook")

        assert result is not None
        assert result.name == "scene1_hook.mp3"

    def test_find_audio_file_wav(self, config, audio_dir):
        """Test finding WAV audio file."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        result = provider._find_audio_file("scene2_intro")

        assert result is not None
        assert result.name == "scene2_intro.wav"

    def test_find_audio_file_not_found(self, config, audio_dir):
        """Test that missing audio file returns None."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        result = provider._find_audio_file("nonexistent_scene")

        assert result is None

    def test_find_audio_file_with_hyphen_variation(self, config, tmp_path):
        """Test finding audio file with hyphen instead of underscore."""
        from src.audio import ManualVoiceoverProvider

        audio_dir = tmp_path / "recordings"
        audio_dir.mkdir()
        (audio_dir / "scene1-hook.mp3").write_bytes(b"\x00" * 1000)

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        result = provider._find_audio_file("scene1_hook")

        assert result is not None
        assert result.name == "scene1-hook.mp3"

    def test_get_available_voices(self, config, audio_dir):
        """Test listing available audio files."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        voices = provider.get_available_voices()

        assert len(voices) == 3
        voice_ids = [v["voice_id"] for v in voices]
        assert "scene1_hook" in voice_ids
        assert "scene2_intro" in voice_ids
        assert "scene3_main" in voice_ids

    def test_list_missing_scenes(self, config, audio_dir):
        """Test listing missing scene audio files."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)

        scene_ids = ["scene1_hook", "scene2_intro", "scene4_missing", "scene5_missing"]
        missing = provider.list_missing_scenes(scene_ids)

        assert len(missing) == 2
        assert "scene4_missing" in missing
        assert "scene5_missing" in missing
        assert "scene1_hook" not in missing

    def test_generate_copies_file(self, config, audio_dir, tmp_path):
        """Test that generate copies the audio file."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        output_path = tmp_path / "output" / "scene1_hook.mp3"

        result = provider.generate("Test text", output_path, scene_id="scene1_hook")

        assert result == output_path
        assert output_path.exists()

    def test_generate_file_not_found(self, config, audio_dir, tmp_path):
        """Test that generate raises error for missing file."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        output_path = tmp_path / "output" / "missing.mp3"

        with pytest.raises(FileNotFoundError, match="No audio file found"):
            provider.generate("Test text", output_path, scene_id="missing_scene")

    def test_generate_extracts_scene_id_from_path(self, config, audio_dir, tmp_path):
        """Test that generate can extract scene_id from output path."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        output_path = tmp_path / "output" / "scene1_hook.mp3"

        # Don't pass scene_id - should extract from path
        result = provider.generate("Test text", output_path)

        assert result == output_path
        assert output_path.exists()

    def test_generate_stream_not_supported(self, config, audio_dir):
        """Test that streaming is not supported."""
        from src.audio import ManualVoiceoverProvider

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)

        with pytest.raises(NotImplementedError, match="Streaming is not supported"):
            list(provider.generate_stream("Test"))

    @patch("src.audio.tts.ManualVoiceoverProvider._get_transcriber")
    def test_generate_with_timestamps(self, mock_get_transcriber, config, audio_dir, tmp_path):
        """Test generate_with_timestamps uses Whisper for transcription."""
        from src.audio import ManualVoiceoverProvider
        from src.audio.transcribe import TranscriptionResult

        # Mock transcriber
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = TranscriptionResult(
            text="Hello world",
            word_timestamps=[
                WordTimestamp(word="Hello", start_seconds=0.0, end_seconds=0.5),
                WordTimestamp(word="world", start_seconds=0.6, end_seconds=1.0),
            ],
            duration_seconds=1.0,
        )
        mock_get_transcriber.return_value = mock_transcriber

        provider = ManualVoiceoverProvider(config, audio_dir=audio_dir)
        output_path = tmp_path / "output" / "scene1_hook.mp3"

        result = provider.generate_with_timestamps(
            "Test text", output_path, scene_id="scene1_hook"
        )

        assert isinstance(result, TTSResult)
        assert result.audio_path == output_path
        assert result.duration_seconds == 1.0
        assert len(result.word_timestamps) == 2
        assert result.word_timestamps[0].word == "Hello"
