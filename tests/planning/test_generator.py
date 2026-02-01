"""Tests for PlanGenerator class."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Config
from src.ingestion import parse_document
from src.models import ContentAnalysis, Concept, PlannedScene, VideoPlan
from src.planning.generator import PlanGenerator


class TestPlanGenerator:
    """Tests for the PlanGenerator class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def generator(self, mock_config):
        """Create a PlanGenerator with mock config."""
        return PlanGenerator(config=mock_config)

    @pytest.fixture
    def sample_analysis(self):
        """Create a sample content analysis."""
        return ContentAnalysis(
            core_thesis="Testing is essential for software quality",
            key_concepts=[
                Concept(
                    name="Unit Testing",
                    explanation="Testing individual components in isolation",
                    complexity=3,
                    prerequisites=["basic programming"],
                    analogies=["Like checking ingredients before cooking"],
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
        """Create a sample parsed document."""
        return parse_document(sample_markdown)

    def test_generate_returns_video_plan(self, generator, sample_document, sample_analysis):
        """Test that generate returns a VideoPlan."""
        plan = generator.generate(sample_document, sample_analysis)

        assert isinstance(plan, VideoPlan)

    def test_plan_has_required_fields(self, generator, sample_document, sample_analysis):
        """Test that generated plan has all required fields."""
        plan = generator.generate(sample_document, sample_analysis)

        assert plan.title
        assert plan.central_question
        assert plan.target_audience
        assert plan.estimated_total_duration_seconds > 0
        assert plan.core_thesis
        assert isinstance(plan.key_concepts, list)
        assert 1 <= plan.complexity_score <= 10
        assert len(plan.scenes) > 0
        assert plan.visual_style
        assert plan.source_document

    def test_plan_has_valid_scenes(self, generator, sample_document, sample_analysis):
        """Test that generated plan has valid scenes."""
        plan = generator.generate(sample_document, sample_analysis)

        for scene in plan.scenes:
            assert isinstance(scene, PlannedScene)
            assert scene.scene_number > 0
            assert scene.scene_type in ["hook", "context", "explanation", "insight", "conclusion"]
            assert scene.title
            assert scene.concept_to_cover
            assert scene.visual_approach
            assert scene.estimated_duration_seconds > 0

    def test_plan_status_is_draft(self, generator, sample_document, sample_analysis):
        """Test that new plans start as draft."""
        plan = generator.generate(sample_document, sample_analysis)

        assert plan.status == "draft"
        assert plan.approved_at is None

    def test_plan_created_at_is_set(self, generator, sample_document, sample_analysis):
        """Test that created_at timestamp is set."""
        plan = generator.generate(sample_document, sample_analysis)

        assert plan.created_at
        # Should be a valid ISO format timestamp
        from datetime import datetime
        datetime.fromisoformat(plan.created_at)

    def test_custom_target_duration(self, generator, sample_document, sample_analysis):
        """Test generating plan with custom duration."""
        plan = generator.generate(sample_document, sample_analysis, target_duration=300)

        # Plan should exist (mock doesn't strictly respect duration)
        assert isinstance(plan, VideoPlan)

    def test_refine_updates_plan(self, generator, sample_document, sample_analysis):
        """Test that refine updates the plan based on feedback."""
        original_plan = generator.generate(sample_document, sample_analysis)
        original_title = original_plan.title

        refined_plan = generator.refine(original_plan, "Make the title more engaging")

        assert isinstance(refined_plan, VideoPlan)
        # Created_at should be preserved
        assert refined_plan.created_at == original_plan.created_at
        # User notes should include feedback
        assert "Make the title more engaging" in refined_plan.user_notes

    def test_refine_preserves_created_at(self, generator, sample_document, sample_analysis):
        """Test that refinement preserves the original created_at."""
        original_plan = generator.generate(sample_document, sample_analysis)
        original_created_at = original_plan.created_at

        refined_plan = generator.refine(original_plan, "Add more detail to scene 2")

        assert refined_plan.created_at == original_created_at

    def test_refine_accumulates_user_notes(self, generator, sample_document, sample_analysis):
        """Test that multiple refinements accumulate user notes."""
        plan = generator.generate(sample_document, sample_analysis)
        plan.user_notes = "Initial note"

        refined_plan = generator.refine(plan, "Second feedback")

        assert "Initial note" in refined_plan.user_notes
        assert "Second feedback" in refined_plan.user_notes


class TestPlanGeneratorFormatting:
    """Tests for plan formatting and display."""

    @pytest.fixture
    def mock_config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def generator(self, mock_config):
        return PlanGenerator(config=mock_config)

    @pytest.fixture
    def sample_plan(self):
        """Create a sample plan for testing formatting."""
        scenes = [
            PlannedScene(
                scene_number=1,
                scene_type="hook",
                title="The Challenge",
                concept_to_cover="The problem",
                visual_approach="Dramatic visualization",
                ascii_visual="┌───────┐\n│ HOOK  │\n└───────┘",
                estimated_duration_seconds=45.0,
                key_points=["Point 1", "Point 2"],
            ),
            PlannedScene(
                scene_number=2,
                scene_type="explanation",
                title="How It Works",
                concept_to_cover="Core mechanism",
                visual_approach="Step-by-step animation",
                ascii_visual="┌────────────┐\n│ EXPLAIN    │\n└────────────┘",
                estimated_duration_seconds=90.0,
                key_points=["Explain 1"],
            ),
        ]

        return VideoPlan(
            status="draft",
            created_at="2024-01-15T10:00:00",
            title="Test Video Plan",
            central_question="How does this work?",
            target_audience="Developers",
            estimated_total_duration_seconds=135.0,
            core_thesis="This is the main thesis",
            key_concepts=["Concept A", "Concept B", "Concept C"],
            complexity_score=6,
            scenes=scenes,
            visual_style="Clean with animations",
            source_document="test.md",
        )

    def test_format_for_display_includes_title(self, generator, sample_plan):
        """Test that formatted output includes title."""
        output = generator.format_for_display(sample_plan)

        assert "VIDEO PLAN:" in output
        assert sample_plan.title in output

    def test_format_for_display_includes_metadata(self, generator, sample_plan):
        """Test that formatted output includes metadata."""
        output = generator.format_for_display(sample_plan)

        assert "Central Question:" in output
        assert sample_plan.central_question in output
        assert "Target Audience:" in output
        assert "Duration:" in output
        assert "Complexity:" in output

    def test_format_for_display_includes_scenes(self, generator, sample_plan):
        """Test that formatted output includes all scenes."""
        output = generator.format_for_display(sample_plan)

        assert "SCENES:" in output
        assert "[HOOK]" in output
        assert "[EXPLANATION]" in output
        assert "The Challenge" in output
        assert "How It Works" in output

    def test_format_for_display_includes_ascii_art(self, generator, sample_plan):
        """Test that formatted output includes ASCII art."""
        output = generator.format_for_display(sample_plan)

        # Check for ASCII art elements
        assert "HOOK" in output
        assert "EXPLAIN" in output

    def test_format_for_display_includes_commands(self, generator, sample_plan):
        """Test that formatted output includes command hints."""
        output = generator.format_for_display(sample_plan)

        assert "Commands:" in output
        assert "[a]pprove" in output
        assert "[r]efine" in output
        assert "[s]ave" in output
        assert "[q]uit" in output


class TestPlanGeneratorPersistence:
    """Tests for plan save/load functionality."""

    @pytest.fixture
    def mock_config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def generator(self, mock_config):
        return PlanGenerator(config=mock_config)

    @pytest.fixture
    def sample_plan(self):
        scenes = [
            PlannedScene(
                scene_number=1,
                scene_type="hook",
                title="Test Hook",
                concept_to_cover="Test concept",
                visual_approach="Test approach",
                ascii_visual="[TEST]",
                estimated_duration_seconds=30.0,
                key_points=["Point 1"],
            ),
        ]

        return VideoPlan(
            status="draft",
            created_at="2024-01-15T10:00:00",
            title="Test Plan",
            central_question="Test?",
            target_audience="Testers",
            estimated_total_duration_seconds=30.0,
            core_thesis="Test thesis",
            key_concepts=["A", "B"],
            complexity_score=5,
            scenes=scenes,
            visual_style="Test style",
            source_document="test.md",
            user_notes="Test notes",
        )

    def test_save_plan_creates_files(self, generator, sample_plan, tmp_path):
        """Test that save_plan creates both JSON and MD files."""
        json_path, md_path = generator.save_plan(sample_plan, tmp_path)

        assert json_path.exists()
        assert md_path.exists()
        assert json_path.name == "plan.json"
        assert md_path.name == "plan.md"

    def test_save_plan_json_valid(self, generator, sample_plan, tmp_path):
        """Test that saved JSON is valid and complete."""
        json_path, _ = generator.save_plan(sample_plan, tmp_path)

        with open(json_path) as f:
            data = json.load(f)

        assert data["title"] == sample_plan.title
        assert data["status"] == "draft"
        assert len(data["scenes"]) == 1
        assert data["complexity_score"] == 5

    def test_save_plan_creates_directory(self, generator, sample_plan, tmp_path):
        """Test that save_plan creates directory if needed."""
        plan_dir = tmp_path / "nested" / "plan"
        json_path, md_path = generator.save_plan(sample_plan, plan_dir)

        assert plan_dir.exists()
        assert json_path.exists()

    def test_load_plan(self, generator, sample_plan, tmp_path):
        """Test loading a saved plan."""
        json_path, _ = generator.save_plan(sample_plan, tmp_path)

        loaded_plan = PlanGenerator.load_plan(json_path)

        assert isinstance(loaded_plan, VideoPlan)
        assert loaded_plan.title == sample_plan.title
        assert loaded_plan.status == sample_plan.status
        assert len(loaded_plan.scenes) == len(sample_plan.scenes)
        assert loaded_plan.complexity_score == sample_plan.complexity_score

    def test_load_plan_preserves_all_fields(self, generator, sample_plan, tmp_path):
        """Test that load preserves all plan fields."""
        sample_plan.status = "approved"
        sample_plan.approved_at = "2024-01-15T12:00:00"

        json_path, _ = generator.save_plan(sample_plan, tmp_path)
        loaded_plan = PlanGenerator.load_plan(json_path)

        assert loaded_plan.status == "approved"
        assert loaded_plan.approved_at == "2024-01-15T12:00:00"
        assert loaded_plan.user_notes == sample_plan.user_notes
        assert loaded_plan.key_concepts == sample_plan.key_concepts
