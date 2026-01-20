"""Tests for refine principles."""

import pytest

from src.refine.principles import (
    GUIDING_PRINCIPLES,
    Principle,
    format_principles_for_prompt,
    format_checklist_for_prompt,
    get_principle_by_id,
    get_principle_by_issue_type,
)
from src.refine.models import IssueType


class TestPrinciple:
    """Tests for Principle dataclass."""

    def test_principle_creation(self):
        """Test creating a Principle."""
        principle = Principle(
            id=1,
            name="Test Principle",
            issue_type=IssueType.SHOW_DONT_TELL,
            description="A test principle",
            good_example="Do this",
            bad_example="Not this",
            checklist_question="Is this good?",
        )
        assert principle.id == 1
        assert principle.name == "Test Principle"
        assert principle.issue_type == IssueType.SHOW_DONT_TELL
        assert principle.checklist_question == "Is this good?"

    def test_principle_to_dict(self):
        """Test Principle serialization."""
        principle = Principle(
            id=1,
            name="Test Principle",
            issue_type=IssueType.VISUAL_HIERARCHY,
            description="A test",
            good_example="Good",
            bad_example="Bad",
            checklist_question="Check?",
        )
        data = principle.to_dict()

        assert data["id"] == 1
        assert data["name"] == "Test Principle"
        assert data["issue_type"] == "visual_hierarchy"
        assert data["checklist_question"] == "Check?"


class TestGuidingPrinciples:
    """Tests for GUIDING_PRINCIPLES list."""

    def test_has_11_principles(self):
        """Test that there are exactly 11 guiding principles."""
        assert len(GUIDING_PRINCIPLES) == 11

    def test_principles_have_unique_ids(self):
        """Test that all principles have unique IDs."""
        ids = [p.id for p in GUIDING_PRINCIPLES]
        assert len(ids) == len(set(ids))

    def test_principles_have_unique_names(self):
        """Test that all principles have unique names."""
        names = [p.name for p in GUIDING_PRINCIPLES]
        assert len(names) == len(set(names))

    def test_principles_cover_all_issue_types(self):
        """Test that principles cover all issue types (except 'other')."""
        covered_types = {p.issue_type for p in GUIDING_PRINCIPLES}
        expected_types = {
            IssueType.SHOW_DONT_TELL,
            IssueType.ANIMATION_REVEALS,
            IssueType.PROGRESSIVE_DISCLOSURE,
            IssueType.TEXT_COMPLEMENTS,
            IssueType.VISUAL_HIERARCHY,
            IssueType.BREATHING_ROOM,
            IssueType.PURPOSEFUL_MOTION,
            IssueType.EMOTIONAL_RESONANCE,
            IssueType.PROFESSIONAL_POLISH,
            IssueType.SYNC_WITH_NARRATION,
            IssueType.SCREEN_SPACE_UTILIZATION,
        }
        assert covered_types == expected_types

    def test_each_principle_has_checklist_question(self):
        """Test that each principle has a checklist question."""
        for principle in GUIDING_PRINCIPLES:
            assert principle.checklist_question, f"Principle {principle.name} has no checklist question"

    def test_each_principle_has_examples(self):
        """Test that each principle has good and bad examples."""
        for principle in GUIDING_PRINCIPLES:
            assert principle.good_example, f"Principle {principle.name} has no good example"
            assert principle.bad_example, f"Principle {principle.name} has no bad example"

    def test_principles_sequential_ids(self):
        """Test that principle IDs are sequential 1-11."""
        ids = sorted([p.id for p in GUIDING_PRINCIPLES])
        assert ids == list(range(1, 12))


class TestGetPrincipleById:
    """Tests for get_principle_by_id function."""

    def test_get_existing_principle(self):
        """Test retrieving an existing principle by ID."""
        principle = get_principle_by_id(1)
        assert principle is not None
        assert principle.id == 1
        assert principle.name == "Show, don't tell"

    def test_get_nonexistent_principle(self):
        """Test retrieving a non-existent principle returns None."""
        principle = get_principle_by_id(999)
        assert principle is None

    def test_get_all_principles_by_id(self):
        """Test that all principles can be retrieved by their IDs."""
        for i in range(1, 12):
            principle = get_principle_by_id(i)
            assert principle is not None
            assert principle.id == i


