"""Tests for the shorts custom scene generator module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json

from src.short.custom_scene_generator import (
    ShortsCustomSceneGenerator,
    SHORTS_CONSTRAINTS,
    DEFAULT_REMOTION_RULES,
)
from src.short.models import ShortsStoryboard, ShortsBeat, ShortsVisual, VisualType


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def generator():
    """Create a ShortsCustomSceneGenerator instance."""
    return ShortsCustomSceneGenerator()


@pytest.fixture
def sample_word_timestamps():
    """Sample word timestamps for testing."""
    return [
        {"word": "Text", "start_seconds": 0.0, "end_seconds": 0.3},
        {"word": "models", "start_seconds": 0.4, "end_seconds": 0.7},
        {"word": "are", "start_seconds": 0.8, "end_seconds": 0.9},
        {"word": "simple", "start_seconds": 1.0, "end_seconds": 1.4},
        # Gap here - natural phrase break
        {"word": "But", "start_seconds": 2.5, "end_seconds": 2.7},
        {"word": "images", "start_seconds": 2.8, "end_seconds": 3.2},
        {"word": "are", "start_seconds": 3.3, "end_seconds": 3.4},
        {"word": "complex", "start_seconds": 3.5, "end_seconds": 4.0},
    ]


@pytest.fixture
def sample_word_timestamps_no_gaps():
    """Word timestamps without significant gaps."""
    return [
        {"word": "This", "start_seconds": 0.0, "end_seconds": 0.2},
        {"word": "is", "start_seconds": 0.25, "end_seconds": 0.35},
        {"word": "a", "start_seconds": 0.4, "end_seconds": 0.45},
        {"word": "continuous", "start_seconds": 0.5, "end_seconds": 0.9},
        {"word": "sentence", "start_seconds": 0.95, "end_seconds": 1.3},
        {"word": "without", "start_seconds": 1.35, "end_seconds": 1.6},
        {"word": "any", "start_seconds": 1.65, "end_seconds": 1.8},
        {"word": "pauses", "start_seconds": 1.85, "end_seconds": 2.2},
    ]


@pytest.fixture
def sample_visual():
    """Create a sample visual for testing."""
    return ShortsVisual(
        type=VisualType.BIG_NUMBER,
        primary_text="100",
        secondary_text="test",
    )


@pytest.fixture
def sample_storyboard(sample_visual):
    """Create a sample storyboard for testing."""
    return ShortsStoryboard(
        id="test_short",
        title="Test Short",
        total_duration_seconds=30.0,
        beats=[
            ShortsBeat(
                id="beat_1",
                start_seconds=0.0,
                end_seconds=10.0,
                visual=sample_visual,
                caption_text="Text models are simple But images are complex",
                visual_description="Show comparison between text and images",
                word_timestamps=[
                    {"word": "Text", "start_seconds": 0.0, "end_seconds": 0.3},
                    {"word": "models", "start_seconds": 0.4, "end_seconds": 0.7},
                ],
            ),
            ShortsBeat(
                id="beat_2",
                start_seconds=10.0,
                end_seconds=20.0,
                visual=sample_visual,
                caption_text="This is the second beat",
                visual_description="Show the second concept",
            ),
        ],
    )


# ============================================================================
# Remotion Skill Loading Tests
# ============================================================================


class TestLoadRemotionRules:
    """Tests for _load_remotion_rules method."""

    def test_loads_rules_from_skill_directory(self):
        """Test loading rules from a valid skill directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock skill directory structure
            skill_dir = Path(tmpdir) / ".claude" / "skills" / "remotion" / "rules"
            skill_dir.mkdir(parents=True)

            # Create mock rule files
            (skill_dir / "animations.md").write_text("# Animations\nUse interpolate for smooth animations.")
            (skill_dir / "timing.md").write_text("# Timing\nUse spring for natural motion.")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            rules = generator._load_remotion_rules(["animations.md", "timing.md"])

            assert "Animations" in rules
            assert "interpolate" in rules
            assert "Timing" in rules
            assert "spring" in rules

    def test_returns_fallback_when_skill_not_found(self):
        """Test fallback when skill directory doesn't exist."""
        generator = ShortsCustomSceneGenerator(
            remotion_skill_path=Path("/nonexistent/path"),
        )

        rules = generator._load_remotion_rules(["animations.md"])

        assert "not found" in rules.lower()

    def test_caches_loaded_rules(self):
        """Test that loaded rules are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "rules"
            skill_dir.mkdir(parents=True)
            (skill_dir / "animations.md").write_text("# Animations content")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            # Load twice
            generator._load_remotion_rules(["animations.md"])
            generator._load_remotion_rules(["animations.md"])

            # Should be cached
            assert "animations.md" in generator._remotion_rules_cache
            assert generator._remotion_rules_cache["animations.md"] == "# Animations content"

    def test_uses_default_rules_when_none_specified(self):
        """Test that DEFAULT_REMOTION_RULES is used when no rules specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "rules"
            skill_dir.mkdir(parents=True)

            # Create all default rule files
            for rule_file in DEFAULT_REMOTION_RULES:
                (skill_dir / rule_file).write_text(f"# {rule_file} content")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            rules = generator._load_remotion_rules()  # No args = use defaults

            for rule_file in DEFAULT_REMOTION_RULES:
                assert rule_file in rules

    def test_handles_missing_individual_rules(self):
        """Test handling when some rule files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "rules"
            skill_dir.mkdir(parents=True)

            # Only create one rule file
            (skill_dir / "animations.md").write_text("# Animations")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            # Request two files, only one exists
            rules = generator._load_remotion_rules(["animations.md", "nonexistent.md"])

            assert "Animations" in rules
            # Should not crash, just skip missing file


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt method."""

    def test_combines_remotion_rules_and_shorts_constraints(self):
        """Test that system prompt includes both Remotion rules and shorts constraints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "rules"
            skill_dir.mkdir(parents=True)
            (skill_dir / "animations.md").write_text("# Animation Rules\nUse interpolate.")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            prompt = generator._build_system_prompt(["animations.md"])

            # Should contain Remotion rules
            assert "Animation Rules" in prompt
            assert "interpolate" in prompt

            # Should contain shorts constraints
            assert "1080x1920" in prompt  # Vertical canvas
            assert "Visual area: Top 70%" in prompt
            assert "Dark Theme" in prompt

    def test_includes_shorts_constraints(self):
        """Test that shorts-specific constraints are included."""
        generator = ShortsCustomSceneGenerator(
            remotion_skill_path=Path("/nonexistent"),  # Force fallback
        )

        prompt = generator._build_system_prompt()

        # Check for shorts-specific content
        assert "YouTube Shorts" in prompt
        assert "1080x1920" in prompt
        assert "COLORS.backgroundGradient" in prompt
        assert "Phase-Based Animation" in prompt

    def test_prompt_structure(self):
        """Test the overall structure of the generated prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "rules"
            skill_dir.mkdir(parents=True)
            (skill_dir / "timing.md").write_text("# Timing content")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            prompt = generator._build_system_prompt(["timing.md"])

            # Should have section headers
            assert "Remotion Best Practices" in prompt
            assert "Your Task" in prompt


