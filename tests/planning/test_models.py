"""Tests for planning-related data models."""

import pytest
from pydantic import ValidationError

from src.models import PlannedScene, VideoPlan


class TestPlannedScene:
    """Tests for PlannedScene model."""

    def test_create_valid_scene(self):
        """Test creating a valid planned scene."""
        scene = PlannedScene(
            scene_number=1,
            scene_type="hook",
            title="The Challenge",
            concept_to_cover="The problem that needs solving",
            visual_approach="Show a dramatic visualization",
            ascii_visual="┌───────────┐\n│  VISUAL  │\n└───────────┘",
            estimated_duration_seconds=45.0,
            key_points=["Hook the viewer", "Establish scale"],
        )

        assert scene.scene_number == 1
        assert scene.scene_type == "hook"
        assert scene.title == "The Challenge"
        assert scene.estimated_duration_seconds == 45.0
        assert len(scene.key_points) == 2

    def test_scene_default_key_points(self):
        """Test that key_points defaults to empty list."""
        scene = PlannedScene(
            scene_number=1,
            scene_type="explanation",
            title="How It Works",
            concept_to_cover="Core mechanism",
            visual_approach="Step by step animation",
            ascii_visual="",
            estimated_duration_seconds=60.0,
        )

        assert scene.key_points == []

    def test_scene_with_all_scene_types(self):
        """Test all valid scene types."""
        scene_types = ["hook", "context", "explanation", "insight", "conclusion"]

        for scene_type in scene_types:
            scene = PlannedScene(
                scene_number=1,
                scene_type=scene_type,
                title=f"Test {scene_type}",
                concept_to_cover="Test concept",
                visual_approach="Test approach",
                ascii_visual="",
                estimated_duration_seconds=30.0,
            )
            assert scene.scene_type == scene_type


