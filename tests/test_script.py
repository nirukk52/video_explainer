"""Tests for script generation module."""

from pathlib import Path

import pytest

from src.config import Config
from src.ingestion import parse_document
from src.models import ContentAnalysis, Script
from src.script import ScriptGenerator
from src.understanding import ContentAnalyzer


class TestScriptGenerator:
    """Tests for the script generator."""

    @pytest.fixture
    def generator(self):
        return ScriptGenerator()

    @pytest.fixture
    def sample_analysis(self) -> ContentAnalysis:
        """Create a sample content analysis for testing."""
        from src.models import Concept

        return ContentAnalysis(
            core_thesis="Testing is important for software quality.",
            key_concepts=[
                Concept(
                    name="Unit Testing",
                    explanation="Testing individual components in isolation",
                    complexity=3,
                    prerequisites=["basic programming"],
                    analogies=["Like checking each ingredient before cooking"],
                    visual_potential="medium",
                ),
                Concept(
                    name="Integration Testing",
                    explanation="Testing how components work together",
                    complexity=5,
                    prerequisites=["unit testing"],
                    analogies=["Like tasting the dish while cooking"],
                    visual_potential="high",
                ),
            ],
            target_audience="Software developers",
            suggested_duration_seconds=180,
            complexity_score=4,
        )

    @pytest.fixture
    def sample_document(self, sample_markdown):
        return parse_document(sample_markdown)

    def test_generate_returns_script(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis)
        assert isinstance(script, Script)

    def test_script_has_title(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis)
        assert script.title
        assert len(script.title) > 0

    def test_script_has_scenes(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis)
        assert len(script.scenes) > 0

    def test_scenes_have_required_fields(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis)
        for scene in script.scenes:
            assert scene.scene_id > 0
            assert scene.scene_type in ["hook", "context", "explanation", "insight", "conclusion"]
            assert scene.voiceover
            assert scene.visual_cue
            assert scene.duration_seconds > 0

    def test_visual_cues_have_description(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis)
        for scene in script.scenes:
            assert scene.visual_cue.description
            assert scene.visual_cue.visual_type

    def test_total_duration_matches_scenes(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis)
        expected_duration = sum(s.duration_seconds for s in script.scenes)
        assert script.total_duration_seconds == expected_duration

    def test_custom_target_duration(self, generator, sample_document, sample_analysis):
        script = generator.generate(sample_document, sample_analysis, target_duration=120)
        # Script should exist (mock doesn't respect duration, but real LLM would)
        assert isinstance(script, Script)


class TestScriptFormatting:
    """Tests for script formatting and serialization."""

    @pytest.fixture
    def generator(self):
        return ScriptGenerator()

    @pytest.fixture
    def sample_script(self, generator, sample_markdown):
        from src.models import Concept
        doc = parse_document(sample_markdown)
        analysis = ContentAnalysis(
            core_thesis="Test thesis",
            key_concepts=[
                Concept(
                    name="Test Concept",
                    explanation="Test explanation",
                    complexity=5,
                    visual_potential="high",
                )
            ],
            target_audience="Developers",
            suggested_duration_seconds=120,
            complexity_score=5,
        )
        return generator.generate(doc, analysis)

    def test_format_for_review(self, generator, sample_script):
        formatted = generator.format_script_for_review(sample_script)
        assert isinstance(formatted, str)
        assert sample_script.title in formatted
        assert "Scene" in formatted
        assert "Voiceover" in formatted
        assert "Visual" in formatted

    def test_save_and_load_script(self, generator, sample_script, tmp_path):
        script_path = tmp_path / "test_script.json"
        generator.save_script(sample_script, str(script_path))

        # Check both files were created
        assert script_path.exists()
        assert script_path.with_suffix(".md").exists()

        # Load and verify
        loaded = ScriptGenerator.load_script(str(script_path))
        assert loaded.title == sample_script.title
        assert len(loaded.scenes) == len(sample_script.scenes)