class TestShortsConstraintsContent:
    """Tests for the SHORTS_CONSTRAINTS constant."""

    def test_contains_canvas_dimensions(self):
        """Test that canvas dimensions are specified."""
        assert "1080x1920" in SHORTS_CONSTRAINTS
        assert "vertical" in SHORTS_CONSTRAINTS.lower()

    def test_contains_visual_area_constraint(self):
        """Test that visual area constraint is specified."""
        assert "Top 70%" in SHORTS_CONSTRAINTS
        assert "1344" in SHORTS_CONSTRAINTS  # 1920 * 0.7

    def test_contains_dark_theme_requirement(self):
        """Test that dark theme is required."""
        assert "Dark Theme" in SHORTS_CONSTRAINTS
        assert "COLORS.backgroundGradient" in SHORTS_CONSTRAINTS

    def test_contains_animation_speed_guidelines(self):
        """Test that fast animation guidelines are included."""
        assert "10-15 frames" in SHORTS_CONSTRAINTS
        assert "damping: 12" in SHORTS_CONSTRAINTS
        assert "stiffness: 120" in SHORTS_CONSTRAINTS

    def test_contains_typography_sizes(self):
        """Test that mobile typography sizes are specified."""
        assert "72-96px" in SHORTS_CONSTRAINTS  # Main text
        assert "48-64px" in SHORTS_CONSTRAINTS  # Secondary

    def test_contains_phase_based_animation_requirement(self):
        """Test that phase-based animation is required."""
        assert "Phase-Based Animation" in SHORTS_CONSTRAINTS
        assert "2-3 phases" in SHORTS_CONSTRAINTS


