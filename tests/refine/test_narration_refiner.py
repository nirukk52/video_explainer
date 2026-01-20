"""Tests for the ScriptRefiner (Phase 2: Script Refinement)."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import LLMConfig
from src.refine.models import (
    AddScenePatch,
    ExpandScenePatch,
    GapAnalysisResult,
    ModifyScenePatch,
    NarrationIssue,
    NarrationIssueType,
    NarrationRefinementResult,
    NarrationScores,
    SceneNarrationAnalysis,
    ScriptPatchType,
)
from src.refine.script.narration_refiner import (
    ScriptRefiner,
    NarrationRefiner,
    NARRATION_ANALYSIS_SYSTEM_PROMPT,
    SINGLE_SCENE_ANALYSIS_PROMPT,
)


class TestNarrationIssueType:
    """Tests for NarrationIssueType enum."""

    def test_all_types_defined(self):
        """Test that all expected issue types are defined."""
        expected_types = [
            "weak_hook",
            "poor_transition",
            "missing_tension",
            "no_key_insight",
            "lacks_analogy",
            "no_emotional_beat",
            "wrong_length",
            "technical_inaccuracy",
            "redundant_text",
            "other",
        ]
        for t in expected_types:
            assert NarrationIssueType(t)


class TestNarrationIssue:
    """Tests for NarrationIssue dataclass."""

    def test_creation(self):
        """Test creating a NarrationIssue."""
        issue = NarrationIssue(
            scene_id="scene1",
            issue_type=NarrationIssueType.WEAK_HOOK,
            description="Opening doesn't grab attention",
            current_text="In this section we discuss...",
            severity="high",
            suggested_fix="Start with a surprising statistic",
        )
        assert issue.issue_type == NarrationIssueType.WEAK_HOOK
        assert issue.severity == "high"

    def test_to_dict(self):
        """Test NarrationIssue serialization."""
        issue = NarrationIssue(
            scene_id="scene1",
            issue_type=NarrationIssueType.POOR_TRANSITION,
            description="Abrupt topic change",
            current_text="Next, we look at...",
            severity="medium",
        )
        data = issue.to_dict()
        assert data["issue_type"] == "poor_transition"
        assert data["severity"] == "medium"

    def test_from_dict(self):
        """Test NarrationIssue deserialization."""
        data = {
            "scene_id": "scene2",
            "issue_type": "lacks_analogy",
            "description": "Concept explained abstractly",
            "current_text": "The algorithm works by...",
            "severity": "low",
            "suggested_fix": "Add concrete example",
        }
        issue = NarrationIssue.from_dict(data)
        assert issue.issue_type == NarrationIssueType.LACKS_ANALOGY
        assert issue.suggested_fix == "Add concrete example"


class TestNarrationScores:
    """Tests for NarrationScores dataclass."""

    def test_default_scores(self):
        """Test default score values."""
        scores = NarrationScores()
        assert scores.hook == 0.0
        assert scores.flow == 0.0

    def test_overall_weighted_average(self):
        """Test overall score calculation."""
        scores = NarrationScores(
            hook=10.0,
            flow=10.0,
            tension=10.0,
            insight=10.0,
            engagement=10.0,
            accuracy=10.0,
            length=10.0,
        )
        # All 10s should give overall of 10
        assert scores.overall == 10.0

    def test_overall_weighted(self):
        """Test that weights affect overall score."""
        # Higher weight on hook and accuracy
        scores1 = NarrationScores(hook=10.0, accuracy=10.0)
        scores2 = NarrationScores(tension=10.0, length=10.0)
        # scores1 should be higher because hook/accuracy have higher weights
        assert scores1.overall > scores2.overall

    def test_to_dict_includes_overall(self):
        """Test that to_dict includes computed overall."""
        scores = NarrationScores(hook=8.0, flow=7.0)
        data = scores.to_dict()
        assert "overall" in data
        assert data["overall"] > 0


class TestSceneNarrationAnalysis:
    """Tests for SceneNarrationAnalysis dataclass."""

    def test_needs_revision_no_issues(self):
        """Test needs_revision when no issues."""
        analysis = SceneNarrationAnalysis(
            scene_id="scene1",
            scene_title="Test Scene",
            current_narration="Test narration",
            duration_seconds=30,
            word_count=75,
            scores=NarrationScores(hook=8, flow=8, tension=8, insight=8, engagement=8, accuracy=8, length=8),
            issues=[],
        )
        assert not analysis.needs_revision

    def test_needs_revision_with_medium_issue(self):
        """Test needs_revision with medium severity issue."""
        analysis = SceneNarrationAnalysis(
            scene_id="scene1",
            scene_title="Test Scene",
            current_narration="Test narration",
            duration_seconds=30,
            word_count=75,
            scores=NarrationScores(),
            issues=[
                NarrationIssue(
                    scene_id="scene1",
                    issue_type=NarrationIssueType.WEAK_HOOK,
                    description="Test",
                    current_text="Test",
                    severity="medium",
                )
            ],
        )
        assert analysis.needs_revision

    def test_needs_revision_only_low_issues(self):
        """Test needs_revision with only low severity issues."""
        analysis = SceneNarrationAnalysis(
            scene_id="scene1",
            scene_title="Test Scene",
            current_narration="Test narration",
            duration_seconds=30,
            word_count=75,
            scores=NarrationScores(),
            issues=[
                NarrationIssue(
                    scene_id="scene1",
                    issue_type=NarrationIssueType.OTHER,
                    description="Minor issue",
                    current_text="Test",
                    severity="low",
                )
            ],
        )
        assert not analysis.needs_revision

    def test_expected_word_count(self):
        """Test expected word count calculation."""
        analysis = SceneNarrationAnalysis(
            scene_id="scene1",
            scene_title="Test",
            current_narration="Test",
            duration_seconds=60,  # 1 minute
            word_count=100,
            scores=NarrationScores(),
        )
        # 60 seconds * 2.5 words/sec = 150 expected
        assert analysis.expected_word_count == 150

    def test_length_ratio(self):
        """Test length ratio calculation."""
        analysis = SceneNarrationAnalysis(
            scene_id="scene1",
            scene_title="Test",
            current_narration="Test",
            duration_seconds=40,  # 100 expected words
            word_count=50,  # Half the expected
            scores=NarrationScores(),
        )
        assert analysis.length_ratio == 0.5


class TestNarrationRefinementResult:
    """Tests for NarrationRefinementResult dataclass."""

    def test_scenes_needing_revision(self):
        """Test scenes_needing_revision property."""
        result = NarrationRefinementResult(
            project_id="test",
            scene_analyses=[
                SceneNarrationAnalysis(
                    scene_id="scene1",
                    scene_title="Scene 1",
                    current_narration="Test",
                    duration_seconds=30,
                    word_count=75,
                    scores=NarrationScores(),
                    issues=[
                        NarrationIssue(
                            scene_id="scene1",
                            issue_type=NarrationIssueType.WEAK_HOOK,
                            description="Test",
                            current_text="Test",
                            severity="high",
                        )
                    ],
                ),
                SceneNarrationAnalysis(
                    scene_id="scene2",
                    scene_title="Scene 2",
                    current_narration="Test",
                    duration_seconds=30,
                    word_count=75,
                    scores=NarrationScores(),
                    issues=[],  # No issues
                ),
            ],
        )
        assert result.scenes_needing_revision == ["scene1"]

    def test_high_priority_scenes(self):
        """Test high_priority_scenes property."""
        result = NarrationRefinementResult(
            project_id="test",
            scene_analyses=[
                SceneNarrationAnalysis(
                    scene_id="scene1",
                    scene_title="Scene 1",
                    current_narration="Test",
                    duration_seconds=30,
                    word_count=75,
                    scores=NarrationScores(),
                    issues=[
                        NarrationIssue(
                            scene_id="scene1",
                            issue_type=NarrationIssueType.TECHNICAL_INACCURACY,
                            description="Wrong fact",
                            current_text="Test",
                            severity="high",
                        )
                    ],
                ),
            ],
        )
        assert result.high_priority_scenes == ["scene1"]


class TestScriptRefiner:
    """Tests for ScriptRefiner class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM provider."""
        mock = MagicMock()
        mock.generate_json.return_value = {
            "scores": {
                "hook": 7.0,
                "flow": 8.0,
                "tension": 6.0,
                "insight": 8.0,
                "engagement": 7.0,
                "accuracy": 9.0,
                "length": 8.0,
            },
            "issues": [],
            "patch": None,
            "analysis_notes": "Good narration",
        }
        return mock

    @pytest.fixture
    def project_with_narrations(self, temp_project_dir, sample_narrations):
        """Create a project with narrations."""
        # Write narrations
        narrations_path = temp_project_dir / "narration" / "narrations.json"
        with open(narrations_path, "w") as f:
            json.dump(sample_narrations, f)

        # Create source material for accuracy checks
        source_path = temp_project_dir / "input" / "source.md"
        source_path.write_text("# Source Material\n\nTest content.")

        from src.project import load_project
        return load_project(temp_project_dir)

    def test_init_with_custom_provider(self, project_with_narrations, mock_llm):
        """Test initialization with custom LLM provider."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )
        assert refiner.llm == mock_llm

    def test_narration_refiner_alias(self, project_with_narrations, mock_llm):
        """Test that NarrationRefiner is an alias for ScriptRefiner."""
        refiner = NarrationRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )
        assert isinstance(refiner, ScriptRefiner)

    def test_load_narrations(self, project_with_narrations, mock_llm):
        """Test loading narrations from project."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )
        scenes = refiner._load_narrations()
        assert len(scenes) == 2
        assert scenes[0]["scene_id"] == "scene1_hook"

    def test_get_scene_ending(self, project_with_narrations, mock_llm):
        """Test getting scene ending text."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        # None returns start indicator
        assert refiner._get_scene_ending(None) == "(start of video)"

        # Short scene returns full text
        short_scene = {"narration": "Short text"}
        assert refiner._get_scene_ending(short_scene) == "Short text"

        # Long scene returns truncated text
        long_scene = {"narration": "A" * 200}
        ending = refiner._get_scene_ending(long_scene)
        assert ending.startswith("...")
        assert len(ending) <= 104  # "..." + 100 chars

    def test_get_scene_start(self, project_with_narrations, mock_llm):
        """Test getting scene start text."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        # None returns end indicator
        assert refiner._get_scene_start(None) == "(end of video)"

        # Short scene returns full text
        short_scene = {"narration": "Short text"}
        assert refiner._get_scene_start(short_scene) == "Short text"

    def test_analyze_scene(self, project_with_narrations, mock_llm):
        """Test analyzing a single scene."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        scene = {
            "scene_id": "test_scene",
            "title": "Test Scene",
            "duration_seconds": 30,
            "narration": "This is a test narration for the scene.",
        }

        analysis, patch = refiner._analyze_scene(
            scene=scene,
            prev_ending="Previous ending",
            next_start="Next start",
            gap_context="No significant gaps identified.",
        )

        assert analysis.scene_id == "test_scene"
        assert analysis.scores.hook == 7.0
        assert patch is None  # No patch because no issues
        mock_llm.generate_json.assert_called_once()

    def test_analyze_scene_with_issues(self, project_with_narrations, mock_llm):
        """Test analyzing a scene that has issues and generates a patch."""
        mock_llm.generate_json.return_value = {
            "scores": {"hook": 3.0, "flow": 4.0, "tension": 3.0, "insight": 5.0, "engagement": 4.0, "accuracy": 8.0, "length": 7.0},
            "issues": [
                {
                    "issue_type": "weak_hook",
                    "description": "Opening doesn't grab attention",
                    "current_text": "In this section",
                    "severity": "high",
                    "suggested_fix": "Start with a question",
                }
            ],
            "patch": {
                "patch_type": "modify_scene",
                "priority": "high",
                "reason": "Hook needs improvement",
                "scene_id": "test_scene",
                "field_name": "narration",
                "old_value": "In this section we discuss important topics.",
                "new_value": "What if I told you...",
            },
            "analysis_notes": "Needs work on hook",
        }

        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        scene = {
            "scene_id": "test_scene",
            "title": "Test Scene",
            "duration_seconds": 30,
            "narration": "In this section we discuss important topics.",
        }

        analysis, patch = refiner._analyze_scene(
            scene=scene,
            prev_ending="(start of video)",
            next_start="Next scene",
            gap_context="",
        )

        assert len(analysis.issues) == 1
        assert analysis.issues[0].issue_type == NarrationIssueType.WEAK_HOOK
        assert patch is not None
        assert isinstance(patch, ModifyScenePatch)
        assert patch.new_value == "What if I told you..."

    def test_refine_returns_tuple(self, project_with_narrations, mock_llm):
        """Test that refine returns a tuple of (patches, result)."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        patches, result = refiner.refine()

        assert isinstance(patches, list)
        assert isinstance(result, NarrationRefinementResult)
        assert result.project_id == project_with_narrations.id
        assert len(result.scene_analyses) == 2
        # Called once per scene
        assert mock_llm.generate_json.call_count == 2

    def test_apply_modify_patch(self, project_with_narrations, mock_llm, temp_project_dir):
        """Test applying a ModifyScenePatch."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        patch = ModifyScenePatch(
            reason="Improve hook",
            priority="high",
            scene_id="scene1_hook",
            field_name="narration",
            old_value="Old text",
            new_value="New improved narration text.",
        )

        success = refiner.apply_patch(patch)
        assert success

        # Verify the file was updated
        narrations_path = temp_project_dir / "narration" / "narrations.json"
        with open(narrations_path) as f:
            data = json.load(f)

        scene1 = next(s for s in data["scenes"] if s["scene_id"] == "scene1_hook")
        assert scene1["narration"] == "New improved narration text."

    def test_apply_add_scene_patch(self, project_with_narrations, mock_llm, temp_project_dir):
        """Test applying an AddScenePatch."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        patch = AddScenePatch(
            reason="Fill gap between scenes",
            priority="high",
            insert_after_scene_id="scene1_hook",
            new_scene_id="scene1b_bridge",
            title="Bridge Scene",
            narration="This is the bridge content.",
            visual_description="Transition visual",
            duration_seconds=20.0,
        )

        success = refiner.apply_patch(patch)
        assert success

        # Verify the file was updated
        narrations_path = temp_project_dir / "narration" / "narrations.json"
        with open(narrations_path) as f:
            data = json.load(f)

        # New scene should be at index 1 (after scene1_hook)
        assert data["scenes"][1]["scene_id"] == "scene1b_bridge"
        assert data["scenes"][1]["narration"] == "This is the bridge content."

    def test_apply_expand_scene_patch(self, project_with_narrations, mock_llm, temp_project_dir):
        """Test applying an ExpandScenePatch."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        patch = ExpandScenePatch(
            reason="Cover concept more deeply",
            priority="medium",
            scene_id="scene1_hook",
            current_narration="Short narration",
            expanded_narration="Much longer expanded narration with more detail.",
            concepts_to_add=["concept1"],
            additional_duration_seconds=10.0,
        )

        success = refiner.apply_patch(patch)
        assert success

        # Verify the file was updated
        narrations_path = temp_project_dir / "narration" / "narrations.json"
        with open(narrations_path) as f:
            data = json.load(f)

        scene1 = next(s for s in data["scenes"] if s["scene_id"] == "scene1_hook")
        assert scene1["narration"] == "Much longer expanded narration with more detail."

    def test_apply_patch_scene_not_found(self, project_with_narrations, mock_llm):
        """Test applying patch to non-existent scene."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        patch = ModifyScenePatch(
            reason="Test",
            scene_id="nonexistent_scene",
            new_value="Test",
        )

        success = refiner.apply_patch(patch)
        assert not success

    def test_save_result(self, project_with_narrations, mock_llm):
        """Test saving refinement result."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        result = NarrationRefinementResult(
            project_id="test",
            overall_storytelling_score=7.5,
            total_issues_found=3,
        )

        output_path = refiner.save_result(result)
        assert output_path.exists()
        assert output_path.name == "narration_analysis.json"

        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data["overall_storytelling_score"] == 7.5

    def test_load_gap_analysis(self, project_with_narrations, mock_llm, temp_project_dir):
        """Test loading gap analysis from Phase 1."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        # First, should return None (no gap analysis exists)
        result = refiner.load_gap_analysis()
        assert result is None

        # Create a gap analysis file
        refinement_dir = temp_project_dir / "refinement"
        refinement_dir.mkdir(parents=True, exist_ok=True)
        gap_analysis_path = refinement_dir / "gap_analysis.json"

        gap_data = {
            "project_id": "test",
            "source_file": "input.md",
            "concepts": [],
            "narrative_gaps": [],
            "suggested_scenes": [],
            "patches": [],
            "overall_coverage_score": 80.0,
            "analysis_notes": "Good coverage",
        }
        with open(gap_analysis_path, "w") as f:
            json.dump(gap_data, f)

        # Now should load successfully
        result = refiner.load_gap_analysis()
        assert result is not None
        assert result.project_id == "test"
        assert result.overall_coverage_score == 80.0

    def test_format_gap_context(self, project_with_narrations, mock_llm):
        """Test formatting gap context for prompts."""
        refiner = ScriptRefiner(
            project=project_with_narrations,
            llm_provider=mock_llm,
            verbose=False,
        )

        # Create a gap analysis result with various gaps
        from src.refine.models import ConceptCoverage, ConceptDepth, NarrativeGap, SourceConcept

        gap_analysis = GapAnalysisResult(
            project_id="test",
            source_file="input.md",
            concepts=[
                ConceptCoverage(
                    concept=SourceConcept(name="Missing Concept", description="Test"),
                    depth=ConceptDepth.NOT_COVERED,
                ),
                ConceptCoverage(
                    concept=SourceConcept(name="Shallow Concept", description="Test", importance="high"),
                    depth=ConceptDepth.MENTIONED,
                ),
            ],
            narrative_gaps=[
                NarrativeGap(
                    from_scene_id="s1",
                    from_scene_title="Scene 1",
                    to_scene_id="s2",
                    to_scene_title="Scene 2",
                    gap_description="Missing transition",
                    severity="high",
                ),
            ],
        )

        context = refiner._format_gap_context(gap_analysis)

        assert "Missing Concept" in context
        assert "Shallow Concept" in context
        assert "Scene 1" in context
        assert "Missing transition" in context


class TestNarrationAnalysisPrompt:
    """Tests for the narration analysis prompt format."""

    def test_prompt_contains_required_placeholders(self):
        """Test that the prompt has required placeholders."""
        required = [
            "{scene_id}",
            "{scene_title}",
            "{duration_seconds}",
            "{expected_words}",
            "{actual_words}",
            "{prev_ending}",
            "{next_start}",
            "{gap_context}",  # Changed from {source_excerpt}
            "{narration}",
            "{principles}",
        ]
        for placeholder in required:
            assert placeholder in SINGLE_SCENE_ANALYSIS_PROMPT

    def test_prompt_requests_scores(self):
        """Test that the prompt requests all score types."""
        score_types = ["hook", "flow", "tension", "insight", "engagement", "accuracy", "length"]
        for score in score_types:
            assert score in SINGLE_SCENE_ANALYSIS_PROMPT

    def test_prompt_requests_issue_types(self):
        """Test that the prompt lists all issue types."""
        issue_types = [
            "weak_hook",
            "poor_transition",
            "missing_tension",
            "no_key_insight",
            "lacks_analogy",
            "no_emotional_beat",
            "wrong_length",
            "technical_inaccuracy",
        ]
        for issue_type in issue_types:
            assert issue_type in SINGLE_SCENE_ANALYSIS_PROMPT

    def test_prompt_requests_patch_output(self):
        """Test that the prompt requests patch output format."""
        assert "modify_scene" in SINGLE_SCENE_ANALYSIS_PROMPT
        assert "patch_type" in SINGLE_SCENE_ANALYSIS_PROMPT
        assert "new_value" in SINGLE_SCENE_ANALYSIS_PROMPT


class TestSystemPrompt:
    """Tests for the system prompt."""

    def test_mentions_3blue1brown_style(self):
        """Test that the system prompt mentions target style."""
        assert "3Blue1Brown" in NARRATION_ANALYSIS_SYSTEM_PROMPT or "Veritasium" in NARRATION_ANALYSIS_SYSTEM_PROMPT

    def test_mentions_patches(self):
        """Test that the system prompt mentions patches."""
        assert "patch" in NARRATION_ANALYSIS_SYSTEM_PROMPT.lower()

    def test_emphasizes_actionable_output(self):
        """Test that the system prompt emphasizes actionable output."""
        assert "actionable" in NARRATION_ANALYSIS_SYSTEM_PROMPT.lower()