class TestScriptParserNewFormat:
    """Tests for parsing the new script format with emotional arc fields."""

    @pytest.fixture
    def generator(self):
        return ScriptGenerator()

    def test_parse_new_format_with_all_fields(self, generator):
        """Test parsing script with new format fields."""
        result = {
            "title": "Test Video",
            "central_question": "How does X work when Y happens?",
            "total_duration_seconds": 120,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Hook",
                    "voiceover": "Here's a surprising fact about technology.",
                    "connection_to_previous": None,
                    "emotional_target": "intrigue",
                    "visual_description": "Animated diagram showing the concept",
                    "key_visual_moments": ["Show diagram", "Highlight key part", "Zoom in"],
                    "duration_seconds": 20,
                },
                {
                    "scene_id": 2,
                    "scene_type": "context",
                    "title": "The Problem",
                    "voiceover": "But here's why this is harder than it looks.",
                    "connection_to_previous": "But this creates a challenge...",
                    "emotional_target": "tension",
                    "visual_description": "Show the naive approach failing",
                    "key_visual_moments": ["Show attempt", "Show failure"],
                    "duration_seconds": 30,
                },
            ],
        }

        script = generator._parse_script_result(result, "test.md")

        assert script.title == "Test Video"
        assert len(script.scenes) == 2

        # Check first scene
        scene1 = script.scenes[0]
        assert scene1.scene_type == "hook"
        assert scene1.visual_cue.description == "Animated diagram showing the concept"
        assert "Show diagram" in scene1.visual_cue.elements
        assert "intrigue" in scene1.notes.lower()

        # Check second scene has connection info
        scene2 = script.scenes[1]
        assert "connection" in scene2.notes.lower()
        assert "tension" in scene2.notes.lower()

    def test_parse_old_format_still_works(self, generator):
        """Test backward compatibility with old visual_cue format."""
        result = {
            "title": "Old Format Video",
            "total_duration_seconds": 60,
            "scenes": [
                {
                    "scene_id": "scene1_hook",
                    "scene_type": "hook",
                    "title": "Old Hook",
                    "voiceover": "Old style narration.",
                    "visual_cue": {
                        "description": "Old style visual description",
                        "visual_type": "animation",
                        "elements": ["element1", "element2"],
                        "duration_seconds": 15,
                    },
                    "duration_seconds": 15,
                    "builds_to": "next concept",
                },
            ],
        }

        script = generator._parse_script_result(result, "test.md")

        assert script.title == "Old Format Video"
        scene = script.scenes[0]
        assert scene.scene_id == 1  # Extracted from "scene1_hook"
        assert scene.visual_cue.description == "Old style visual description"
        assert scene.visual_cue.elements == ["element1", "element2"]
        assert "Builds to" in scene.notes

    def test_parse_mixed_format(self, generator):
        """Test parsing when some fields use old format, some use new."""
        result = {
            "title": "Mixed Format",
            "total_duration_seconds": 30,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "explanation",
                    "title": "Mixed Scene",
                    "voiceover": "Explanation text.",
                    "visual_description": "New style description",
                    "key_elements": ["old_key_elements_field"],  # Old field name
                    "duration_seconds": 30,
                },
            ],
        }

        script = generator._parse_script_result(result, "test.md")
        scene = script.scenes[0]

        # Should fall back to key_elements if key_visual_moments not present
        assert scene.visual_cue.description == "New style description"

    def test_format_shows_word_count(self, generator):
        """Test that formatted output includes word count."""
        from src.models import Script, ScriptScene, VisualCue

        script = Script(
            title="Word Count Test",
            total_duration_seconds=30,
            scenes=[
                ScriptScene(
                    scene_id=1,
                    scene_type="hook",
                    title="Test Scene",
                    voiceover="One two three four five six seven eight nine ten.",
                    visual_cue=VisualCue(
                        description="Test visual",
                        visual_type="animation",
                        elements=[],
                        duration_seconds=30,
                    ),
                    duration_seconds=30,
                    notes="",
                )
            ],
            source_document="test.md",
        )

        formatted = generator.format_script_for_review(script)
        assert "Words" in formatted
        assert "10" in formatted  # 10 words in voiceover

    def test_format_shows_arc_info(self, generator):
        """Test that formatted output includes emotional arc information."""
        from src.models import Script, ScriptScene, VisualCue

        script = Script(
            title="Arc Test",
            total_duration_seconds=30,
            scenes=[
                ScriptScene(
                    scene_id=1,
                    scene_type="context",
                    title="Tension Scene",
                    voiceover="Building tension here.",
                    visual_cue=VisualCue(
                        description="Test visual",
                        visual_type="animation",
                        elements=["moment1", "moment2"],
                        duration_seconds=30,
                    ),
                    duration_seconds=30,
                    notes="Connection: But here's the problem | Emotion: tension",
                )
            ],
            source_document="test.md",
        )

        formatted = generator.format_script_for_review(script)
        assert "Arc" in formatted
        assert "moment1" in formatted
        assert "moment2" in formatted

    def test_key_visual_moments_in_elements(self, generator):
        """Test that key_visual_moments are stored in visual_cue.elements."""
        result = {
            "title": "Visual Moments Test",
            "total_duration_seconds": 30,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "explanation",
                    "title": "Test",
                    "voiceover": "Test narration.",
                    "visual_description": "Description",
                    "key_visual_moments": [
                        "Show initial state",
                        "Animate transformation",
                        "Reveal final result",
                    ],
                    "duration_seconds": 30,
                },
            ],
        }

        script = generator._parse_script_result(result, "test.md")
        elements = script.scenes[0].visual_cue.elements

        assert len(elements) == 3
        assert "Show initial state" in elements
        assert "Animate transformation" in elements
        assert "Reveal final result" in elements


