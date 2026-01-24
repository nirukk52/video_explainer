"""Tests for YouTube Shorts generation module."""

import json
from pathlib import Path

import pytest

from src.config import Config
from src.models import Script, ScriptScene, VisualCue
from src.short import ShortGenerator, ShortSceneGenerator, ShortConfig, ShortScript, ShortScene
from src.short.models import HookAnalysis, CondensedNarration, ShortResult, ShortsVisual, VisualType
from src.short.generator import normalize_script_format


class TestShortModels:
    """Tests for short data models."""

    def test_short_config_defaults(self):
        config = ShortConfig()
        assert config.width == 1080
        assert config.height == 1920
        assert config.fps == 30
        assert config.target_duration_seconds == 45
        assert config.include_cta is True
        assert config.cta_duration_seconds == 5.0

    def test_short_config_custom(self):
        config = ShortConfig(
            width=720,
            height=1280,
            fps=24,
            target_duration_seconds=30,
        )
        assert config.width == 720
        assert config.height == 1280
        assert config.fps == 24
        assert config.target_duration_seconds == 30

    def test_short_scene(self):
        """Test ShortScene without condensed_narration (now at script level)."""
        scene = ShortScene(
            source_scene_id="scene1_hook",
            duration_seconds=20.0,
        )
        assert scene.source_scene_id == "scene1_hook"
        assert scene.condensed_narration == ""  # Default empty
        assert scene.duration_seconds == 20.0

    def test_short_scene_with_deprecated_narration(self):
        """Test ShortScene with deprecated condensed_narration for backwards compatibility."""
        scene = ShortScene(
            source_scene_id="scene1_hook",
            condensed_narration="Legacy narration",
            duration_seconds=20.0,
        )
        assert scene.condensed_narration == "Legacy narration"

    def test_short_script(self):
        """Test ShortScript with condensed_narration at script level."""
        script = ShortScript(
            source_project="test-project",
            title="Test Short",
            condensed_narration="This is the full condensed narration for the short.",
            hook_question="How did they solve this?",
            scenes=[
                ShortScene(
                    source_scene_id="scene1",
                    duration_seconds=20.0,
                )
            ],
            cta_text="Full breakdown in description",
            cta_narration="Want to know more?",
            total_duration_seconds=45.0,
        )
        assert script.source_project == "test-project"
        assert script.title == "Test Short"
        assert script.condensed_narration == "This is the full condensed narration for the short."
        assert len(script.scenes) == 1
        assert script.scenes[0].condensed_narration == ""  # Not in scene
        assert script.total_duration_seconds == 45.0

    def test_hook_analysis(self):
        analysis = HookAnalysis(
            selected_scene_ids=["scene1", "scene2"],
            hook_question="How did they do it?",
            reasoning="These scenes create maximum curiosity.",
        )
        assert len(analysis.selected_scene_ids) == 2
        assert analysis.hook_question == "How did they do it?"

    def test_condensed_narration(self):
        narration = CondensedNarration(
            condensed_narration="Short and punchy content.",
            cta_narration="Check the description!",
            hook_question="Want to know the secret?",
        )
        assert "punchy" in narration.condensed_narration
        assert narration.cta_narration == "Check the description!"

    def test_short_result_success(self, tmp_path):
        result = ShortResult(
            success=True,
            variant="default",
            short_script_path=tmp_path / "script.json",
            scenes_dir=tmp_path / "scenes",
        )
        assert result.success is True
        assert result.variant == "default"
        assert result.error is None

    def test_short_result_failure(self):
        result = ShortResult(
            success=False,
            variant="test",
            error="Script not found",
        )
        assert result.success is False
        assert result.error == "Script not found"