class TestVideoPlan:
    """Tests for VideoPlan model."""

    @pytest.fixture
    def sample_scenes(self):
        """Create sample planned scenes."""
        return [
            PlannedScene(
                scene_number=1,
                scene_type="hook",
                title="The Challenge",
                concept_to_cover="The problem",
                visual_approach="Dramatic visualization",
                ascii_visual="[ASCII ART]",
                estimated_duration_seconds=45.0,
                key_points=["Hook point 1"],
            ),
            PlannedScene(
                scene_number=2,
                scene_type="explanation",
                title="How It Works",
                concept_to_cover="Core mechanism",
                visual_approach="Step-by-step",
                ascii_visual="[ASCII ART 2]",
                estimated_duration_seconds=90.0,
                key_points=["Explanation point 1", "Explanation point 2"],
            ),
            PlannedScene(
                scene_number=3,
                scene_type="conclusion",
                title="Wrap Up",
                concept_to_cover="Summary",
                visual_approach="Recap animation",
                ascii_visual="[ASCII ART 3]",
                estimated_duration_seconds=45.0,
                key_points=["Conclusion point"],
            ),
        ]

    def test_create_valid_plan(self, sample_scenes):
        """Test creating a valid video plan."""
        plan = VideoPlan(
            status="draft",
            created_at="2024-01-15T10:00:00",
            title="Understanding the Core Concept",
            central_question="How does this work?",
            target_audience="Technical professionals",
            estimated_total_duration_seconds=180.0,
            core_thesis="This concept transforms everything",
            key_concepts=["Concept A", "Concept B"],
            complexity_score=6,
            scenes=sample_scenes,
            visual_style="Clean diagrams with animations",
            source_document="input/doc.md",
        )

        assert plan.status == "draft"
        assert plan.title == "Understanding the Core Concept"
        assert len(plan.scenes) == 3
        assert plan.complexity_score == 6
        assert plan.approved_at is None

    def test_plan_defaults(self, sample_scenes):
        """Test default values for optional fields."""
        plan = VideoPlan(
            created_at="2024-01-15T10:00:00",
            title="Test Plan",
            central_question="Test question?",
            target_audience="Developers",
            estimated_total_duration_seconds=120.0,
            core_thesis="Test thesis",
            key_concepts=["A", "B"],
            complexity_score=5,
            scenes=sample_scenes,
            visual_style="Simple",
            source_document="test.md",
        )

        assert plan.status == "draft"
        assert plan.approved_at is None
        assert plan.user_notes == ""

    def test_plan_complexity_score_validation(self, sample_scenes):
        """Test that complexity score must be between 1-10."""
        # Valid scores
        for score in [1, 5, 10]:
            plan = VideoPlan(
                created_at="2024-01-15T10:00:00",
                title="Test",
                central_question="?",
                target_audience="All",
                estimated_total_duration_seconds=60.0,
                core_thesis="Test",
                key_concepts=[],
                complexity_score=score,
                scenes=sample_scenes,
                visual_style="Test",
                source_document="test.md",
            )
            assert plan.complexity_score == score

        # Invalid scores
        with pytest.raises(ValidationError):
            VideoPlan(
                created_at="2024-01-15T10:00:00",
                title="Test",
                central_question="?",
                target_audience="All",
                estimated_total_duration_seconds=60.0,
                core_thesis="Test",
                key_concepts=[],
                complexity_score=0,  # Too low
                scenes=sample_scenes,
                visual_style="Test",
                source_document="test.md",
            )

        with pytest.raises(ValidationError):
            VideoPlan(
                created_at="2024-01-15T10:00:00",
                title="Test",
                central_question="?",
                target_audience="All",
                estimated_total_duration_seconds=60.0,
                core_thesis="Test",
                key_concepts=[],
                complexity_score=11,  # Too high
                scenes=sample_scenes,
                visual_style="Test",
                source_document="test.md",
            )

    def test_plan_approval(self, sample_scenes):
        """Test plan approval workflow."""
        plan = VideoPlan(
            created_at="2024-01-15T10:00:00",
            title="Test Plan",
            central_question="?",
            target_audience="All",
            estimated_total_duration_seconds=60.0,
            core_thesis="Test",
            key_concepts=[],
            complexity_score=5,
            scenes=sample_scenes,
            visual_style="Test",
            source_document="test.md",
        )

        assert plan.status == "draft"
        assert plan.approved_at is None

        # Simulate approval
        plan.status = "approved"
        plan.approved_at = "2024-01-15T12:00:00"

        assert plan.status == "approved"
        assert plan.approved_at == "2024-01-15T12:00:00"

    def test_plan_serialization(self, sample_scenes):
        """Test plan serialization to dict/JSON."""
        plan = VideoPlan(
            created_at="2024-01-15T10:00:00",
            title="Test Plan",
            central_question="Test?",
            target_audience="Developers",
            estimated_total_duration_seconds=180.0,
            core_thesis="Test thesis",
            key_concepts=["A", "B", "C"],
            complexity_score=7,
            scenes=sample_scenes,
            visual_style="Modern",
            source_document="doc.md",
            user_notes="Some notes",
        )

        # Convert to dict
        data = plan.model_dump()

        assert data["title"] == "Test Plan"
        assert data["status"] == "draft"
        assert len(data["scenes"]) == 3
        assert data["scenes"][0]["scene_type"] == "hook"
        assert data["key_concepts"] == ["A", "B", "C"]

    def test_plan_from_dict(self, sample_scenes):
        """Test creating plan from dictionary."""
        data = {
            "status": "approved",
            "created_at": "2024-01-15T10:00:00",
            "approved_at": "2024-01-15T11:00:00",
            "title": "From Dict Plan",
            "central_question": "Test?",
            "target_audience": "All",
            "estimated_total_duration_seconds": 120.0,
            "core_thesis": "Test",
            "key_concepts": ["X", "Y"],
            "complexity_score": 4,
            "scenes": [s.model_dump() for s in sample_scenes],
            "visual_style": "Clean",
            "source_document": "test.md",
            "user_notes": "Created from dict",
        }

        plan = VideoPlan(**data)

        assert plan.status == "approved"
        assert plan.approved_at == "2024-01-15T11:00:00"
        assert plan.title == "From Dict Plan"
        assert len(plan.scenes) == 3