# ============================================================================
# Phrase Break Detection Tests
# ============================================================================


class TestIdentifyPhraseBreaks:
    """Tests for _identify_phrase_breaks method."""

    def test_detects_gap_based_breaks(self, generator, sample_word_timestamps):
        """Test that gaps > 0.7s are detected as phrase breaks."""
        breaks = generator._identify_phrase_breaks(sample_word_timestamps, 4.0)

        # Should find the gap between "simple" (ends 1.4) and "But" (starts 2.5)
        assert len(breaks) >= 1
        # First break should be after "simple" (index 3)
        word_idx, timestamp, reason = breaks[0]
        assert word_idx == 3
        assert "pause" in reason.lower()

    def test_falls_back_to_equal_division(self, generator, sample_word_timestamps_no_gaps):
        """Test fallback to equal word count division when no gaps."""
        breaks = generator._identify_phrase_breaks(sample_word_timestamps_no_gaps, 2.5)

        # With 8 words and no gaps, should divide into thirds
        assert len(breaks) >= 1
        # Breaks should be at word indices that divide roughly into thirds
        for word_idx, timestamp, reason in breaks:
            assert "equal division" in reason

    def test_handles_short_timestamps(self, generator):
        """Test handling of very short word lists."""
        short_timestamps = [
            {"word": "Hello", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "world", "start_seconds": 0.6, "end_seconds": 1.0},
        ]
        breaks = generator._identify_phrase_breaks(short_timestamps, 1.0)

        # With only 2 words, may not have meaningful breaks
        assert isinstance(breaks, list)

    def test_handles_empty_timestamps(self, generator):
        """Test handling of empty word list."""
        breaks = generator._identify_phrase_breaks([], 5.0)
        assert breaks == []


# ============================================================================
# Phase Timing Calculation Tests
# ============================================================================


class TestCalculatePhaseTiming:
    """Tests for _calculate_phase_timing method."""

    def test_generates_phase_timing_from_breaks(self, generator, sample_word_timestamps):
        """Test that phase timing is generated from phrase breaks."""
        breaks = [(3, 1.4, "pause of 1.1s")]  # Break after "simple"
        total_frames = 120  # 4 seconds at 30fps

        result = generator._calculate_phase_timing(breaks, sample_word_timestamps, total_frames)

        # Should contain phase information
        assert "Phase 1" in result
        assert "Phase 2" in result
        # Should contain frame numbers
        assert "frames" in result.lower()
        # Should contain code snippet
        assert "const phase1End" in result

    def test_handles_no_breaks(self, generator, sample_word_timestamps):
        """Test handling when no breaks are found."""
        breaks = []
        total_frames = 120

        result = generator._calculate_phase_timing(breaks, sample_word_timestamps, total_frames)

        # Should return single phase
        assert "Phase 1" in result
        assert f"frames 0-{total_frames}" in result

    def test_handles_multiple_breaks(self, generator, sample_word_timestamps):
        """Test handling of multiple phrase breaks."""
        breaks = [
            (1, 0.7, "pause"),
            (5, 3.2, "pause"),
        ]
        total_frames = 120

        result = generator._calculate_phase_timing(breaks, sample_word_timestamps, total_frames)

        # Should have 3 phases (2 breaks = 3 segments)
        assert "Phase 1" in result
        assert "Phase 2" in result
        assert "Phase 3" in result
        # Should have phase2End in code
        assert "phase2End" in result


# ============================================================================
# Word Timestamps Formatting Tests
# ============================================================================