class TestGetPrincipleByIssueType:
    """Tests for get_principle_by_issue_type function."""

    def test_get_by_issue_type(self):
        """Test retrieving principle by issue type."""
        principle = get_principle_by_issue_type(IssueType.SHOW_DONT_TELL)
        assert principle is not None
        assert principle.id == 1

    def test_get_by_each_issue_type(self):
        """Test that each issue type maps to a principle."""
        issue_types = [
            IssueType.SHOW_DONT_TELL,
            IssueType.ANIMATION_REVEALS,
            IssueType.PROGRESSIVE_DISCLOSURE,
            IssueType.TEXT_COMPLEMENTS,
            IssueType.VISUAL_HIERARCHY,
            IssueType.BREATHING_ROOM,
            IssueType.PURPOSEFUL_MOTION,
            IssueType.EMOTIONAL_RESONANCE,
            IssueType.PROFESSIONAL_POLISH,
            IssueType.SYNC_WITH_NARRATION,
            IssueType.SCREEN_SPACE_UTILIZATION,
        ]
        for issue_type in issue_types:
            principle = get_principle_by_issue_type(issue_type)
            assert principle is not None


class TestFormatPrinciplesForPrompt:
    """Tests for format_principles_for_prompt function."""

    def test_format_includes_all_principles(self):
        """Test that formatted output includes all principles."""
        formatted = format_principles_for_prompt()
        for principle in GUIDING_PRINCIPLES:
            assert principle.name in formatted

    def test_format_includes_descriptions(self):
        """Test that formatted output includes descriptions."""
        formatted = format_principles_for_prompt()
        assert "Show, don't tell" in formatted
        assert "Animation reveals" in formatted

    def test_format_includes_examples(self):
        """Test that formatted output includes examples."""
        formatted = format_principles_for_prompt()
        assert "Good:" in formatted
        assert "Bad:" in formatted

    def test_format_includes_checklist(self):
        """Test that formatted output includes checklist questions."""
        formatted = format_principles_for_prompt()
        assert "Check:" in formatted


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
        for principle in GUIDING_PRINCIPLES:
            # Each principle should have its number and name
            assert str(principle.id) in checklist
            assert principle.name in checklist

    def test_format_checklist_has_questions(self):
        """Test checklist includes questions."""
        checklist = format_checklist_for_prompt()
        # Should include checklist questions
        assert "?" in checklist

    def test_format_checklist_has_11_items(self):
        """Test checklist has 11 items."""
        checklist = format_checklist_for_prompt()
        # Count checkbox occurrences
        checkbox_count = checklist.count("[ ]")
        assert checkbox_count == 11