class TestShortGenerator:
    """Tests for the short generator."""

    @pytest.fixture
    def generator(self, mock_config):
        return ShortGenerator(config=mock_config)

    @pytest.fixture
    def sample_script(self) -> Script:
        """Create a sample script for testing."""
        return Script(
            title="Test Video: Understanding AI",
            total_duration_seconds=180,
            scenes=[
                ScriptScene(
                    scene_id="scene_1",
                    scene_type="hook",
                    title="The Surprising Discovery",
                    voiceover="What if AI could do something nobody expected?",
                    visual_cue=VisualCue(
                        description="Surprising reveal",
                        visual_type="animation",
                        elements=["surprise"],
                        duration_seconds=15.0,
                    ),
                    duration_seconds=15.0,
                ),
                ScriptScene(
                    scene_id="scene_2",
                    scene_type="context",
                    title="The Challenge",
                    voiceover="For years, researchers struggled with this problem.",
                    visual_cue=VisualCue(
                        description="Problem visualization",
                        visual_type="animation",
                        elements=["challenge"],
                        duration_seconds=30.0,
                    ),
                    duration_seconds=30.0,
                ),
                ScriptScene(
                    scene_id="scene_3",
                    scene_type="explanation",
                    title="The Breakthrough",
                    voiceover="Then, in 2023, everything changed.",
                    visual_cue=VisualCue(
                        description="Solution reveal",
                        visual_type="animation",
                        elements=["breakthrough"],
                        duration_seconds=45.0,
                    ),
                    duration_seconds=45.0,
                ),
            ],
            source_document="test.md",
        )

    @pytest.fixture
    def sample_narrations(self) -> list[dict]:
        return [
            {
                "scene_id": "scene1_surprising_discovery",
                "title": "The Surprising Discovery",
                "duration_seconds": 15,
                "narration": "What if AI could do something nobody expected? The numbers are staggering.",
            },
            {
                "scene_id": "scene2_challenge",
                "title": "The Challenge",
                "duration_seconds": 30,
                "narration": "For years, researchers struggled. 99% of attempts failed.",
            },
            {
                "scene_id": "scene3_breakthrough",
                "title": "The Breakthrough",
                "duration_seconds": 45,
                "narration": "Then, in 2023, a team achieved the impossible. Here's how.",
            },
        ]

    def test_generator_initializes(self, generator):
        assert generator.config is not None
        assert generator.llm is not None

    def test_analyze_for_hook(self, generator, sample_script, sample_narrations):
        result = generator.analyze_for_hook(sample_script, sample_narrations)
        assert isinstance(result, HookAnalysis)
        # Mock LLM may return empty scene_ids, but result should be valid
        assert isinstance(result.selected_scene_ids, list)
        assert result.hook_question is not None

    def test_generate_condensed_narration(
        self, generator, sample_script, sample_narrations
    ):
        selected_ids = ["scene1_surprising_discovery", "scene2_challenge"]
        result = generator.generate_condensed_narration(
            sample_script,
            sample_narrations,
            selected_ids,
            target_duration=45,
        )
        assert isinstance(result, CondensedNarration)
        assert result.condensed_narration is not None
        assert result.cta_narration is not None

    def test_generate_mock_short_script(self, generator):
        script = generator.generate_mock_short_script(
            project_id="test-project",
            topic="Machine Learning",
            duration=45,
        )
        assert isinstance(script, ShortScript)
        assert script.source_project == "test-project"
        assert "Machine Learning" in script.hook_question
        assert len(script.scenes) >= 1
        assert script.total_duration_seconds == 45

    def test_save_and_load_short_script(self, generator, tmp_path):
        script = generator.generate_mock_short_script(
            project_id="test",
            topic="Test Topic",
        )
        script_path = tmp_path / "short_script.json"
        generator.save_short_script(script, script_path)

        assert script_path.exists()

        loaded = ShortGenerator.load_short_script(script_path)
        assert loaded.source_project == script.source_project
        assert loaded.title == script.title
        assert loaded.total_duration_seconds == script.total_duration_seconds