class TestFormatWordTimestamps:
    """Tests for _format_word_timestamps method."""

    def test_formats_timestamps_with_phases(self, generator, sample_word_timestamps):
        """Test formatting of word timestamps with phase recommendations."""
        result = generator._format_word_timestamps(
            sample_word_timestamps,
            "Text models are simple But images are complex",
            4.0,  # duration
        )

        # Should contain word timeline
        assert '"Text"' in result
        assert '"simple"' in result
        # Should contain phase recommendations
        assert "RECOMMENDED PHASE TIMING" in result
        # Should contain frame numbers
        assert "frame" in result.lower()

    def test_handles_missing_timestamps(self, generator):
        """Test handling when no timestamps provided."""
        result = generator._format_word_timestamps([], "Some text", 5.0)

        # Should indicate timestamps not available
        assert "NOT AVAILABLE" in result
        # Should still provide phase estimates
        assert "RECOMMENDED PHASE TIMING" in result
        # Check for phase timing code (camelCase)
        assert "phase1End" in result

    def test_calculates_frames_correctly(self, generator):
        """Test that frame calculations are correct (30fps)."""
        timestamps = [
            {"word": "Test", "start_seconds": 1.0, "end_seconds": 1.5},
        ]
        result = generator._format_word_timestamps(timestamps, "Test", 2.0)

        # 1.0 seconds * 30fps = frame 30
        assert "frame 30" in result


# ============================================================================
# Vertical Styles Generation Tests
# ============================================================================