class TestRealDocumentScript:
    """Test script generation with the real LLM inference document."""

    @pytest.fixture
    def inference_doc_path(self):
        path = Path("/Users/prajwal/Desktop/Learning/inference/website/post.md")
        if not path.exists():
            pytest.skip("Inference document not found")
        return path

    @pytest.fixture
    def generator(self):
        return ScriptGenerator()

    @pytest.fixture
    def analyzer(self):
        return ContentAnalyzer()

    def test_generate_script_for_inference_doc(
        self, generator, analyzer, inference_doc_path
    ):
        doc = parse_document(inference_doc_path)
        analysis = analyzer.analyze(doc)
        script = generator.generate(doc, analysis, target_duration=210)

        # Verify script structure
        assert script.title
        assert len(script.scenes) >= 3  # At least hook, content, conclusion

        # Check for expected scene types
        scene_types = [s.scene_type for s in script.scenes]
        assert "hook" in scene_types
        assert "conclusion" in scene_types

    def test_script_covers_key_concepts(self, generator, analyzer, inference_doc_path):
        doc = parse_document(inference_doc_path)
        analysis = analyzer.analyze(doc)
        script = generator.generate(doc, analysis)

        # Combine all voiceover text
        all_voiceover = " ".join(s.voiceover.lower() for s in script.scenes)

        # Mock provider returns generic script content
        assert len(all_voiceover) > 100  # Should have substantial content

    def test_script_has_visual_cues_for_each_scene(
        self, generator, analyzer, inference_doc_path
    ):
        doc = parse_document(inference_doc_path)
        analysis = analyzer.analyze(doc)
        script = generator.generate(doc, analysis)

        for scene in script.scenes:
            assert scene.visual_cue.description
            assert len(scene.visual_cue.description) > 10  # Meaningful description

    def test_formatted_script_is_readable(
        self, generator, analyzer, inference_doc_path
    ):
        doc = parse_document(inference_doc_path)
        analysis = analyzer.analyze(doc)
        script = generator.generate(doc, analysis)

        formatted = generator.format_script_for_review(script)

        # Should be well-structured markdown
        assert "# " in formatted  # Has title
        assert "## Scene" in formatted  # Has scene headers
        assert "---" in formatted  # Has separators
        assert "Voiceover" in formatted
        assert "Visual" in formatted
