"""Integration tests that make real LLM calls.

These tests verify the quality of generated content, not just structure.
They are expensive to run and should only be run when explicitly requested.

Run with: pytest tests/test_integration_llm.py -v --run-llm-tests
Skip with: pytest tests/test_integration_llm.py -v (will skip by default)
"""

import pytest
from pathlib import Path

# Mark all tests in this module to require --run-llm-tests flag
pytestmark = pytest.mark.llm_integration


@pytest.fixture
def sample_technical_content():
    """A short technical document for testing."""
    return """
# Understanding Attention Mechanisms

Attention mechanisms allow neural networks to focus on relevant parts of input.

## The Problem
Traditional sequence models process input left-to-right, making it hard to
capture long-range dependencies. By the time the model reaches token 100,
information about token 1 has degraded.

## The Solution: Attention
Attention computes relevance scores between all pairs of tokens:
1. Each token produces Query (Q), Key (K), and Value (V) vectors
2. Attention scores = softmax(Q · K^T / √d)
3. Output = weighted sum of Values using attention scores

The key insight: every token can directly attend to every other token,
regardless of position. No information degradation over distance.

## Why It Works
- Q represents "what am I looking for?"
- K represents "what do I contain?"
- V represents "what information do I provide?"
- The dot product Q·K measures relevance
- Softmax normalizes scores to sum to 1
"""


@pytest.fixture
def llm_provider():
    """Create an LLM provider for testing."""
    from src.understanding.llm_provider import get_llm_provider
    from src.config import load_config

    config = load_config()
    return get_llm_provider(config)


class TestScriptGeneratorQuality:
    """Test that script generator produces quality output."""

    @pytest.fixture
    def script_generator(self):
        from src.script.generator import ScriptGenerator

        return ScriptGenerator()

    @pytest.fixture
    def content_analyzer(self):
        from src.understanding.analyzer import ContentAnalyzer

        return ContentAnalyzer()

    @pytest.fixture
    def parsed_document(self, sample_technical_content, tmp_path):
        """Parse the sample content into a document."""
        from src.ingestion.parser import parse_document

        # Write to temp file
        doc_path = tmp_path / "test_doc.md"
        doc_path.write_text(sample_technical_content)

        return parse_document(doc_path)

    def test_script_covers_core_concepts(
        self, script_generator, content_analyzer, parsed_document
    ):
        """Verify the script covers core concepts from source material."""
        # Analyze the document
        analysis = content_analyzer.analyze(parsed_document)

        # Generate script
        script = script_generator.generate(
            parsed_document, analysis, target_duration=180  # 3 minutes
        )

        # Check that core concepts are covered
        all_voiceovers = " ".join(scene.voiceover for scene in script.scenes).lower()

        # These concepts should be mentioned (from source material)
        expected_concepts = [
            "attention",
            "query",
            "key",
            "value",
            "softmax",
        ]

        missing = [c for c in expected_concepts if c not in all_voiceovers]
        assert (
            len(missing) <= 1
        ), f"Script missing core concepts: {missing}. Script should cover: {expected_concepts}"

    def test_script_explains_mechanisms(
        self, script_generator, content_analyzer, parsed_document
    ):
        """Verify the script explains how things work, not just what they are."""
        analysis = content_analyzer.analyze(parsed_document)
        script = script_generator.generate(parsed_document, analysis, target_duration=180)

        all_voiceovers = " ".join(scene.voiceover for scene in script.scenes).lower()

        # Should contain mechanism explanations (how, why, step)
        mechanism_indicators = [
            "how",
            "why",
            "step",
            "because",
            "therefore",
            "computes",
            "calculates",
            "produces",
        ]

        found = [ind for ind in mechanism_indicators if ind in all_voiceovers]
        assert (
            len(found) >= 3
        ), f"Script lacks mechanism explanations. Only found: {found}"

    def test_script_has_causal_connections(
        self, script_generator, content_analyzer, parsed_document
    ):
        """Verify scenes connect causally, not just sequentially."""
        analysis = content_analyzer.analyze(parsed_document)
        script = script_generator.generate(parsed_document, analysis, target_duration=180)

        # Count scenes with causal connections
        causal_markers = ["but", "therefore", "so", "however", "because"]
        scenes_with_connections = 0

        for scene in script.scenes[1:]:  # Skip first scene
            voiceover_lower = scene.voiceover.lower()
            if any(marker in voiceover_lower for marker in causal_markers):
                scenes_with_connections += 1

        # At least 50% of scenes should have causal connections
        connection_ratio = scenes_with_connections / max(1, len(script.scenes) - 1)
        assert (
            connection_ratio >= 0.4
        ), f"Only {connection_ratio:.0%} of scenes have causal connections. Expected at least 40%."


