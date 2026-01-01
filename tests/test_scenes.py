"""Tests for scene generation module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.scenes.generator import (
    SceneGenerator,
    SCENE_SYSTEM_PROMPT,
    SCENE_GENERATION_PROMPT,
    STYLES_TEMPLATE,
    INDEX_TEMPLATE,
)


class TestSceneGeneratorHelpers:
    """Tests for SceneGenerator helper methods."""

    @pytest.fixture
    def generator(self):
        return SceneGenerator()

    def test_title_to_component_name_simple(self, generator):
        """Test simple title conversion."""
        assert generator._title_to_component_name("The Hook") == "TheHookScene"

    def test_title_to_component_name_with_special_chars(self, generator):
        """Test title with special characters."""
        assert generator._title_to_component_name("What's Next?") == "WhatsNextScene"

    def test_title_to_component_name_numbers(self, generator):
        """Test title with numbers."""
        assert generator._title_to_component_name("Phase 1 Introduction") == "Phase1IntroductionScene"

    def test_title_to_component_name_single_word(self, generator):
        """Test single word title."""
        assert generator._title_to_component_name("Conclusion") == "ConclusionScene"

    def test_component_to_registry_key_simple(self, generator):
        """Test simple component name to key conversion."""
        assert generator._component_to_registry_key("TheHookScene") == "the_hook"

    def test_component_to_registry_key_complex(self, generator):
        """Test complex component name to key conversion."""
        # Note: consecutive capitals are not split (KV stays together)
        assert generator._component_to_registry_key("KVCacheExplanationScene") == "kvcache_explanation"

    def test_title_to_registry_name(self, generator):
        """Test registry name generation."""
        assert generator._title_to_registry_name("LLM Image Understanding") == "LLM_IMAGE_UNDERSTANDING_SCENES"

    def test_title_to_registry_name_long(self, generator):
        """Test registry name generation with long title."""
        result = generator._title_to_registry_name("A Very Long Project Title Here")
        assert result == "A_VERY_LONG_SCENES"

    def test_extract_code_from_markdown(self, generator):
        """Test code extraction from markdown response."""
        response = '''Here's the code:

```typescript
import React from "react";
export const TestScene = () => <div>Test</div>;
```

That's the component.'''
        code = generator._extract_code(response)
        assert code is not None
        assert "import React" in code
        assert "TestScene" in code

    def test_extract_code_from_tsx_block(self, generator):
        """Test code extraction from tsx code block."""
        response = '''```tsx
import React from "react";
export const TestScene = () => <div>Test</div>;
```'''
        code = generator._extract_code(response)
        assert code is not None
        assert "TestScene" in code

    def test_extract_code_plain_code(self, generator):
        """Test code extraction when response is plain code."""
        response = '''import React from "react";
export const TestScene = () => <div>Test</div>;'''
        code = generator._extract_code(response)
        assert code is not None
        assert "import" in code
        assert "export" in code

    def test_extract_code_no_code(self, generator):
        """Test code extraction when no code present."""
        response = "This is just a text response without any code."
        code = generator._extract_code(response)
        assert code is None


class TestStylesTemplate:
    """Tests for styles template generation."""

    def test_styles_template_has_colors(self):
        """Test that styles template includes colors."""
        content = STYLES_TEMPLATE.format(project_title="Test Project")
        assert "COLORS" in content
        assert "#00d9ff" in content  # primary
        assert "#ff6b35" in content  # secondary

    def test_styles_template_has_typography(self):
        """Test that styles template includes typography."""
        content = STYLES_TEMPLATE.format(project_title="Test Project")
        assert "TYPOGRAPHY" in content
        assert "fontSize" in content

    def test_styles_template_has_helpers(self):
        """Test that styles template includes helper functions."""
        content = STYLES_TEMPLATE.format(project_title="Test Project")
        assert "getSceneIndicatorStyle" in content
        assert "getScale" in content

    def test_styles_template_project_title(self):
        """Test that project title is included."""
        content = STYLES_TEMPLATE.format(project_title="My Custom Project")
        assert "My Custom Project" in content


class TestIndexTemplate:
    """Tests for index template generation."""

    def test_index_template_structure(self):
        """Test that index template has correct structure."""
        content = INDEX_TEMPLATE.format(
            project_title="Test Project",
            imports='import { TestScene } from "./TestScene";',
            exports='export { TestScene } from "./TestScene";',
            registry_name="TEST_SCENES",
            registry_entries='  test: TestScene,',
        )
        assert "TestScene" in content
        assert "TEST_SCENES" in content
        assert "getScene" in content
        assert "getAvailableSceneTypes" in content


class TestSceneGeneratorWithMocks:
    """Tests for SceneGenerator with mocked LLM."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory with script."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create script directory and file
        script_dir = project_dir / "script"
        script_dir.mkdir()

        script_data = {
            "title": "Test Video",
            "total_duration_seconds": 120,
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Opening Hook",
                    "voiceover": "This is the opening narration.",
                    "visual_description": "Show an animated title card.",
                    "key_elements": ["title", "animation"],
                    "duration_seconds": 20,
                },
                {
                    "scene_id": 2,
                    "scene_type": "explanation",
                    "title": "Core Concept",
                    "voiceover": "Here's how it works.",
                    "visual_description": "Diagram showing the process.",
                    "key_elements": ["diagram", "arrows"],
                    "duration_seconds": 30,
                },
            ],
        }

        with open(script_dir / "script.json", "w") as f:
            json.dump(script_data, f)

        return project_dir

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response with scene code."""
        return MagicMock(
            success=True,
            response='''import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill>Test</AbsoluteFill>;
};''',
            modified_files=[],
        )

    def test_generate_styles(self, temp_project_dir):
        """Test styles.ts generation."""
        generator = SceneGenerator()
        scenes_dir = temp_project_dir / "scenes"
        scenes_dir.mkdir()

        generator._generate_styles(scenes_dir, "Test Project")

        styles_path = scenes_dir / "styles.ts"
        assert styles_path.exists()

        content = styles_path.read_text()
        assert "COLORS" in content
        assert "Test Project" in content

    def test_generate_index(self, temp_project_dir):
        """Test index.ts generation."""
        generator = SceneGenerator()
        scenes_dir = temp_project_dir / "scenes"
        scenes_dir.mkdir()

        scenes = [
            {"scene_number": 1, "title": "Hook", "component_name": "HookScene", "filename": "HookScene.tsx", "scene_type": "hook"},
            {"scene_number": 2, "title": "Explanation", "component_name": "ExplanationScene", "filename": "ExplanationScene.tsx", "scene_type": "explanation"},
        ]

        generator._generate_index(scenes_dir, scenes, "Test Video")

        index_path = scenes_dir / "index.ts"
        assert index_path.exists()

        content = index_path.read_text()
        assert "HookScene" in content
        assert "ExplanationScene" in content
        assert "TEST_VIDEO_SCENES" in content

    @patch("src.scenes.generator.ClaudeCodeLLMProvider")
    def test_generate_scene_creates_file(self, mock_llm_class, temp_project_dir, mock_llm_response):
        """Test that scene generation creates a file."""
        mock_llm = MagicMock()
        mock_llm.generate_with_file_access.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm

        generator = SceneGenerator()
        scenes_dir = temp_project_dir / "scenes"
        scenes_dir.mkdir()

        scene = {
            "title": "Test Scene",
            "scene_type": "hook",
            "duration_seconds": 20,
            "voiceover": "Test narration",
            "visual_description": "Test visual",
            "key_elements": ["element1"],
        }

        result = generator._generate_scene(
            scene=scene,
            scene_number=1,
            scenes_dir=scenes_dir,
            example_scene="// Example scene code",
        )

        assert result["component_name"] == "TestSceneScene"
        assert result["filename"] == "TestSceneScene.tsx"
        assert (scenes_dir / "TestSceneScene.tsx").exists()

    @patch("src.scenes.generator.ClaudeCodeLLMProvider")
    def test_generate_all_scenes(self, mock_llm_class, temp_project_dir, mock_llm_response):
        """Test full scene generation pipeline."""
        mock_llm = MagicMock()
        mock_llm.generate_with_file_access.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm

        generator = SceneGenerator()

        results = generator.generate_all_scenes(
            project_dir=temp_project_dir,
            force=True,
        )

        assert len(results["scenes"]) == 2
        assert len(results["errors"]) == 0

        scenes_dir = temp_project_dir / "scenes"
        assert (scenes_dir / "styles.ts").exists()
        assert (scenes_dir / "index.ts").exists()

    def test_generate_scenes_no_script_error(self, tmp_path):
        """Test error when script doesn't exist."""
        project_dir = tmp_path / "empty-project"
        project_dir.mkdir()

        generator = SceneGenerator()

        with pytest.raises(FileNotFoundError) as exc_info:
            generator.generate_all_scenes(project_dir=project_dir)

        assert "Script not found" in str(exc_info.value)

    def test_generate_scenes_existing_no_force(self, temp_project_dir):
        """Test error when scenes exist without force flag."""
        scenes_dir = temp_project_dir / "scenes"
        scenes_dir.mkdir()
        (scenes_dir / "ExistingScene.tsx").write_text("// existing")

        generator = SceneGenerator()

        with pytest.raises(FileExistsError) as exc_info:
            generator.generate_all_scenes(project_dir=temp_project_dir)

        assert "Use --force" in str(exc_info.value)