class TestShortSceneGenerator:
    """Tests for the vertical scene generator."""

    @pytest.fixture
    def generator(self, mock_config):
        return ShortSceneGenerator(config=mock_config)

    @pytest.fixture
    def sample_short_script(self) -> ShortScript:
        return ShortScript(
            source_project="test-project",
            title="Test Short Video",
            condensed_narration="Punchy content here.",  # At script level
            hook_question="How did they solve this impossible problem?",
            scenes=[
                ShortScene(
                    source_scene_id="scene1_hook",
                    duration_seconds=20.0,
                )
            ],
            cta_text="Full breakdown in description",
            cta_narration="Want to know how? Check the description.",
            total_duration_seconds=45.0,
        )

    def test_generator_initializes(self, generator):
        assert generator.config is not None

    def test_generate_vertical_styles(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        styles_path = generator.generate_vertical_styles(
            scenes_dir, "Test Project"
        )

        assert styles_path.exists()
        content = styles_path.read_text()

        # Check for vertical-specific values
        assert "CANVAS_WIDTH = 1080" in content
        assert "CANVAS_HEIGHT = 1920" in content
        assert "LAYOUT" in content
        assert "COLORS" in content
        assert "FONTS" in content

    def test_generate_cta_scene(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        cta_path = generator.generate_cta_scene(
            scenes_dir, "Test Project"
        )

        assert cta_path.exists()
        content = cta_path.read_text()

        # Check for CTA-specific content
        assert "CTAScene" in content
        assert "hookQuestion" in content
        assert "ctaText" in content
        assert "thumbnailUrl" in content

    def test_generate_index(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        scene_components = [
            {"name": "CTAScene", "filename": "CTAScene.tsx", "scene_key": "cta"},
            {"name": "HookScene", "filename": "HookScene.tsx", "scene_key": "hook"},
        ]

        index_path = generator.generate_index(
            scenes_dir, "Test Project", scene_components
        )

        assert index_path.exists()
        content = index_path.read_text()

        # Check for index content
        assert "sceneRegistry" in content
        assert "CTAScene" in content
        assert "HookScene" in content

    def test_setup_short_scenes(self, generator, sample_short_script, tmp_path):
        # Create a mock project-like structure
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        class MockProject:
            id = "test-project"
            root_dir = project_dir
            title = "Test Project"

        project = MockProject()

        paths = generator.setup_short_scenes(
            project, sample_short_script, variant="default"
        )

        assert paths["scenes_dir"].exists()
        assert paths["styles_path"].exists()
        assert paths["cta_path"].exists()
        assert paths["index_path"].exists()


class TestShortGeneratorIntegration:
    """Integration tests for short generation with mock project."""

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a mock project directory with required files."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create config
        config = {
            "id": "test-project",
            "title": "Test Project",
            "description": "A test project",
            "version": "1.0.0",
            "video": {
                "resolution": {"width": 1920, "height": 1080},
                "fps": 30,
            },
            "tts": {"provider": "mock"},
            "style": {},
            "paths": {
                "script": "script/script.json",
                "narration": "narration/narrations.json",
            },
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        # Create script
        script_dir = project_dir / "script"
        script_dir.mkdir()
        script = {
            "title": "Test Video",
            "total_duration_seconds": 120,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Hook",
                    "voiceover": "Amazing discovery!",
                    "visual_cue": {
                        "description": "Reveal",
                        "visual_type": "animation",
                        "elements": [],
                        "duration_seconds": 15,
                    },
                    "duration_seconds": 15,
                }
            ],
            "source_document": "test.md",
        }
        with open(script_dir / "script.json", "w") as f:
            json.dump(script, f)

        # Create narrations
        narration_dir = project_dir / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {
                    "scene_id": "scene1_hook",
                    "title": "The Hook",
                    "duration_seconds": 15,
                    "narration": "This is an amazing discovery that will change everything.",
                }
            ],
            "total_duration_seconds": 15,
        }
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump(narrations, f)

        return project_dir

    def test_generate_short_with_mock_project(self, mock_project_dir, mock_config):
        from src.project import load_project

        project = load_project(mock_project_dir)
        generator = ShortGenerator(config=mock_config)

        result = generator.generate_short(
            project,
            variant="test",
            duration=45,
            mock=True,
        )

        assert result.success is True
        assert result.variant == "test"
        assert result.short_script_path is not None
        assert result.short_script_path.exists()

        # Verify short script content
        script = ShortGenerator.load_short_script(result.short_script_path)
        assert script.source_project == "test-project"
        assert len(script.scenes) > 0

    def test_generate_short_with_scene_override(self, mock_project_dir, mock_config):
        from src.project import load_project

        project = load_project(mock_project_dir)
        generator = ShortGenerator(config=mock_config)

        result = generator.generate_short(
            project,
            variant="custom",
            scene_ids=["scene1_hook"],
            mock=True,
        )

        assert result.success is True

    def test_generate_short_invalid_scene_ids(self, mock_project_dir, mock_config):
        from src.project import load_project

        project = load_project(mock_project_dir)
        generator = ShortGenerator(config=mock_config)

        result = generator.generate_short(
            project,
            scene_ids=["invalid_scene_id"],
            mock=True,
        )

        assert result.success is False
        assert "invalid" in result.error.lower()


