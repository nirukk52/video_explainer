"""Tests for the ScriptAnalyzer (Phase 1: Gap Analysis)."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import LLMConfig
from src.refine.models import (
    ConceptDepth,
    ConceptCoverage,
    GapAnalysisResult,
    NarrativeGap,
    SourceConcept,
    SuggestedScene,
)
from src.refine.script.analyzer import (
    ScriptAnalyzer,
    CONCEPT_EXTRACTION_PROMPT,
    GAP_ANALYSIS_PROMPT,
)


class TestSourceConcept:
    """Tests for SourceConcept dataclass."""

    def test_creation(self):
        """Test creating a SourceConcept."""
        concept = SourceConcept(
            name="Policy Gradient",
            description="Method for optimizing policies",
            importance="high",
            prerequisites=["neural networks", "calculus"],
            section_reference="Section 3",
        )
        assert concept.name == "Policy Gradient"
        assert concept.importance == "high"
        assert len(concept.prerequisites) == 2

    def test_to_dict(self):
        """Test SourceConcept serialization."""
        concept = SourceConcept(
            name="Test",
            description="Test description",
            importance="medium",
        )
        data = concept.to_dict()
        assert data["name"] == "Test"
        assert data["importance"] == "medium"
        assert data["prerequisites"] == []

    def test_from_dict(self):
        """Test SourceConcept deserialization."""
        data = {
            "name": "Test",
            "description": "Description",
            "importance": "critical",
            "prerequisites": ["prereq1"],
            "section_reference": "Intro",
        }
        concept = SourceConcept.from_dict(data)
        assert concept.name == "Test"
        assert concept.importance == "critical"
        assert concept.prerequisites == ["prereq1"]


class TestConceptCoverage:
    """Tests for ConceptCoverage dataclass."""

    def test_is_covered(self):
        """Test is_covered property."""
        concept = SourceConcept(name="Test", description="")

        # Not covered
        coverage = ConceptCoverage(
            concept=concept,
            depth=ConceptDepth.NOT_COVERED,
        )
        assert not coverage.is_covered

        # Covered
        coverage = ConceptCoverage(
            concept=concept,
            depth=ConceptDepth.MENTIONED,
        )
        assert coverage.is_covered

    def test_needs_improvement_critical_concept(self):
        """Test needs_improvement for critical concepts."""
        concept = SourceConcept(name="Test", description="", importance="critical")

        # Critical + not covered = needs improvement
        coverage = ConceptCoverage(concept=concept, depth=ConceptDepth.NOT_COVERED)
        assert coverage.needs_improvement

        # Critical + only mentioned = needs improvement
        coverage = ConceptCoverage(concept=concept, depth=ConceptDepth.MENTIONED)
        assert coverage.needs_improvement

        # Critical + explained = OK
        coverage = ConceptCoverage(concept=concept, depth=ConceptDepth.EXPLAINED)
        assert not coverage.needs_improvement

    def test_needs_improvement_low_importance(self):
        """Test needs_improvement for low importance concepts."""
        concept = SourceConcept(name="Test", description="", importance="low")

        # Low importance + mentioned = OK
        coverage = ConceptCoverage(concept=concept, depth=ConceptDepth.MENTIONED)
        assert not coverage.needs_improvement

        # Low importance + not covered = needs improvement
        coverage = ConceptCoverage(concept=concept, depth=ConceptDepth.NOT_COVERED)
        assert coverage.needs_improvement


class TestNarrativeGap:
    """Tests for NarrativeGap dataclass."""

    def test_creation(self):
        """Test creating a NarrativeGap."""
        gap = NarrativeGap(
            from_scene_id="scene5",
            from_scene_title="The REINFORCE Algorithm",
            to_scene_id="scene6",
            to_scene_title="The Emergence",
            gap_description="Unexplained jump from high variance to working solution",
            severity="high",
            suggested_bridge="Add scene explaining advantage functions",
        )
        assert gap.severity == "high"
        assert "advantage functions" in gap.suggested_bridge

    def test_to_dict_from_dict(self):
        """Test serialization roundtrip."""
        gap = NarrativeGap(
            from_scene_id="s1",
            from_scene_title="Scene 1",
            to_scene_id="s2",
            to_scene_title="Scene 2",
            gap_description="Gap",
            severity="medium",
        )
        data = gap.to_dict()
        restored = NarrativeGap.from_dict(data)
        assert restored.from_scene_id == gap.from_scene_id
        assert restored.severity == gap.severity


class TestSuggestedScene:
    """Tests for SuggestedScene dataclass."""

    def test_creation(self):
        """Test creating a SuggestedScene."""
        scene = SuggestedScene(
            title="Better Than Average",
            reason="Explain advantage functions to bridge the gap",
            suggested_position=11,
            concepts_addressed=["advantage functions", "variance reduction"],
            suggested_narration="The solution is elegant...",
        )
        assert scene.suggested_position == 11
        assert len(scene.concepts_addressed) == 2


class TestGapAnalysisResult:
    """Tests for GapAnalysisResult dataclass."""

    def test_missing_concepts(self):
        """Test missing_concepts property."""
        concept1 = SourceConcept(name="Covered", description="")
        concept2 = SourceConcept(name="Missing", description="")

        result = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            concepts=[
                ConceptCoverage(concept=concept1, depth=ConceptDepth.EXPLAINED),
                ConceptCoverage(concept=concept2, depth=ConceptDepth.NOT_COVERED),
            ],
        )

        assert result.missing_concepts == ["Missing"]

    def test_shallow_concepts(self):
        """Test shallow_concepts property."""
        concept1 = SourceConcept(name="Deep", description="", importance="high")
        concept2 = SourceConcept(name="Shallow", description="", importance="high")

        result = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            concepts=[
                ConceptCoverage(concept=concept1, depth=ConceptDepth.DEEP_DIVE),
                ConceptCoverage(concept=concept2, depth=ConceptDepth.MENTIONED),
            ],
        )

        assert result.shallow_concepts == ["Shallow"]

    def test_has_critical_gaps(self):
        """Test has_critical_gaps property."""
        concept = SourceConcept(name="Critical", description="", importance="critical")

        # Critical concept missing = critical gap
        result = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            concepts=[
                ConceptCoverage(concept=concept, depth=ConceptDepth.NOT_COVERED),
            ],
        )
        assert result.has_critical_gaps

        # High severity narrative gap = critical gap
        result = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            narrative_gaps=[
                NarrativeGap(
                    from_scene_id="s1",
                    from_scene_title="S1",
                    to_scene_id="s2",
                    to_scene_title="S2",
                    gap_description="Gap",
                    severity="high",
                ),
            ],
        )
        assert result.has_critical_gaps

    def test_to_dict_includes_computed_properties(self):
        """Test that to_dict includes computed properties."""
        concept = SourceConcept(name="Missing", description="", importance="critical")
        result = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            concepts=[
                ConceptCoverage(concept=concept, depth=ConceptDepth.NOT_COVERED),
            ],
        )

        data = result.to_dict()
        assert "missing_concepts" in data
        assert "shallow_concepts" in data
        assert "has_critical_gaps" in data


class TestScriptAnalyzer:
    """Tests for ScriptAnalyzer class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        mock = MagicMock()
        mock.generate_json.return_value = {}
        return mock

    @pytest.fixture
    def project_with_source(self, temp_project_dir, sample_narrations):
        """Create a project with source material and narrations."""
        # Create source material
        source_path = temp_project_dir / "input" / "source.md"
        source_path.write_text("""
# How AI Learned to Think

This document explains reinforcement learning for reasoning models.

## Key Concepts

### Chain-of-Thought Prompting
Showing AI step-by-step reasoning improves performance.

### Policy Gradients
The method used to train reasoning models.

### Advantage Functions
A technique to reduce variance in training.
""")

        # Write narrations
        narrations_path = temp_project_dir / "narration" / "narrations.json"
        with open(narrations_path, "w") as f:
            json.dump(sample_narrations, f)

        from src.project import load_project
        return load_project(temp_project_dir)

    def test_init_with_default_provider(self, project_with_source):
        """Test initialization creates ClaudeCodeLLMProvider by default."""
        # This will try to create ClaudeCodeLLMProvider, but we just test it doesn't crash
        with patch("src.refine.script.analyzer.ClaudeCodeLLMProvider"):
            analyzer = ScriptAnalyzer(project=project_with_source)
            assert analyzer.project == project_with_source

    def test_init_with_custom_provider(self, project_with_source, mock_llm):
        """Test initialization with custom LLM provider."""
        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )
        assert analyzer.llm == mock_llm

    def test_load_source_material(self, project_with_source, mock_llm):
        """Test loading source material from input directory."""
        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )
        path, content = analyzer._load_source_material()
        assert path.name == "source.md"
        assert "Chain-of-Thought" in content

    def test_load_source_material_not_found(self, temp_project_dir, mock_llm):
        """Test loading source material when none exists."""
        # Create minimal project without source
        config = {"id": "empty", "title": "Empty"}
        with open(temp_project_dir / "config.json", "w") as f:
            json.dump(config, f)

        from src.project import load_project
        project = load_project(temp_project_dir)

        analyzer = ScriptAnalyzer(project=project, llm_provider=mock_llm, verbose=False)
        path, content = analyzer._load_source_material()
        assert content == ""

    def test_load_script_scenes(self, project_with_source, mock_llm):
        """Test loading script scenes from narrations."""
        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )
        scenes = analyzer._load_script_scenes()
        assert len(scenes) == 2
        assert scenes[0]["scene_id"] == "scene1_hook"

    def test_extract_concepts(self, project_with_source, mock_llm):
        """Test concept extraction from source."""
        mock_llm.generate_json.return_value = {
            "concepts": [
                {
                    "name": "Policy Gradient",
                    "description": "Training method",
                    "importance": "high",
                    "prerequisites": [],
                    "section_reference": "Section 2",
                }
            ]
        }

        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )
        concepts = analyzer._extract_concepts("Test content")

        assert len(concepts) == 1
        assert concepts[0].name == "Policy Gradient"
        mock_llm.generate_json.assert_called_once()

    def test_analyze_gaps(self, project_with_source, mock_llm):
        """Test gap analysis between concepts and scenes."""
        mock_llm.generate_json.return_value = {
            "concept_coverage": [
                {
                    "concept_name": "Test Concept",
                    "depth": "explained",
                    "scene_ids": ["scene1"],
                    "coverage_notes": "Well covered",
                    "suggestion": None,
                }
            ],
            "narrative_gaps": [
                {
                    "from_scene_id": "scene1",
                    "from_scene_title": "Scene 1",
                    "to_scene_id": "scene2",
                    "to_scene_title": "Scene 2",
                    "gap_description": "Missing transition",
                    "severity": "medium",
                    "suggested_bridge": "Add connecting sentence",
                }
            ],
            "suggested_scenes": [],
            "overall_coverage_score": 75.0,
            "analysis_notes": "Good coverage overall",
        }

        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )

        concepts = [SourceConcept(name="Test Concept", description="Test")]
        scenes = [{"scene_id": "scene1", "title": "Scene 1"}]
        result = analyzer._analyze_gaps(Path("input.md"), concepts, scenes)

        assert len(result.concepts) == 1
        assert len(result.narrative_gaps) == 1
        assert result.overall_coverage_score == 75.0

    def test_analyze_full_workflow(self, project_with_source, mock_llm):
        """Test full analyze workflow."""
        # Set up mock responses
        mock_llm.generate_json.side_effect = [
            # First call: concept extraction
            {
                "concepts": [
                    {
                        "name": "Chain-of-Thought",
                        "description": "Step-by-step reasoning",
                        "importance": "high",
                        "prerequisites": [],
                        "section_reference": "Section 1",
                    }
                ]
            },
            # Second call: gap analysis
            {
                "concept_coverage": [
                    {
                        "concept_name": "Chain-of-Thought",
                        "depth": "mentioned",
                        "scene_ids": ["scene1_hook"],
                        "coverage_notes": "Briefly mentioned",
                        "suggestion": "Add more detail",
                    }
                ],
                "narrative_gaps": [],
                "suggested_scenes": [],
                "overall_coverage_score": 60.0,
                "analysis_notes": "Needs more depth",
            },
        ]

        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )
        result = analyzer.analyze()

        assert result.project_id == project_with_source.id
        assert result.overall_coverage_score == 60.0
        assert mock_llm.generate_json.call_count == 2

    def test_save_result(self, project_with_source, mock_llm):
        """Test saving analysis result to file."""
        analyzer = ScriptAnalyzer(
            project=project_with_source,
            llm_provider=mock_llm,
            verbose=False,
        )

        result = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            overall_coverage_score=80.0,
        )

        output_path = analyzer.save_result(result)
        assert output_path.exists()
        assert output_path.name == "gap_analysis.json"

        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data["overall_coverage_score"] == 80.0


class TestConceptExtractionPrompt:
    """Tests for the concept extraction prompt format."""

    def test_prompt_contains_source_content_placeholder(self):
        """Test that the prompt has the source_content placeholder."""
        assert "{source_content}" in CONCEPT_EXTRACTION_PROMPT

    def test_prompt_requests_json_output(self):
        """Test that the prompt requests JSON output."""
        assert "JSON" in CONCEPT_EXTRACTION_PROMPT


class TestGapAnalysisPrompt:
    """Tests for the gap analysis prompt format."""

    def test_prompt_contains_placeholders(self):
        """Test that the prompt has required placeholders."""
        assert "{concepts_json}" in GAP_ANALYSIS_PROMPT
        assert "{scenes_json}" in GAP_ANALYSIS_PROMPT

    def test_prompt_requests_required_fields(self):
        """Test that the prompt requests required output fields."""
        assert "concept_coverage" in GAP_ANALYSIS_PROMPT
        assert "narrative_gaps" in GAP_ANALYSIS_PROMPT
        assert "suggested_scenes" in GAP_ANALYSIS_PROMPT
        assert "overall_coverage_score" in GAP_ANALYSIS_PROMPT