class TestScenePrompts:
    """Tests for scene generation prompts."""

    def test_system_prompt_has_remotion_guidance(self):
        """Test system prompt includes Remotion guidance."""
        assert "Remotion" in SCENE_SYSTEM_PROMPT
        assert "useCurrentFrame" in SCENE_SYSTEM_PROMPT
        assert "interpolate" in SCENE_SYSTEM_PROMPT

    def test_system_prompt_has_animation_principles(self):
        """Test system prompt includes animation principles."""
        assert "Frame-based timing" in SCENE_SYSTEM_PROMPT
        assert "spring" in SCENE_SYSTEM_PROMPT

    def test_system_prompt_has_color_guidance(self):
        """Test system prompt includes color guidance."""
        assert "#00d9ff" in SCENE_SYSTEM_PROMPT
        assert "primary" in SCENE_SYSTEM_PROMPT

    def test_generation_prompt_template_has_placeholders(self):
        """Test generation prompt has required placeholders."""
        assert "{scene_number}" in SCENE_GENERATION_PROMPT
        assert "{title}" in SCENE_GENERATION_PROMPT
        assert "{voiceover}" in SCENE_GENERATION_PROMPT
        assert "{visual_description}" in SCENE_GENERATION_PROMPT
        assert "{component_name}" in SCENE_GENERATION_PROMPT

    def test_generation_prompt_formatting(self):
        """Test that generation prompt can be formatted."""
        formatted = SCENE_GENERATION_PROMPT.format(
            scene_number=1,
            title="Test Scene",
            scene_type="hook",
            duration=20,
            total_frames=600,
            voiceover="Test narration",
            visual_description="Test visual",
            elements="- element1\n- element2",
            component_name="TestScene",
            example_scene="// Example code",
            output_path="/path/to/scene.tsx",
        )
        assert "Test Scene" in formatted
        assert "TestScene" in formatted
        assert "600 frames" in formatted