class TestPrinciplesInInspectorPrompt:
    """Tests to ensure principles are passed to Claude Code inspector.

    These tests prevent regression where principles could be duplicated
    or not passed to the agent prompt.
    """

    def test_inspector_prompt_has_principles_placeholder(self):
        """Test that the inspector prompt template includes {principles} placeholder."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        assert "{principles}" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT, (
            "CLAUDE_CODE_VISUAL_INSPECTION_PROMPT must include {principles} placeholder. "
            "Without this, principles won't be passed to the Claude Code agent."
        )

    def test_inspector_prompt_mentions_all_11_principles(self):
        """Test that formatted prompt includes all 11 principles."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Format the prompt with actual principles
        formatted = CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.format(
            remotion_url="http://test",
            scene_number=1,
            scene_title="Test",
            scene_file="/test/file.tsx",
            duration_seconds=30.0,
            total_frames=900,
            num_beats=5,
            narration_text="Test narration",
            beats_info="Beat 1 info",
            beat_frames_list="0, 450",
            first_beat_frame="0",
            principles=format_principles_for_prompt(),
        )

        # Check all principle names appear
        for principle in GUIDING_PRINCIPLES:
            assert principle.name in formatted, (
                f"Principle '{principle.name}' not found in formatted prompt. "
                "All principles must be included in the Claude Code agent prompt."
            )

    def test_inspector_prompt_includes_screen_space_principle(self):
        """Test that the new screen space utilization principle is included."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        formatted = CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.format(
            remotion_url="http://test",
            scene_number=1,
            scene_title="Test",
            scene_file="/test/file.tsx",
            duration_seconds=30.0,
            total_frames=900,
            num_beats=5,
            narration_text="Test narration",
            beats_info="Beat 1 info",
            beat_frames_list="0, 450",
            first_beat_frame="0",
            principles=format_principles_for_prompt(),
        )

        # Specifically check for screen space utilization
        assert "Screen space utilization" in formatted
        assert "screen_space_utilization" in formatted, (
            "screen_space_utilization principle code must be in the prompt "
            "so Claude Code can identify issues of this type."
        )

    def test_inspector_prompt_lists_all_principle_codes(self):
        """Test that all principle codes are listed in the prompt."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # These codes should be in the prompt for JSON output
        expected_codes = [
            "show_dont_tell",
            "animation_reveals",
            "progressive_disclosure",
            "text_complements",
            "visual_hierarchy",
            "breathing_room",
            "purposeful_motion",
            "emotional_resonance",
            "professional_polish",
            "sync_with_narration",
            "screen_space_utilization",
        ]

        for code in expected_codes:
            assert code in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT, (
                f"Principle code '{code}' not found in prompt. "
                "All principle codes must be listed for the JSON output format."
            )

    def test_no_duplicate_principles_definition(self):
        """Test that principles are not duplicated in inspector.py."""
        import inspect
        from src.refine.visual import inspector

        source = inspect.getsource(inspector)

        # Check there's no hardcoded PRINCIPLES_SHORT or similar
        assert "PRINCIPLES_SHORT" not in source, (
            "Found PRINCIPLES_SHORT in inspector.py. "
            "Principles should only be defined in principles.py to prevent duplication."
        )

        # Check there's no hardcoded list of principle descriptions
        # (looking for patterns like "1. Show Don't Tell" which would indicate duplication)
        hardcoded_pattern_count = source.count("1. Show Don't Tell")
        assert hardcoded_pattern_count == 0, (
            "Found hardcoded principle list in inspector.py. "
            "Use format_principles_for_prompt() instead."
        )

    def test_inspector_prompt_has_three_phase_workflow(self):
        """Test that prompt enforces a 3-phase workflow for thoroughness."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for Phase 1: Complete Inspection
        assert "Phase 1" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "COMPLETE INSPECTION" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT or \
               "complete inspection" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.lower()

        # Check for Phase 2: Fix Issues
        assert "Phase 2" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "FIX" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for Phase 3: Verify
        assert "Phase 3" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "VERIFY" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT or \
               "verify" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.lower()

    def test_inspector_prompt_requires_complete_coverage(self):
        """Test that prompt emphasizes complete coverage of all beats."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for emphasis on complete coverage
        assert "MUST" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "ALL" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "{num_beats}" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for warnings against partial inspection
        partial_warning_present = (
            "Partial inspection" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT or
            "Stopping early" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT or
            "skipping frames" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        )
        assert partial_warning_present, (
            "Prompt should warn against partial inspection or skipping frames"
        )

    def test_inspector_prompt_requires_per_beat_reporting(self):
        """Test that prompt requires reporting on each beat inspected."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for beats_inspected in JSON output
        assert "beats_inspected" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "total_beats_expected" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "total_beats_inspected" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_inspector_prompt_has_navigation_tips(self):
        """Test that prompt includes Remotion Studio navigation tips."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for navigation section
        assert "Navigation" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        # Check for specific navigation instructions
        assert "frame counter" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.lower()
        assert "arrow keys" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.lower()
        # Check that PRESS ENTER is emphasized
        assert "PRESS ENTER" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_inspector_prompt_has_principle_checklist(self):
        """Test that prompt includes explicit principle checklist for each beat."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for checklist format
        assert "Principle Checklist" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "PASS/ISSUE" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        # Check all 11 principles are in checklist
        assert "Show don't tell" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "Screen space utilization" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_inspector_prompt_requires_verification_with_evidence(self):
        """Test that prompt requires verification to show which principles were fixed."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for verification results structure
        assert "verification_results" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "principles_fixed" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "Was ISSUE" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "Now PASS" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "evidence" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_inspector_prompt_requires_principle_checklist_in_json(self):
        """Test that JSON output includes principle_checklist for each beat."""
        from src.refine.visual.inspector import CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

        # Check for principle_checklist in JSON structure
        assert "principle_checklist" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "issues_summary" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