class TestVerticalStylesTemplate:
    """Tests for the vertical styles template content."""

    @pytest.fixture
    def generator(self, mock_config):
        return ShortSceneGenerator(config=mock_config)

    def test_vertical_layout_dimensions(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        styles_path = generator.generate_vertical_styles(scenes_dir, "Test")
        content = styles_path.read_text()

        # Verify vertical-specific dimensions
        assert "CANVAS_WIDTH = 1080" in content
        assert "CANVAS_HEIGHT = 1920" in content

        # Verify margins are adjusted for vertical
        assert "MARGIN_LEFT = 40" in content
        assert "MARGIN_RIGHT = 40" in content

    def test_vertical_layout_helpers(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        styles_path = generator.generate_vertical_styles(scenes_dir, "Test")
        content = styles_path.read_text()

        # Verify layout helpers exist
        assert "getFlexibleGrid" in content
        assert "getCenteredPosition" in content
        assert "getTwoColumnLayout" in content
        assert "getTwoRowLayout" in content
        assert "getThreeRowLayout" in content  # Vertical-specific


class TestCTASceneTemplate:
    """Tests for the CTA scene template content."""

    @pytest.fixture
    def generator(self, mock_config):
        return ShortSceneGenerator(config=mock_config)

    def test_cta_scene_props(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        cta_path = generator.generate_cta_scene(scenes_dir, "Test")
        content = cta_path.read_text()

        # Verify props
        assert "hookQuestion" in content
        assert "ctaText" in content
        assert "thumbnailUrl" in content
        assert "channelName" in content

    def test_cta_scene_animations(self, generator, tmp_path):
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        cta_path = generator.generate_cta_scene(scenes_dir, "Test")
        content = cta_path.read_text()

        # Verify animation functions
        assert "useCurrentFrame" in content
        assert "interpolate" in content
        assert "spring" in content


class TestNormalizeScriptFormat:
    """Tests for the normalize_script_format function."""

    def test_normalizes_visual_description_to_visual_cue(self):
        """Test that flat visual_description is converted to visual_cue object."""
        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 100,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Hook",
                    "voiceover": "Test voiceover",
                    "visual_description": "Show animation of concept",
                    "duration_seconds": 30.0,
                }
            ],
        }

        normalized = normalize_script_format(script_data)

        assert "visual_cue" in normalized["scenes"][0]
        assert "visual_description" not in normalized["scenes"][0]
        assert normalized["scenes"][0]["visual_cue"]["description"] == "Show animation of concept"
        assert normalized["scenes"][0]["visual_cue"]["visual_type"] == "animation"
        assert normalized["scenes"][0]["visual_cue"]["elements"] == []
        assert normalized["scenes"][0]["visual_cue"]["duration_seconds"] == 30.0

    def test_preserves_existing_visual_cue(self):
        """Test that existing visual_cue objects are not modified."""
        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 100,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Hook",
                    "voiceover": "Test voiceover",
                    "visual_cue": {
                        "description": "Original description",
                        "visual_type": "diagram",
                        "elements": ["element1", "element2"],
                        "duration_seconds": 20.0,
                    },
                    "duration_seconds": 30.0,
                }
            ],
        }

        normalized = normalize_script_format(script_data)

        assert normalized["scenes"][0]["visual_cue"]["description"] == "Original description"
        assert normalized["scenes"][0]["visual_cue"]["visual_type"] == "diagram"
        assert normalized["scenes"][0]["visual_cue"]["elements"] == ["element1", "element2"]

    def test_adds_missing_source_document(self):
        """Test that source_document is added if missing."""
        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 100,
            "scenes": [],
        }

        normalized = normalize_script_format(script_data)

        assert "source_document" in normalized
        assert normalized["source_document"] == ""

    def test_preserves_existing_source_document(self):
        """Test that existing source_document is preserved."""
        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 100,
            "scenes": [],
            "source_document": "original.md",
        }

        normalized = normalize_script_format(script_data)

        assert normalized["source_document"] == "original.md"

    def test_handles_empty_scenes(self):
        """Test handling of script with no scenes."""
        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 0,
            "scenes": [],
        }

        normalized = normalize_script_format(script_data)

        assert normalized["scenes"] == []

    def test_handles_missing_scenes_key(self):
        """Test handling of script without scenes key."""
        script_data = {
            "title": "Test Video",
        }

        normalized = normalize_script_format(script_data)

        # Should return unchanged if no scenes key
        assert normalized == {"title": "Test Video"}

    def test_normalized_script_can_be_loaded(self):
        """Test that normalized script data can be loaded as Script model."""
        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 100,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Hook",
                    "voiceover": "Test voiceover",
                    "visual_description": "Show animation of concept",
                    "duration_seconds": 30.0,
                }
            ],
        }

        normalized = normalize_script_format(script_data)
        script = Script(**normalized)

        assert script.title == "Test Video"
        assert len(script.scenes) == 1
        assert script.scenes[0].visual_cue.description == "Show animation of concept"


