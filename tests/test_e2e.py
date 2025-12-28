"""End-to-end tests for the video explainer pipeline."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.audio.tts import MockTTS
from src.config import Config
from src.ingestion import parse_document
from src.pipeline import VideoPipeline
from src.script import ScriptGenerator
from src.understanding import ContentAnalyzer


class TestEndToEndPipeline:
    """End-to-end tests for the complete video generation pipeline."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    @pytest.fixture
    def inference_doc_path(self):
        """Get the path to the inference document."""
        path = Path("/Users/prajwal/Desktop/Learning/inference/website/post.md")
        if not path.exists():
            pytest.skip("Inference document not found")
        return path

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create output directories."""
        (tmp_path / "scripts").mkdir()
        (tmp_path / "audio").mkdir()
        (tmp_path / "video").mkdir()
        return tmp_path

    def test_full_pipeline_mock(self, config, inference_doc_path, output_dir):
        """Test the complete pipeline from document to script to audio."""
        # Step 1: Parse the document
        document = parse_document(inference_doc_path)
        assert document.title == "Scaling LLM Inference to Millions of Users"
        assert len(document.sections) > 5

        # Step 2: Analyze the content
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        assert analysis.core_thesis
        assert len(analysis.key_concepts) > 0
        assert any("prefill" in c.name.lower() for c in analysis.key_concepts)

        # Step 3: Generate the script
        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis, target_duration=210)

        assert script.title
        assert len(script.scenes) >= 3
        assert any(s.scene_type == "hook" for s in script.scenes)
        assert any(s.scene_type == "conclusion" for s in script.scenes)

        # Step 4: Save the script
        script_path = output_dir / "scripts" / "test_script.json"
        script_gen.save_script(script, str(script_path))

        assert script_path.exists()
        assert script_path.with_suffix(".md").exists()

        # Verify script can be loaded back
        loaded_script = ScriptGenerator.load_script(str(script_path))
        assert loaded_script.title == script.title
        assert len(loaded_script.scenes) == len(script.scenes)

        # Step 5: Generate audio for each scene (mock)
        tts = MockTTS(config.tts)
        audio_files = []

        for scene in script.scenes:
            audio_path = output_dir / "audio" / f"scene_{scene.scene_id}.mp3"
            result = tts.generate(scene.voiceover, audio_path)
            audio_files.append(result)
            assert result.exists()

        assert len(audio_files) == len(script.scenes)

    def test_pipeline_produces_reviewable_output(self, config, inference_doc_path, output_dir):
        """Test that the pipeline produces output suitable for human review."""
        # Parse and analyze
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        # Generate script
        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis)

        # Format for review
        review_text = script_gen.format_script_for_review(script)

        # Check review format
        assert "# " in review_text  # Has markdown headers
        assert "Scene " in review_text
        assert "Voiceover" in review_text
        assert "Visual" in review_text

        # Each scene should be represented
        for scene in script.scenes:
            assert f"Scene {scene.scene_id}" in review_text

    def test_pipeline_respects_section_limits(self, config, inference_doc_path):
        """Test that we can analyze specific sections of the document."""
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)

        # Analyze only "Two Phases" through "KV Cache"
        analysis = analyzer.analyze_sections(
            document,
            start_heading="Two Phases",
            end_heading="Enter vLLM",
        )

        assert analysis.core_thesis
        # Should focus on prefill/decode concepts
        concept_names = [c.name.lower() for c in analysis.key_concepts]
        assert any("prefill" in name or "decode" in name for name in concept_names)

    def test_script_scenes_have_timing(self, config, inference_doc_path):
        """Test that script scenes have proper timing information."""
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis, target_duration=180)

        # All scenes should have positive duration
        for scene in script.scenes:
            assert scene.duration_seconds > 0
            assert scene.visual_cue.duration_seconds > 0

        # Total duration should match sum of scenes
        total = sum(s.duration_seconds for s in script.scenes)
        assert script.total_duration_seconds == total

    def test_visual_cues_are_actionable(self, config, inference_doc_path):
        """Test that visual cues contain actionable information."""
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis)

        for scene in script.scenes:
            cue = scene.visual_cue

            # Each cue should have a type and description
            assert cue.visual_type in ["animation", "diagram", "code", "equation", "image"]
            assert len(cue.description) > 20  # Meaningful description

            # Most cues should have elements
            # (some simple scenes might not)


class TestPipelineErrorHandling:
    """Test error handling in the pipeline."""

    @pytest.fixture
    def config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    def test_handles_empty_document(self, config):
        """Test handling of empty document."""
        document = parse_document("# Empty\n\nNo content here.")
        analyzer = ContentAnalyzer(config)

        # Should still produce some analysis
        analysis = analyzer.analyze(document)
        assert analysis is not None

    def test_handles_short_content(self, config):
        """Test handling of very short content."""
        document = parse_document("# Title\n\nJust one sentence about a topic.")
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis, target_duration=60)

        # Should still produce a valid script
        assert script.title
        assert len(script.scenes) > 0


class TestPipelineOutputFormats:
    """Test that pipeline outputs are in correct formats."""

    @pytest.fixture
    def config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def sample_script(self, config, sample_markdown):
        document = parse_document(sample_markdown)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)
        script_gen = ScriptGenerator(config)
        return script_gen.generate(document, analysis)

    def test_script_json_format(self, sample_script, tmp_path):
        """Test that saved scripts are valid JSON."""
        script_gen = ScriptGenerator()
        script_path = tmp_path / "script.json"
        script_gen.save_script(sample_script, str(script_path))

        # Should be valid JSON
        with open(script_path) as f:
            data = json.load(f)

        assert "title" in data
        assert "scenes" in data
        assert isinstance(data["scenes"], list)

    def test_script_markdown_format(self, sample_script, tmp_path):
        """Test that saved scripts have valid markdown review format."""
        script_gen = ScriptGenerator()
        script_path = tmp_path / "script.json"
        script_gen.save_script(sample_script, str(script_path))

        md_path = script_path.with_suffix(".md")
        assert md_path.exists()

        content = md_path.read_text()

        # Should be valid markdown
        assert content.startswith("# ")
        assert "---" in content


class TestFullVideoPipeline:
    """Test the complete VideoPipeline with mock providers.

    These tests ensure the pipeline doesn't regress after code changes.
    Uses mock LLM and TTS to avoid API costs during testing.
    """

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
        """Create mock config for testing."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    def test_pipeline_quick_test(self, config, mock_subprocess, tmp_path):
        """Test pipeline quick_test completes all stages."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        result = pipeline.quick_test()

        # All stages should complete
        assert "parsing" in result.stages_completed
        assert "analysis" in result.stages_completed
        assert "script" in result.stages_completed
        assert "audio" in result.stages_completed
        assert "animation" in result.stages_completed
        assert "composition" in result.stages_completed
        assert result.success

    def test_pipeline_from_document(self, config, mock_subprocess, tmp_path):
        """Test pipeline generates video from document."""
        # Create test document
        doc_path = tmp_path / "test_doc.md"
        doc_path.write_text("""# Test Technical Document