class TestGenerateVerticalStyles:
    """Tests for _generate_vertical_styles method."""

    def test_generates_dark_theme_styles(self, generator):
        """Test that generated styles use dark theme."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            generator._generate_vertical_styles(scenes_dir, "Test Short")

            styles_path = scenes_dir / "styles.ts"
            assert styles_path.exists()

            content = styles_path.read_text()

            # Should have dark background
            assert "#0a0a0f" in content
            # Should have backgroundGradient
            assert "backgroundGradient" in content
            assert "linear-gradient" in content
            # Should have light text
            assert 'text: "#ffffff"' in content or "text: '#ffffff'" in content
            # Should have dark theme comment
            assert "DARK THEME" in content.upper() or "dark theme" in content.lower()

    def test_generates_layout_constants(self, generator):
        """Test that layout constants are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            generator._generate_vertical_styles(scenes_dir, "Test Short")

            content = (scenes_dir / "styles.ts").read_text()

            # Should have canvas dimensions
            assert "1080" in content  # width
            assert "1920" in content  # height
            # Should have visual area height (70%)
            assert "1344" in content or "0.7" in content
            # Should export COLORS and FONTS
            assert "export const COLORS" in content
            assert "export const FONTS" in content

    def test_generates_animation_helpers(self, generator):
        """Test that animation helper constants are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            generator._generate_vertical_styles(scenes_dir, "Test Short")

            content = (scenes_dir / "styles.ts").read_text()

            # Should have animation config
            assert "ANIMATION" in content
            # Should have spring config
            assert "damping" in content
            assert "stiffness" in content


# ============================================================================
# Index Generation Tests
# ============================================================================


class TestGenerateIndex:
    """Tests for _generate_index method."""

    def test_generates_valid_index(self, generator):
        """Test that a valid index.ts file is generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            components = [
                {"beat_id": "beat_1", "component_name": "Beat1Scene", "filename": "Beat1Scene.tsx"},
                {"beat_id": "beat_2", "component_name": "Beat2Scene", "filename": "Beat2Scene.tsx"},
            ]

            generator._generate_index(scenes_dir, components)

            index_path = scenes_dir / "index.ts"
            assert index_path.exists()

            content = index_path.read_text()

            # Should have imports
            assert 'import { Beat1Scene }' in content
            assert 'import { Beat2Scene }' in content
            # Should have registry entries
            assert '"beat_1": Beat1Scene' in content
            assert '"beat_2": Beat2Scene' in content
            # Should have getBeatScene function
            assert "getBeatScene" in content

    def test_handles_empty_components(self, generator):
        """Test handling of empty component list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            generator._generate_index(scenes_dir, [])

            index_path = scenes_dir / "index.ts"
            assert index_path.exists()

            content = index_path.read_text()
            # Should still have the structure but empty
            assert "BEAT_SCENE_REGISTRY" in content


# ============================================================================
# Code Extraction Tests
# ============================================================================


class TestExtractCode:
    """Tests for _extract_code method."""

    def test_extracts_typescript_code_block(self, generator):
        """Test extraction of TypeScript code blocks."""
        response = '''Here is the component:

```typescript
import React from "react";

export const TestScene = () => {
  return <div>Test</div>;
};
```

That's all!'''

        code = generator._extract_code(response)

        assert code is not None
        assert "import React" in code
        assert "TestScene" in code
        assert "```" not in code

    def test_extracts_tsx_code_block(self, generator):
        """Test extraction of TSX code blocks."""
        response = '''```tsx
export const Component = () => <div />;
```'''

        code = generator._extract_code(response)
        assert code is not None
        assert "Component" in code

    def test_extracts_plain_code_block(self, generator):
        """Test extraction of plain code blocks."""
        response = '''```
const x = 1;
```'''

        code = generator._extract_code(response)
        assert code is not None
        assert "const x = 1" in code

    def test_handles_code_without_blocks(self, generator):
        """Test handling of response that looks like code without blocks."""
        response = '''import React from "react";

export const Scene = () => {
  return <div>Test</div>;
};'''

        code = generator._extract_code(response)
        assert code is not None
        assert "import" in code
        assert "export" in code

    def test_returns_none_for_non_code(self, generator):
        """Test that non-code responses return None."""
        response = "This is just a regular text response without any code."
        code = generator._extract_code(response)
        assert code is None


# ============================================================================
# Integration Tests
# ============================================================================


class TestGenerateAllScenes:
    """Integration tests for generate_all_scenes method."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Mock the LLM provider."""
        with patch("src.short.custom_scene_generator.ClaudeCodeLLMProvider") as mock:
            instance = MagicMock()
            instance.generate_with_file_access.return_value = MagicMock(
                success=True,
                response='''```typescript
import React from "react";
import { AbsoluteFill } from "remotion";

export const Beat1Scene = () => <AbsoluteFill />;
```''',
            )
            mock.return_value = instance
            yield mock

    def test_generates_styles_file(self, generator, sample_storyboard):
        """Test that styles.ts is generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)

            # Skip actual scene generation by removing visual descriptions
            for beat in sample_storyboard.beats:
                beat.visual_description = ""

            generator.generate_all_scenes(sample_storyboard, None, scenes_dir)

            styles_path = scenes_dir / "styles.ts"
            assert styles_path.exists()

    def test_skips_cta_beat(self, generator, sample_storyboard, sample_visual, mock_llm_provider):
        """Test that CTA beats are skipped."""
        sample_storyboard.beats.append(
            ShortsBeat(
                id="cta",
                start_seconds=20.0,
                end_seconds=30.0,
                visual=sample_visual,
                caption_text="Subscribe for more!",
                visual_description="CTA animation",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            results = generator.generate_all_scenes(sample_storyboard, None, scenes_dir)

            # CTA should not be in generated scenes
            scene_ids = [s["beat_id"] for s in results["scenes"]]
            assert "cta" not in scene_ids

    def test_skips_beats_without_visual_description(self, generator, sample_storyboard):
        """Test that beats without visual_description are skipped."""
        # Remove visual descriptions
        sample_storyboard.beats[0].visual_description = ""
        sample_storyboard.beats[1].visual_description = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            scenes_dir = Path(tmpdir)
            results = generator.generate_all_scenes(sample_storyboard, None, scenes_dir)

            # No scenes should be generated
            assert len(results["scenes"]) == 0

    def test_uses_remotion_skill_when_available(self, sample_storyboard, sample_visual):
        """Test that Remotion skill rules are loaded when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock skill directory
            skill_dir = Path(tmpdir) / "skills" / "remotion" / "rules"
            skill_dir.mkdir(parents=True)
            (skill_dir / "animations.md").write_text("# Custom Animation Rules\nThese are project-specific rules.")

            generator = ShortsCustomSceneGenerator(
                remotion_skill_path=skill_dir,
            )

            prompt = generator._build_system_prompt(["animations.md"])

            # Should include the custom rules
            assert "Custom Animation Rules" in prompt
            assert "project-specific" in prompt

    def test_generator_works_without_skill_directory(self, sample_storyboard):
        """Test that generator works even if skill directory is missing."""
        generator = ShortsCustomSceneGenerator(
            remotion_skill_path=Path("/definitely/not/a/real/path"),
        )

        # Should not raise, just use fallback
        prompt = generator._build_system_prompt()

        # Should still have shorts constraints
        assert "1080x1920" in prompt
        assert "Dark Theme" in prompt
