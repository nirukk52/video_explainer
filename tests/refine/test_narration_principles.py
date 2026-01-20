"""Tests for narration principles."""

import pytest

from src.refine.narration_principles import (
    NARRATION_PRINCIPLES,
    NarrationPrinciple,
    format_principles_for_prompt,
    format_checklist_for_prompt,
    get_principle_by_id,
    get_principle_by_name,
)


class TestNarrationPrinciple:
    """Tests for NarrationPrinciple dataclass."""

    def test_principle_creation(self):
        """Test creating a NarrationPrinciple."""
        principle = NarrationPrinciple(
            id=1,
            name="Test Principle",
            description="A test principle description",
            good_example="Good example text",
            bad_example="Bad example text",
            check_question="Is this good?",
        )
        assert principle.id == 1
        assert principle.name == "Test Principle"
        assert principle.check_question == "Is this good?"

    def test_principle_to_dict(self):
        """Test NarrationPrinciple serialization."""
        principle = NarrationPrinciple(
            id=1,
            name="Test",
            description="Desc",
            good_example="Good",
            bad_example="Bad",
            check_question="Check?",
        )
        data = principle.to_dict()

        assert data["id"] == 1
        assert data["name"] == "Test"
        assert data["description"] == "Desc"
        assert data["good_example"] == "Good"
        assert data["bad_example"] == "Bad"
        assert data["check_question"] == "Check?"


class TestNarrationPrinciplesList:
    """Tests for NARRATION_PRINCIPLES list."""

    def test_has_10_principles(self):
        """Test that there are exactly 10 narration principles."""
        assert len(NARRATION_PRINCIPLES) == 10

    def test_principles_have_unique_ids(self):
        """Test that all principles have unique IDs."""
        ids = [p.id for p in NARRATION_PRINCIPLES]
        assert len(ids) == len(set(ids))

    def test_principles_have_unique_names(self):
        """Test that all principles have unique names."""
        names = [p.name for p in NARRATION_PRINCIPLES]
        assert len(names) == len(set(names))

    def test_principles_sequential_ids(self):
        """Test that principle IDs are sequential 1-10."""
        ids = sorted([p.id for p in NARRATION_PRINCIPLES])
        assert ids == list(range(1, 11))

    def test_each_principle_has_check_question(self):
        """Test that each principle has a check question."""
        for principle in NARRATION_PRINCIPLES:
            assert principle.check_question, f"Principle {principle.name} has no check question"
            assert "?" in principle.check_question, f"Check question for {principle.name} is not a question"

    def test_each_principle_has_examples(self):
        """Test that each principle has good and bad examples."""
        for principle in NARRATION_PRINCIPLES:
            assert principle.good_example, f"Principle {principle.name} has no good example"
            assert principle.bad_example, f"Principle {principle.name} has no bad example"

    def test_principles_are_universal(self):
        """Test that principles don't reference specific projects."""
        # These words would indicate project-specific principles
        project_specific_words = [
            "thinking-models",
            "reinforcement learning",  # Too specific to one topic
            "AI reasoning",  # Too specific
        ]

        for principle in NARRATION_PRINCIPLES:
            full_text = (
                principle.description +
                principle.good_example +
                principle.bad_example +
                principle.check_question
            ).lower()

            # Check that core principle text doesn't reference specific projects
            assert "thinking-models" not in full_text.lower(), \
                f"Principle {principle.name} references specific project"


class TestGetPrincipleById:
    """Tests for get_principle_by_id function."""

    def test_get_existing_principle(self):
        """Test retrieving an existing principle by ID."""
        principle = get_principle_by_id(1)
        assert principle is not None
        assert principle.id == 1
        assert "hook" in principle.name.lower()

    def test_get_nonexistent_principle(self):
        """Test retrieving a non-existent principle returns None."""
        principle = get_principle_by_id(999)
        assert principle is None

    def test_get_all_principles_by_id(self):
        """Test that all principles can be retrieved by their IDs."""
        for i in range(1, 11):
            principle = get_principle_by_id(i)
            assert principle is not None
            assert principle.id == i


class TestGetPrincipleByName:
    """Tests for get_principle_by_name function."""

    def test_get_by_exact_name(self):
        """Test retrieving principle by exact name."""
        principle = get_principle_by_name("hook")
        assert principle is not None
        assert "hook" in principle.name.lower()

    def test_get_by_partial_name(self):
        """Test retrieving principle by partial name match."""
        principle = get_principle_by_name("transition")
        assert principle is not None
        assert "transition" in principle.name.lower()

    def test_case_insensitive(self):
        """Test that name matching is case-insensitive."""
        principle1 = get_principle_by_name("HOOK")
        principle2 = get_principle_by_name("hook")
        assert principle1 == principle2

    def test_nonexistent_name(self):
        """Test that non-matching name returns None."""
        principle = get_principle_by_name("nonexistent_principle_xyz")
        assert principle is None