class TestSceneGeneratorLoadExample:
    """Tests for loading example scenes."""

    def test_load_example_from_llm_inference(self):
        """Test loading example from llm-inference project."""
        # This test only works if the llm-inference project exists
        generator = SceneGenerator()
        example = generator._load_example_scene()

        # Should find an example or return placeholder
        assert example is not None
        assert len(example) > 0

    def test_load_example_from_custom_dir(self, tmp_path):
        """Test loading example from custom directory."""
        example_dir = tmp_path / "examples"
        example_dir.mkdir()
        (example_dir / "TestScene.tsx").write_text("// Test scene code")

        generator = SceneGenerator()
        example = generator._load_example_scene(example_dir)

        assert "Test scene code" in example

    def test_load_example_empty_dir(self, tmp_path):
        """Test loading example from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        generator = SceneGenerator()
        example = generator._load_example_scene(empty_dir)

        assert "No example scene available" in example


class TestSceneGeneratorOldFormat:
    """Tests for handling old script format with visual_cue."""

    @pytest.fixture
    def old_format_script(self, tmp_path):
        """Create script with old visual_cue format."""
        project_dir = tmp_path / "old-format"
        project_dir.mkdir()
        script_dir = project_dir / "script"
        script_dir.mkdir()

        script_data = {
            "title": "Old Format Video",
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "Hook Scene",
                    "voiceover": "Test narration",
                    "visual_cue": {
                        "description": "Old format visual description",
                        "visual_type": "animation",
                        "elements": ["element1", "element2"],
                        "duration_seconds": 20,
                    },
                    "duration_seconds": 20,
                },
            ],
        }

        with open(script_dir / "script.json", "w") as f:
            json.dump(script_data, f)

        return project_dir

    @patch("src.scenes.generator.ClaudeCodeLLMProvider")
    def test_handles_old_visual_cue_format(self, mock_llm_class, old_format_script):
        """Test that old visual_cue format is handled correctly."""
        mock_llm = MagicMock()
        mock_llm.generate_with_file_access.return_value = MagicMock(
            success=True,
            response='import React from "react"; export const HookSceneScene = () => null;',
        )
        mock_llm_class.return_value = mock_llm

        generator = SceneGenerator()
        results = generator.generate_all_scenes(
            project_dir=old_format_script,
            force=True,
        )

        assert len(results["scenes"]) == 1
        assert len(results["errors"]) == 0

        # Verify the prompt included the visual description
        call_args = mock_llm.generate_with_file_access.call_args
        prompt = call_args[0][0]
        assert "Old format visual description" in prompt
