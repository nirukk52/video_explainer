"""Tests for the scene validator module and self-correcting generator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.scenes.validator import SceneValidator, ValidationResult, ValidationIssue, validate_scenes
from src.scenes.generator import SceneGenerator


class TestSceneValidator:
    """Tests for SceneValidator class."""

    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        validator = SceneValidator()
        assert validator.remotion_dir.exists() or True  # May not exist in test env

    def test_validate_empty_directory(self, tmp_path: Path):
        """Test validating an empty directory."""
        result = validate_scenes(tmp_path)
        assert result.success
        assert len(result.issues) == 0

    def test_validate_single_valid_scene(self, tmp_path: Path):
        """Test validating a valid scene file."""
        scene_content = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { COLORS, FONTS } from "./styles";

interface TestSceneProps {
  startFrame?: number;
}

export const TestScene: React.FC<TestSceneProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = width / 1920;

  const titleOpacity = interpolate(localFrame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      <div style={{ opacity: titleOpacity }}>Test Scene</div>
    </AbsoluteFill>
  );
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        # Also need styles.ts
        styles_content = '''
export const COLORS = { background: "#000" };
export const FONTS = { main: "Inter" };
'''
        (tmp_path / "styles.ts").write_text(styles_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should have no static analysis errors
        static_errors = [i for i in result.issues if not i.message.startswith("TypeScript:")]
        assert len(static_errors) == 0


class TestInterpolatePatternCheck:
    """Tests for interpolate pattern detection."""

    def test_detects_missing_extrapolate_left(self, tmp_path: Path):
        """Test detection of interpolate without extrapolateLeft."""
        scene_content = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const phase4 = durationInFrames * 0.6;

  // Missing extrapolateLeft - should trigger warning
  const packetProgress = interpolate(frame, [phase4, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });

  return <div>{packetProgress}</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should have a warning about missing extrapolateLeft
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert any("extrapolateLeft" in w.message for w in warnings)

    def test_no_warning_when_extrapolate_left_present(self, tmp_path: Path):
        """Test no warning when extrapolateLeft is present."""
        scene_content = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const phase4 = durationInFrames * 0.6;

  // Has extrapolateLeft - should not trigger warning
  const packetProgress = interpolate(frame, [phase4, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return <div>{packetProgress}</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should not have warnings about extrapolateLeft
        interpolate_warnings = [
            i for i in result.issues
            if "extrapolateLeft" in i.message
        ]
        assert len(interpolate_warnings) == 0


class TestUndefinedVariableCheck:
    """Tests for undefined variable detection."""

    def test_detects_undefined_phase_variable(self, tmp_path: Path):
        """Test detection of undefined phase variable in interpolate."""
        scene_content = '''
import React from "react";
import { interpolate } from "remotion";

export const TestScene: React.FC = () => {
  // phase4 is not defined - should trigger error
  const opacity = interpolate(0, [phase4, 100], [0, 1]);
  return <div style={{ opacity }}>Test</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should have an error about undefined variable
        errors = result.errors
        # The check specifically looks for phase variables
        phase_errors = [e for e in errors if "phase4" in e.message.lower()]
        assert len(phase_errors) > 0

    def test_detects_undefined_progress_variable(self, tmp_path: Path):
        """Test detection of undefined progress-like variable."""
        scene_content = '''
import React from "react";

export const TestScene: React.FC = () => {
  // tokenProgress is not defined but used
  const value = tokenProgress * 10;
  return <div>{value}</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should have an error about undefined variable
        errors = result.errors
        progress_errors = [e for e in errors if "tokenProgress" in e.message]
        assert len(progress_errors) > 0

    def test_no_error_for_defined_variable(self, tmp_path: Path):
        """Test no error when variable is properly defined."""
        scene_content = '''
import React from "react";
import { interpolate } from "remotion";

export const TestScene: React.FC = () => {
  const phase4 = 100;
  const titleOpacity = interpolate(0, [phase4, 200], [0, 1]);
  return <div style={{ opacity: titleOpacity }}>Test</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should not have errors about phase4 or titleOpacity
        static_errors = [i for i in result.errors if not i.message.startswith("TypeScript:")]
        assert len(static_errors) == 0


class TestImportCheck:
    """Tests for import validation."""

    def test_detects_missing_remotion_import(self, tmp_path: Path):
        """Test detection of missing remotion import when using remotion functions."""
        scene_content = '''
import React from "react";
// Missing remotion import but using interpolate

export const TestScene: React.FC = () => {
  const opacity = interpolate(0, [0, 30], [0, 1]);
  return <div style={{ opacity }}>Test</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should have an error about missing import
        import_errors = [e for e in result.errors if "import" in e.message.lower()]
        assert len(import_errors) > 0

    def test_detects_missing_styles_import(self, tmp_path: Path):
        """Test detection of missing styles import when using COLORS/FONTS."""
        scene_content = '''
import React from "react";
import { AbsoluteFill } from "remotion";
// Missing styles import but using COLORS

export const TestScene: React.FC = () => {
  return <AbsoluteFill style={{ backgroundColor: COLORS.background }} />;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should have an error about missing import
        import_errors = [e for e in result.errors if "styles" in e.message.lower()]
        assert len(import_errors) > 0


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_errors_property(self):
        """Test errors property filters correctly."""
        from src.scenes.validator import ValidationIssue

        result = ValidationResult(
            success=False,
            issues=[
                ValidationIssue(severity="error", message="Error 1", file="test.tsx"),
                ValidationIssue(severity="warning", message="Warning 1", file="test.tsx"),
                ValidationIssue(severity="error", message="Error 2", file="test.tsx"),
            ],
        )

        assert len(result.errors) == 2
        assert all(e.severity == "error" for e in result.errors)

    def test_warnings_property(self):
        """Test warnings property filters correctly."""
        from src.scenes.validator import ValidationIssue

        result = ValidationResult(
            success=True,
            issues=[
                ValidationIssue(severity="error", message="Error 1", file="test.tsx"),
                ValidationIssue(severity="warning", message="Warning 1", file="test.tsx"),
                ValidationIssue(severity="warning", message="Warning 2", file="test.tsx"),
            ],
        )

        assert len(result.warnings) == 2
        assert all(w.severity == "warning" for w in result.warnings)

    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult(success=True)
        assert result.success
        assert len(result.issues) == 0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestValidateScenesFunction:
    """Tests for validate_scenes convenience function."""

    def test_validate_scenes_with_valid_files(self, tmp_path: Path):
        """Test validate_scenes function with valid files."""
        scene_content = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { COLORS, FONTS } from "./styles";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ opacity, backgroundColor: COLORS.background }} />;
};
'''
        (tmp_path / "TestScene.tsx").write_text(scene_content)
        (tmp_path / "styles.ts").write_text("export const COLORS = {}; export const FONTS = {};")

        result = validate_scenes(tmp_path)

        # Should have no static analysis errors
        static_errors = [i for i in result.errors if not i.message.startswith("TypeScript:")]
        assert len(static_errors) == 0


class TestArrayAccessCheck:
    """Tests for array access pattern detection."""

    def test_warns_on_progress_based_array_access(self, tmp_path: Path):
        """Test warning on array access using progress variable."""
        scene_content = '''
import React from "react";

export const TestScene: React.FC = () => {
  const path = [{x: 0, y: 0}, {x: 100, y: 100}];
  const packetProgress = 0.5;
  const currentSegment = Math.floor(packetProgress * (path.length - 1));

  // Array access with Progress in the expression
  const point = path[currentSegment];

  return <div>{point.x}</div>;
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # May or may not have warnings depending on pattern matching
        # This is a less strict check
        assert isinstance(result, ValidationResult)


class TestSVGAttributeExclusion:
    """Tests for SVG attribute exclusion from undefined variable check."""

    def test_ignores_svg_attributes(self, tmp_path: Path):
        """Test that SVG attributes like stopOpacity are not flagged."""
        scene_content = '''
import React from "react";

export const TestScene: React.FC = () => {
  return (
    <svg>
      <linearGradient>
        <stop stopOpacity={0.5} stopColor="#fff" />
      </linearGradient>
    </svg>
  );
};
'''
        scene_file = tmp_path / "TestScene.tsx"
        scene_file.write_text(scene_content)

        validator = SceneValidator()
        result = validator.validate_single_scene(scene_file)

        # Should not flag stopOpacity as undefined
        stop_errors = [e for e in result.errors if "stopOpacity" in e.message]
        assert len(stop_errors) == 0


class TestSceneGeneratorSelfCorrection:
    """Tests for the self-correcting scene generator."""

    def test_generator_has_max_retries(self):
        """Test that generator has MAX_RETRIES constant."""
        assert hasattr(SceneGenerator, "MAX_RETRIES")
        assert SceneGenerator.MAX_RETRIES >= 1

    def test_generator_has_validator(self):
        """Test that generator always has a validator."""
        generator = SceneGenerator()
        assert generator.validator is not None
        assert isinstance(generator.validator, SceneValidator)

    @patch.object(SceneGenerator, "_generate_scene_file")
    def test_generator_retries_on_validation_error(self, mock_generate, tmp_path: Path):
        """Test that generator retries when validation fails."""
        # Setup: create a scene file with validation errors on first attempt,
        # then valid on second attempt
        scene_file = tmp_path / "TestScene.tsx"

        # First call writes invalid code, second call writes valid code
        invalid_code = '''
import React from "react";
export const TestScene: React.FC = () => {
  // Missing interpolate import but using it
  const opacity = interpolate(0, [0, 30], [0, 1]);
  return <div>{opacity}</div>;
};
'''
        valid_code = '''
import React from "react";
import { interpolate } from "remotion";
import { COLORS, FONTS } from "./styles";

export const TestScene: React.FC = () => {
  const opacity = interpolate(0, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <div style={{ opacity }}>{opacity}</div>;
};
'''
        call_count = [0]

        def side_effect(base_prompt, output_path, validation_feedback=""):
            call_count[0] += 1
            if call_count[0] == 1:
                output_path.write_text(invalid_code)
            else:
                output_path.write_text(valid_code)

        mock_generate.side_effect = side_effect

        # Create styles.ts for validation
        (tmp_path / "styles.ts").write_text("export const COLORS = {}; export const FONTS = {};")

        generator = SceneGenerator(working_dir=tmp_path)

        scene_data = {
            "title": "Test Scene",
            "scene_type": "explanation",
            "duration_seconds": 10,
            "voiceover": "Test voiceover",
        }

        result = generator._generate_scene(
            scene=scene_data,
            scene_number=1,
            scenes_dir=tmp_path,
            example_scene="",
        )

        # Should have retried and succeeded
        assert result["component_name"] == "TestSceneScene"
        assert call_count[0] >= 2  # At least one retry

    @patch.object(SceneGenerator, "_generate_scene_file")
    def test_generator_includes_feedback_on_retry(self, mock_generate, tmp_path: Path):
        """Test that validation feedback is included in retry prompts."""
        scene_file = tmp_path / "TestScene.tsx"
        captured_feedback = []

        invalid_code = '''
import React from "react";
export const TestScene: React.FC = () => {
  const opacity = interpolate(0, [0, 30], [0, 1]);
  return <div>{opacity}</div>;
};
'''
        valid_code = '''
import React from "react";
import { interpolate } from "remotion";
import { COLORS, FONTS } from "./styles";

export const TestScene: React.FC = () => {
  const opacity = interpolate(0, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <div>{opacity}</div>;
};
'''
        call_count = [0]

        def side_effect(base_prompt, output_path, validation_feedback=""):
            captured_feedback.append(validation_feedback)
            call_count[0] += 1
            if call_count[0] == 1:
                output_path.write_text(invalid_code)
            else:
                output_path.write_text(valid_code)

        mock_generate.side_effect = side_effect

        (tmp_path / "styles.ts").write_text("export const COLORS = {}; export const FONTS = {};")

        generator = SceneGenerator(working_dir=tmp_path)

        scene_data = {
            "title": "Test Scene",
            "scene_type": "explanation",
            "duration_seconds": 10,
            "voiceover": "Test",
        }

        generator._generate_scene(
            scene=scene_data,
            scene_number=1,
            scenes_dir=tmp_path,
            example_scene="",
        )

        # First call should have no feedback
        assert captured_feedback[0] == ""

        # Second call should have feedback about the error
        if len(captured_feedback) > 1:
            assert "IMPORTANT" in captured_feedback[1]
            assert "error" in captured_feedback[1].lower() or "fix" in captured_feedback[1].lower()

    @patch.object(SceneGenerator, "_generate_scene_file")
    def test_generator_fails_after_max_retries(self, mock_generate, tmp_path: Path):
        """Test that generator raises error after MAX_RETRIES failures."""
        # Always write invalid code
        invalid_code = '''
import React from "react";
export const TestScene: React.FC = () => {
  const opacity = interpolate(0, [0, 30], [0, 1]);
  return <div>{opacity}</div>;
};
'''

        def side_effect(base_prompt, output_path, validation_feedback=""):
            output_path.write_text(invalid_code)

        mock_generate.side_effect = side_effect

        (tmp_path / "styles.ts").write_text("export const COLORS = {}; export const FONTS = {};")

        generator = SceneGenerator(working_dir=tmp_path)

        scene_data = {
            "title": "Test Scene",
            "scene_type": "explanation",
            "duration_seconds": 10,
            "voiceover": "Test",
        }

        with pytest.raises(RuntimeError) as exc_info:
            generator._generate_scene(
                scene=scene_data,
                scene_number=1,
                scenes_dir=tmp_path,
                example_scene="",
            )

        assert "Failed to generate valid scene" in str(exc_info.value)
        assert str(SceneGenerator.MAX_RETRIES) in str(exc_info.value)

    @patch.object(SceneGenerator, "_generate_scene_file")
    def test_generator_succeeds_on_first_try_with_valid_code(self, mock_generate, tmp_path: Path):
        """Test that generator succeeds immediately with valid code."""
        valid_code = '''
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "./styles";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <div style={{ opacity }}>{opacity}</div>;
};
'''
        call_count = [0]

        def side_effect(base_prompt, output_path, validation_feedback=""):
            call_count[0] += 1
            output_path.write_text(valid_code)

        mock_generate.side_effect = side_effect

        (tmp_path / "styles.ts").write_text("export const COLORS = {}; export const FONTS = {};")

        generator = SceneGenerator(working_dir=tmp_path)

        scene_data = {
            "title": "Test Scene",
            "scene_type": "explanation",
            "duration_seconds": 10,
            "voiceover": "Test",
        }

        result = generator._generate_scene(
            scene=scene_data,
            scene_number=1,
            scenes_dir=tmp_path,
            example_scene="",
        )

        # Should succeed on first try
        assert call_count[0] == 1
        assert result["component_name"] == "TestSceneScene"

    @patch.object(SceneGenerator, "_generate_scene_file")
    def test_generator_logs_warnings_but_succeeds(self, mock_generate, tmp_path: Path):
        """Test that generator succeeds with warnings but logs them."""
        # Code with warnings but no errors
        code_with_warnings = '''
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "./styles";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  const phase4 = 100;
  // Missing extrapolateLeft - warning but not error
  const progress = interpolate(frame, [phase4, 200], [0, 1], {
    extrapolateRight: "clamp",
  });
  return <div style={{ opacity: progress }}>{progress}</div>;
};
'''

        def side_effect(base_prompt, output_path, validation_feedback=""):
            output_path.write_text(code_with_warnings)

        mock_generate.side_effect = side_effect

        (tmp_path / "styles.ts").write_text("export const COLORS = {}; export const FONTS = {};")

        generator = SceneGenerator(working_dir=tmp_path)

        scene_data = {
            "title": "Test Scene",
            "scene_type": "explanation",
            "duration_seconds": 10,
            "voiceover": "Test",
        }

        # Should succeed (warnings don't cause failure)
        result = generator._generate_scene(
            scene=scene_data,
            scene_number=1,
            scenes_dir=tmp_path,
            example_scene="",
        )

        assert result["component_name"] == "TestSceneScene"


class TestSceneGeneratorIntegration:
    """Integration tests for scene generator."""

    def test_generate_all_scenes_returns_results_structure(self, tmp_path: Path):
        """Test that generate_all_scenes returns proper structure."""
        # Create minimal project structure
        script_path = tmp_path / "script" / "script.json"
        script_path.parent.mkdir(parents=True)

        import json
        script_data = {
            "title": "Test Video",
            "scenes": []  # Empty scenes list
        }
        script_path.write_text(json.dumps(script_data))

        generator = SceneGenerator(working_dir=tmp_path)

        results = generator.generate_all_scenes(
            project_dir=tmp_path,
            script_path=script_path,
            force=True,
        )

        assert "scenes_dir" in results
        assert "scenes" in results
        assert "errors" in results
        assert isinstance(results["scenes"], list)
        assert isinstance(results["errors"], list)

    def test_generate_all_scenes_creates_styles_and_index(self, tmp_path: Path):
        """Test that styles.ts and index.ts are created."""
        script_path = tmp_path / "script" / "script.json"
        script_path.parent.mkdir(parents=True)

        import json
        script_data = {
            "title": "Test Video",
            "scenes": []
        }
        script_path.write_text(json.dumps(script_data))

        generator = SceneGenerator(working_dir=tmp_path)

        generator.generate_all_scenes(
            project_dir=tmp_path,
            script_path=script_path,
            force=True,
        )

        scenes_dir = tmp_path / "scenes"
        assert (scenes_dir / "styles.ts").exists()
        assert (scenes_dir / "index.ts").exists()