class TestCTABeatTiming:
    """Tests for CTA beat timing edge cases."""

    @pytest.fixture
    def generator(self, mock_config):
        return ShortGenerator(config=mock_config)

    @pytest.fixture
    def sample_short_script(self) -> ShortScript:
        return ShortScript(
            source_project="test-project",
            title="Test Short",
            condensed_narration="Test narration content here.",  # At script level
            hook_question="How did they solve this?",
            scenes=[
                ShortScene(
                    source_scene_id="scene1",
                    duration_seconds=20.0,
                )
            ],
            cta_text="Full breakdown in description",
            cta_narration="Want to know more? Check the description.",
            total_duration_seconds=45.0,
        )

    def test_cta_timing_with_gap(self, generator, sample_short_script):
        """Test CTA beat is created with gap when voiceover ends early."""
        word_timestamps = [
            {"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "narration", "start_seconds": 0.6, "end_seconds": 1.2},
            {"word": "content", "start_seconds": 1.3, "end_seconds": 1.8},
            {"word": "here.", "start_seconds": 1.9, "end_seconds": 2.5},
        ]
        voiceover_duration = 5.0  # Plenty of time after last word

        storyboard = generator.generate_shorts_storyboard_from_voiceover(
            sample_short_script,
            word_timestamps,
            voiceover_duration,
            mock=True,
        )

        # Find CTA beat
        cta_beat = next((b for b in storyboard.beats if b.id == "cta"), None)
        assert cta_beat is not None
        # CTA should start 0.5s after last word (2.5 + 0.5 = 3.0)
        assert cta_beat.start_seconds == 3.0
        assert cta_beat.end_seconds == voiceover_duration
        # Verify timing is valid
        assert cta_beat.start_seconds < cta_beat.end_seconds

    def test_cta_timing_near_end(self, generator, sample_short_script):
        """Test CTA timing when voiceover ends near total duration."""
        # Voiceover ends at 19.5s, duration is 20.0s
        word_timestamps = [
            {"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "narration", "start_seconds": 0.6, "end_seconds": 1.2},
            {"word": "content", "start_seconds": 18.5, "end_seconds": 19.0},
            {"word": "here.", "start_seconds": 19.1, "end_seconds": 19.5},
        ]
        voiceover_duration = 20.0

        storyboard = generator.generate_shorts_storyboard_from_voiceover(
            sample_short_script,
            word_timestamps,
            voiceover_duration,
            mock=True,
        )

        # Find CTA beat
        cta_beat = next((b for b in storyboard.beats if b.id == "cta"), None)
        assert cta_beat is not None
        # CTA start should be adjusted (not 19.5 + 0.5 = 20.0 which would be >= end)
        assert cta_beat.start_seconds < cta_beat.end_seconds
        # CTA end should be voiceover_duration
        assert cta_beat.end_seconds == voiceover_duration

    def test_cta_timing_voiceover_fills_duration(self, generator, sample_short_script):
        """Test CTA beat when voiceover completely fills the duration."""
        # Last word ends at exactly the voiceover duration
        word_timestamps = [
            {"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "narration", "start_seconds": 0.6, "end_seconds": 1.2},
            {"word": "content", "start_seconds": 19.0, "end_seconds": 19.5},
            {"word": "here.", "start_seconds": 19.6, "end_seconds": 20.0},
        ]
        voiceover_duration = 20.0

        storyboard = generator.generate_shorts_storyboard_from_voiceover(
            sample_short_script,
            word_timestamps,
            voiceover_duration,
            mock=True,
        )

        # CTA beat should not have invalid timing (start >= end)
        cta_beat = next((b for b in storyboard.beats if b.id == "cta"), None)
        if cta_beat is not None:
            # If CTA exists, timing must be valid
            assert cta_beat.start_seconds < cta_beat.end_seconds
        # If no CTA beat, that's also acceptable when there's no time

    def test_no_cta_when_no_time(self, generator, sample_short_script):
        """Test that CTA is not added when there's no time for it."""
        # Last word ends after voiceover duration (edge case)
        word_timestamps = [
            {"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "here.", "start_seconds": 20.1, "end_seconds": 20.5},
        ]
        voiceover_duration = 20.0  # Less than last word end

        storyboard = generator.generate_shorts_storyboard_from_voiceover(
            sample_short_script,
            word_timestamps,
            voiceover_duration,
            mock=True,
        )

        # CTA beat should not exist or should have valid timing
        cta_beat = next((b for b in storyboard.beats if b.id == "cta"), None)
        if cta_beat is not None:
            assert cta_beat.start_seconds < cta_beat.end_seconds

    def test_all_beats_have_valid_timing(self, generator, sample_short_script):
        """Test that all beats (including CTA) have valid start < end timing."""
        word_timestamps = [
            {"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "content.", "start_seconds": 0.6, "end_seconds": 1.2},
        ]
        voiceover_duration = 2.0

        storyboard = generator.generate_shorts_storyboard_from_voiceover(
            sample_short_script,
            word_timestamps,
            voiceover_duration,
            mock=True,
        )

        # All beats must have valid timing
        for beat in storyboard.beats:
            assert beat.start_seconds < beat.end_seconds, \
                f"Beat {beat.id} has invalid timing: start={beat.start_seconds}, end={beat.end_seconds}"