class TestFormatPrinciplesForPrompt:
    """Tests for format_principles_for_prompt function."""

    def test_format_includes_all_principles(self):
        """Test that formatted output includes all principles."""
        formatted = format_principles_for_prompt()
        for principle in NARRATION_PRINCIPLES:
            assert principle.name in formatted

    def test_format_includes_descriptions(self):
        """Test that formatted output includes descriptions."""
        formatted = format_principles_for_prompt()
        # Check that at least some key description words appear
        assert "hook" in formatted.lower()
        assert "transition" in formatted.lower()

    def test_format_includes_examples(self):
        """Test that formatted output includes examples."""
        formatted = format_principles_for_prompt()
        assert "Good example" in formatted or "Good:" in formatted
        assert "Bad example" in formatted or "Bad:" in formatted

    def test_format_includes_check_questions(self):
        """Test that formatted output includes check questions."""
        formatted = format_principles_for_prompt()
        assert "Check:" in formatted or "check" in formatted.lower()

    def test_format_has_structure(self):
        """Test that formatted output has proper structure."""
        formatted = format_principles_for_prompt()
        # Should have numbered sections
        assert "1." in formatted or "### 1" in formatted
        assert "10." in formatted or "### 10" in formatted


class TestFormatChecklistForPrompt:
    """Tests for format_checklist_for_prompt function."""

    def test_format_checklist_has_items(self):
        """Test checklist has items for all principles."""
        checklist = format_checklist_for_prompt()
        # Should have checkbox notation
        assert "[ ]" in checklist

    def test_format_checklist_has_all_principles(self):
        """Test checklist includes all principles."""
        checklist = format_checklist_for_prompt()
        for principle in NARRATION_PRINCIPLES:
            # Each principle should have its number
            assert str(principle.id) in checklist

    def test_format_checklist_has_10_items(self):
        """Test checklist has 10 items."""
        checklist = format_checklist_for_prompt()
        # Count checkbox occurrences
        checkbox_count = checklist.count("[ ]")
        assert checkbox_count == 10


class TestPrincipleContent:
    """Tests for specific principle content."""

    def test_hook_principle_exists(self):
        """Test that hook principle exists and is first."""
        principle = get_principle_by_id(1)
        assert "hook" in principle.name.lower()

    def test_transition_principle_exists(self):
        """Test that transition principle exists."""
        principle = get_principle_by_name("transition")
        assert principle is not None

    def test_tension_principle_exists(self):
        """Test that tension/buildup principle exists."""
        principle = get_principle_by_name("tension")
        assert principle is not None

    def test_analogy_principle_exists(self):
        """Test that analogy principle exists."""
        principle = get_principle_by_name("analog")
        assert principle is not None

    def test_emotional_principle_exists(self):
        """Test that emotional beat principle exists."""
        principle = get_principle_by_name("emotional")
        assert principle is not None

    def test_length_principle_exists(self):
        """Test that length/duration principle exists."""
        principle = get_principle_by_name("length")
        assert principle is not None

    def test_impact_ending_principle_exists(self):
        """Test that ending/impact principle exists."""
        principle = get_principle_by_name("impact") or get_principle_by_name("end")
        assert principle is not None


class TestPrincipleUniversality:
    """Tests ensuring principles apply universally to all videos."""

    def test_principles_not_project_specific(self):
        """Test that principles don't mention specific projects."""
        for principle in NARRATION_PRINCIPLES:
            text = principle.description.lower()
            # Should not reference specific projects
            assert "thinking" not in text or "real thinking" in text, \
                f"Principle {principle.name} may be project-specific"

    def test_principles_applicable_to_various_topics(self):
        """Test that principles could apply to various video topics."""
        # These are video types the principles should work for
        video_types = [
            "mathematics",
            "physics",
            "programming",
            "history",
            "biology",
        ]

        # Just verify the principles don't exclude these topics
        formatted = format_principles_for_prompt().lower()

        # Should not contain exclusionary language
        exclusionary = ["only for ai", "only for tech", "specifically for"]
        for phrase in exclusionary:
            assert phrase not in formatted

    def test_examples_are_illustrative_not_prescriptive(self):
        """Test that examples illustrate the principle, not specific content."""
        for principle in NARRATION_PRINCIPLES:
            # Good examples should explain the technique, not give exact words
            good_ex = principle.good_example.lower()
            # They can reference specific examples but should explain WHY it's good
            assert len(good_ex) > 20, f"Good example for {principle.name} is too short to be illustrative"