## Introduction

This document explains an important technical concept.

## Key Concept

Here is the main idea with detailed explanation.
The concept involves multiple components working together.

## Conclusion

In summary, this is how the concept works.
""")

        pipeline = VideoPipeline(config=config, output_dir=tmp_path)
        result = pipeline.generate_from_document(doc_path, target_duration=60)

        assert result.success
        assert result.output_path is not None
        assert "parsing" in result.stages_completed
        assert "analysis" in result.stages_completed
        assert "script" in result.stages_completed
        assert result.metadata.get("llm_provider") == "mock"
        assert result.metadata.get("tts_provider") == "mock"

    def test_pipeline_progress_callback(self, config, mock_subprocess, tmp_path):
        """Test that progress callbacks are fired."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        progress_updates = []
        def on_progress(stage: str, progress: float):
            progress_updates.append((stage, progress))

        pipeline.set_progress_callback(on_progress)
        result = pipeline.quick_test()

        # Should have progress updates for all stages
        stages_with_progress = {stage for stage, _ in progress_updates}
        assert "parsing" in stages_with_progress
        assert "analysis" in stages_with_progress
        assert "script" in stages_with_progress
        assert "audio" in stages_with_progress

    def test_pipeline_saves_script(self, config, mock_subprocess, tmp_path):
        """Test that pipeline saves script for review."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)
        result = pipeline.quick_test()

        # Script should be saved
        script_path = result.metadata.get("script_path")
        assert script_path is not None
        assert Path(script_path).exists()

        # Should be valid JSON
        with open(script_path) as f:
            script_data = json.load(f)
        assert "title" in script_data
        assert "scenes" in script_data

    def test_pipeline_handles_errors_gracefully(self, config, tmp_path):
        """Test that pipeline handles errors and reports them."""
        # Don't mock subprocess - let it fail on missing FFmpeg commands
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        # Create a document that will parse but cause issues
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Test\n\nContent")

        # The pipeline should catch errors and return a failed result
        # rather than raising an exception
        result = pipeline.generate_from_document(doc_path)

        # Should have at least started
        assert len(result.stages_completed) >= 1