class TestVisualDescriptionQuality:
    """Test that visual descriptions are concept-specific."""

    @pytest.fixture
    def script_generator(self):
        from src.script.generator import ScriptGenerator

        return ScriptGenerator()

    @pytest.fixture
    def content_analyzer(self):
        from src.understanding.analyzer import ContentAnalyzer

        return ContentAnalyzer()

    @pytest.fixture
    def parsed_document(self, sample_technical_content, tmp_path):
        from src.ingestion.parser import parse_document

        doc_path = tmp_path / "test_doc.md"
        doc_path.write_text(sample_technical_content)
        return parse_document(doc_path)

    def test_visual_descriptions_are_specific(
        self, script_generator, content_analyzer, parsed_document
    ):
        """Verify visual descriptions reference specific concepts, not generic elements."""
        analysis = content_analyzer.analyze(parsed_document)
        script = script_generator.generate(parsed_document, analysis, target_duration=180)

        # Check visual descriptions for specificity
        all_visuals = " ".join(
            scene.visual_cue.description for scene in script.scenes
        ).lower()

        # Should contain concept-specific terms
        specific_terms = ["query", "key", "value", "attention", "vector", "score"]
        generic_terms_only = ["box", "arrow", "flow", "animation"]

        specific_found = [t for t in specific_terms if t in all_visuals]

        # Should have at least 2 concept-specific terms in visuals
        assert (
            len(specific_found) >= 2
        ), f"Visual descriptions lack specificity. Only found: {specific_found}. Visuals should reference: {specific_terms}"


class TestMathExplanationQuality:
    """Test that math is explained intuitively."""

    @pytest.fixture
    def math_content(self):
        """Content with a formula that needs explaining."""
        return """
# The Advantage Function in RL

The advantage function measures how much better an action is compared to average:

A(s,a) = Q(s,a) - V(s)

Where:
- Q(s,a) is the action-value function
- V(s) is the state-value function
- A(s,a) is the advantage

Positive advantage means the action is better than average.
Negative advantage means it's worse than average.
"""

    @pytest.fixture
    def parsed_math_doc(self, math_content, tmp_path):
        from src.ingestion.parser import parse_document

        doc_path = tmp_path / "math_doc.md"
        doc_path.write_text(math_content)
        return parse_document(doc_path)

    def test_formula_is_explained_intuitively(self, parsed_math_doc):
        """Verify formulas are explained with intuition, not just labels."""
        from src.script.generator import ScriptGenerator
        from src.understanding.analyzer import ContentAnalyzer

        analyzer = ContentAnalyzer()
        generator = ScriptGenerator()

        analysis = analyzer.analyze(parsed_math_doc)
        script = generator.generate(parsed_math_doc, analysis, target_duration=120)

        all_voiceovers = " ".join(scene.voiceover for scene in script.scenes).lower()

        # Should explain intuition, not just label terms
        intuition_indicators = [
            "better",
            "worse",
            "average",
            "compare",
            "difference",
            "how good",
            "how well",
        ]

        found = [ind for ind in intuition_indicators if ind in all_voiceovers]

        # Should have intuitive explanations
        assert (
            len(found) >= 2
        ), f"Formula explanation lacks intuition. Only found: {found}. Should explain meaning, not just labels."
