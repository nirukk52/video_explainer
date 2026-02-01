"""Tests for SyntaxVerifier class."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

from src.scenes.syntax_verifier import (
    SyntaxError,
    SyntaxVerifier,
    VerificationResult,
    verify_scenes,
)


class TestSyntaxError:
    """Tests for SyntaxError dataclass."""

    def test_create_syntax_error(self):
        """Test creating a basic syntax error."""
        error = SyntaxError(
            file="TestScene.tsx",
            line=10,
            column=5,
            message="'}' expected",
        )
        assert error.file == "TestScene.tsx"
        assert error.line == 10
        assert error.column == 5
        assert error.message == "'}' expected"
        assert error.code is None
        assert error.severity == "error"

    def test_syntax_error_with_code(self):
        """Test creating error with error code."""
        error = SyntaxError(
            file="Scene.tsx",
            line=1,
            column=1,
            message="Missing semicolon",
            code="TS1005",
        )
        assert error.code == "TS1005"

    def test_syntax_error_str(self):
        """Test string representation."""
        error = SyntaxError(
            file="Test.tsx",
            line=5,
            column=10,
            message="Unexpected token",
        )
        assert str(error) == "Test.tsx:5:10: Unexpected token"


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful result."""
        result = VerificationResult(success=True)
        assert result.success is True
        assert result.errors == []
        assert result.fixed_files == []
        assert result.unfixed_files == []

    def test_error_count(self):
        """Test error_count property."""
        errors = [
            SyntaxError(file="a.tsx", line=1, column=1, message="Error 1"),
            SyntaxError(file="b.tsx", line=2, column=1, message="Error 2"),
        ]
        result = VerificationResult(success=False, errors=errors)
        assert result.error_count == 2

    def test_files_with_errors(self):
        """Test files_with_errors property."""
        errors = [
            SyntaxError(file="a.tsx", line=1, column=1, message="Error 1"),
            SyntaxError(file="a.tsx", line=2, column=1, message="Error 2"),
            SyntaxError(file="b.tsx", line=1, column=1, message="Error 3"),
        ]
        result = VerificationResult(success=False, errors=errors)
        assert result.files_with_errors == {"a.tsx", "b.tsx"}


class TestSyntaxVerifier:
    """Tests for SyntaxVerifier class."""

    @pytest.fixture
    def verifier(self, tmp_path):
        """Create a verifier with mock remotion dir."""
        return SyntaxVerifier(remotion_dir=tmp_path)

    @pytest.fixture
    def scenes_dir(self, tmp_path):
        """Create a temporary scenes directory."""
        scenes = tmp_path / "scenes"
        scenes.mkdir()
        return scenes

    def test_init_default_remotion_dir(self):
        """Test default remotion directory is set."""
        verifier = SyntaxVerifier()
        assert verifier.remotion_dir is not None
        assert "remotion" in str(verifier.remotion_dir)

    def test_init_custom_remotion_dir(self, tmp_path):
        """Test custom remotion directory."""
        verifier = SyntaxVerifier(remotion_dir=tmp_path)
        assert verifier.remotion_dir == tmp_path

    def test_verify_empty_directory(self, verifier, scenes_dir):
        """Test verifying empty directory returns success."""
        result = verifier.verify_scenes(scenes_dir)
        assert result.success is True
        assert result.errors == []

    def test_verify_valid_scene(self, verifier, scenes_dir):
        """Test verifying a valid scene file."""
        valid_scene = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

export const TestScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <div>Frame: {frame}</div>
    </AbsoluteFill>
  );
};

export default TestScene;
'''
        (scenes_dir / "TestScene.tsx").write_text(valid_scene)

        # Mock TypeScript check to return no errors
        with patch.object(verifier, '_run_typescript_syntax_check', return_value=[]):
            result = verifier.verify_scenes(scenes_dir)

        assert result.success is True

    def test_verify_single_file_not_found(self, verifier, tmp_path):
        """Test verifying a non-existent file."""
        result = verifier.verify_single_file(tmp_path / "nonexistent.tsx")
        assert result.success is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].message.lower()


class TestBasicSyntaxChecks:
    """Tests for basic syntax checking (without TypeScript)."""

    @pytest.fixture
    def verifier(self, tmp_path):
        return SyntaxVerifier(remotion_dir=tmp_path)

    def test_check_balanced_braces_valid(self, verifier):
        """Test balanced braces detection for valid code."""
        content = '''
const obj = {
  nested: {
    value: 1
  }
};
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        assert errors == []

    def test_check_balanced_braces_unclosed(self, verifier):
        """Test detection of unclosed brace."""
        content = '''
const obj = {
  nested: {
    value: 1
  }
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        assert len(errors) == 1
        assert "Unclosed" in errors[0].message

    def test_check_balanced_braces_extra_closing(self, verifier):
        """Test detection of extra closing brace."""
        content = '''
const obj = {
  value: 1
}};
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        assert len(errors) == 1
        assert "Unexpected" in errors[0].message

    def test_check_balanced_braces_in_string(self, verifier):
        """Test braces inside strings are ignored."""
        content = '''
const str = "{ not a brace }";
const obj = { value: 1 };
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        assert errors == []

    def test_check_balanced_parens_valid(self, verifier):
        """Test balanced parentheses for valid code."""
        content = '''
function foo(a, b) {
  return (a + b);
}
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_parens(content, lines, "test.tsx")
        assert errors == []

    def test_check_balanced_parens_unclosed(self, verifier):
        """Test detection of unclosed parenthesis."""
        content = '''
function foo(a, b {
  return a + b;
}
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_parens(content, lines, "test.tsx")
        assert len(errors) == 1
        assert "Unclosed" in errors[0].message

    def test_check_balanced_brackets_valid(self, verifier):
        """Test balanced brackets for valid code."""
        content = '''
const arr = [1, 2, [3, 4]];
const val = arr[0];
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_brackets(content, lines, "test.tsx")
        assert errors == []

    def test_check_balanced_brackets_unclosed(self, verifier):
        """Test detection of unclosed bracket."""
        content = '''
const arr = [1, 2, [3, 4];
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_brackets(content, lines, "test.tsx")
        assert len(errors) == 1
        assert "Unclosed" in errors[0].message

    def test_check_unclosed_strings_valid(self, verifier):
        """Test valid string literals."""
        content = '''
const a = "hello";
const b = 'world';
'''
        lines = content.split("\n")
        errors = verifier._check_unclosed_strings(content, lines, "test.tsx")
        assert errors == []

    def test_check_unclosed_strings_unterminated(self, verifier):
        """Test detection of unterminated string."""
        content = '''
const a = "hello
const b = "world";
'''
        lines = content.split("\n")
        errors = verifier._check_unclosed_strings(content, lines, "test.tsx")
        assert len(errors) == 1
        assert "Unterminated" in errors[0].message


class TestJSXTagChecks:
    """Tests for JSX tag validation."""

    @pytest.fixture
    def verifier(self, tmp_path):
        return SyntaxVerifier(remotion_dir=tmp_path)

    def test_check_jsx_valid(self, verifier):
        """Test valid JSX tags."""
        content = '''
return (
  <div>
    <span>Hello</span>
  </div>
);
'''
        lines = content.split("\n")
        errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert errors == []

    def test_check_jsx_self_closing(self, verifier):
        """Test self-closing JSX tags."""
        content = '''
return (
  <div>
    <br />
    <input />
  </div>
);
'''
        lines = content.split("\n")
        errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert errors == []

    def test_check_jsx_fragment_mismatch(self, verifier):
        """Test detection of mismatched JSX fragments."""
        content = '''
return (
  <>
    <div>Hello</div>
);
'''
        lines = content.split("\n")
        errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        # Should detect missing </>
        assert len(errors) == 1
        assert "fragment" in errors[0].message.lower()

    def test_check_jsx_component_tags(self, verifier):
        """Test React component tags (PascalCase)."""
        content = '''
return (
  <Container>
    <Header>Title</Header>
  </Container>
);
'''
        lines = content.split("\n")
        errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert errors == []

    def test_check_jsx_balanced_fragments(self, verifier):
        """Test balanced JSX fragments."""
        content = '''
return (
  <>
    <div>Hello</div>
  </>
);
'''
        lines = content.split("\n")
        errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert errors == []


class TestTypeScriptErrorParsing:
    """Tests for TypeScript error parsing."""

    @pytest.fixture
    def verifier(self, tmp_path):
        return SyntaxVerifier(remotion_dir=tmp_path)

    def test_parse_typescript_errors(self, verifier):
        """Test parsing TypeScript compiler output."""
        output = '''
TestScene.tsx(10,5): error TS1005: '}' expected.
TestScene.tsx(15,1): error TS1128: Declaration or statement expected.
'''
        errors = verifier._parse_typescript_errors(output)
        assert len(errors) == 2
        assert errors[0].file == "TestScene.tsx"
        assert errors[0].line == 10
        assert errors[0].column == 5
        assert errors[0].code == "TS1005"
        assert "expected" in errors[0].message

    def test_parse_typescript_ignores_non_syntax_errors(self, verifier):
        """Test that non-syntax errors are ignored."""
        output = '''
TestScene.tsx(10,5): error TS2307: Cannot find module 'remotion'.
TestScene.tsx(15,1): error TS1005: ';' expected.
'''
        errors = verifier._parse_typescript_errors(output)
        # TS2307 should be ignored (not a syntax error)
        assert len(errors) == 1
        assert errors[0].code == "TS1005"

    def test_parse_typescript_jsx_errors(self, verifier):
        """Test parsing JSX-related TypeScript errors."""
        output = '''
TestScene.tsx(20,10): error TS17002: Expected corresponding JSX closing tag for 'div'.
'''
        errors = verifier._parse_typescript_errors(output)
        assert len(errors) == 1
        assert errors[0].code == "TS17002"


class TestAutoFix:
    """Tests for automatic syntax fixing."""

    @pytest.fixture
    def verifier(self, tmp_path):
        return SyntaxVerifier(remotion_dir=tmp_path)

    @pytest.fixture
    def scenes_dir(self, tmp_path):
        scenes = tmp_path / "scenes"
        scenes.mkdir()
        return scenes

    def test_fix_double_semicolon(self, verifier, scenes_dir):
        """Test fixing double semicolons."""
        content = '''
const a = 1;;
const b = 2;
'''
        file_path = scenes_dir / "Test.tsx"
        file_path.write_text(content)

        errors = [SyntaxError(file="Test.tsx", line=2, column=12, message="Unexpected ';'")]
        fixed = verifier._attempt_auto_fix(file_path, errors)

        assert fixed is True
        new_content = file_path.read_text()
        assert ";;" not in new_content

    def test_fix_missing_semicolon_after_import(self, verifier, scenes_dir):
        """Test fixing missing semicolon after import."""
        content = '''import React from "react"
import { useState } from "react";
'''
        file_path = scenes_dir / "Test.tsx"
        file_path.write_text(content)

        errors = [SyntaxError(
            file="Test.tsx", line=1, column=26,
            message="';' expected", code="TS1005"
        )]
        fixed = verifier._attempt_auto_fix(file_path, errors)

        assert fixed is True
        new_content = file_path.read_text()
        assert 'import React from "react";' in new_content

    def test_no_fix_needed(self, verifier, scenes_dir):
        """Test when no fixes are needed."""
        content = '''
import React from "react";
const a = 1;
'''
        file_path = scenes_dir / "Test.tsx"
        file_path.write_text(content)

        errors = []
        fixed = verifier._attempt_auto_fix(file_path, errors)

        assert fixed is False


class TestVerifyScenesIntegration:
    """Integration tests for verify_scenes."""

    @pytest.fixture
    def scenes_dir(self, tmp_path):
        scenes = tmp_path / "scenes"
        scenes.mkdir()
        return scenes

    def test_verify_scenes_convenience_function(self, scenes_dir, tmp_path):
        """Test the convenience function."""
        # Create a valid scene
        valid_scene = '''
import React from "react";
export const Test: React.FC = () => <div>Test</div>;
'''
        (scenes_dir / "Test.tsx").write_text(valid_scene)

        with patch('src.scenes.syntax_verifier.SyntaxVerifier._run_typescript_syntax_check', return_value=[]):
            result = verify_scenes(scenes_dir, remotion_dir=tmp_path)

        assert result.success is True

    def test_verify_with_auto_fix_disabled(self, scenes_dir, tmp_path):
        """Test verification without auto-fix."""
        content = '''
const a = 1;;
'''
        (scenes_dir / "Test.tsx").write_text(content)

        verifier = SyntaxVerifier(remotion_dir=tmp_path)

        with patch.object(verifier, '_run_typescript_syntax_check', return_value=[
            SyntaxError(file="Test.tsx", line=2, column=12, message="Unexpected ';'")
        ]):
            result = verifier.verify_scenes(scenes_dir, auto_fix=False)

        assert result.success is False
        assert result.unfixed_files == ["Test.tsx"]
        # File should not be modified
        assert ";;" in (scenes_dir / "Test.tsx").read_text()


class TestEdgeCases:
    """Tests for edge cases and corner scenarios."""

    @pytest.fixture
    def verifier(self, tmp_path):
        return SyntaxVerifier(remotion_dir=tmp_path)

    def test_template_literal_with_braces(self, verifier):
        """Test template literals with embedded expressions."""
        content = '''
const str = `Hello ${name}, you have ${count} items`;
const obj = { value: 1 };
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        # Should not report false positives from template literal
        assert errors == []

    def test_jsx_with_expressions(self, verifier):
        """Test JSX with embedded expressions."""
        content = '''
return (
  <div style={{ color: "red" }}>
    {items.map(item => <span key={item.id}>{item.name}</span>)}
  </div>
);
'''
        lines = content.split("\n")
        brace_errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        jsx_errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert brace_errors == []
        assert jsx_errors == []

    def test_multiline_string(self, verifier):
        """Test template literal spanning multiple lines."""
        content = '''
const query = `
  SELECT *
  FROM users
  WHERE id = ${userId}
`;
'''
        lines = content.split("\n")
        errors = verifier._check_unclosed_strings(content, lines, "test.tsx")
        # Template literals can span multiple lines
        assert errors == []

    def test_escaped_quotes(self, verifier):
        """Test strings with escaped quotes."""
        content = '''
const str = "He said \\"hello\\"";
const obj = { value: 1 };
'''
        lines = content.split("\n")
        errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        assert errors == []

    def test_comment_line_skipped(self, verifier):
        """Test that comment lines are properly skipped."""
        content = '''
// const str = "unclosed
const a = 1;
'''
        lines = content.split("\n")
        errors = verifier._check_unclosed_strings(content, lines, "test.tsx")
        assert errors == []

    def test_void_elements_dont_need_closing(self, verifier):
        """Test that void elements (br, hr, img, etc.) don't need closing tags."""
        content = '''
return (
  <div>
    <br>
    <hr>
    <img src="test.png">
  </div>
);
'''
        lines = content.split("\n")
        errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert errors == []


class TestCLIIntegration:
    """Tests for CLI integration."""

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create a mock project structure."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create config
        config = {
            "id": "test-project",
            "title": "Test",
            "video": {},
            "tts": {},
            "style": {},
        }
        import json
        (project_dir / "config.json").write_text(json.dumps(config))

        # Create scenes directory
        scenes_dir = project_dir / "scenes"
        scenes_dir.mkdir()

        return project_dir

    def test_verify_command_no_scenes(self, mock_project, capsys):
        """Test verify command when no scenes exist."""
        import argparse
        import shutil

        # Remove scenes directory
        shutil.rmtree(mock_project / "scenes")

        from src.cli.main import _cmd_scenes_verify

        # Create mock project object
        class MockProject:
            root_dir = mock_project
            id = "test-project"

        args = argparse.Namespace()
        args.no_auto_fix = False

        result = _cmd_scenes_verify(args, MockProject())

        assert result == 1
        captured = capsys.readouterr()
        assert "No scenes found" in captured.err

    def test_verify_command_success(self, mock_project, capsys):
        """Test verify command with valid scenes."""
        import argparse

        # Create a valid scene
        scenes_dir = mock_project / "scenes"
        (scenes_dir / "Test.tsx").write_text('''
import React from "react";
export const Test = () => <div>Test</div>;
''')

        from src.cli.main import _cmd_scenes_verify

        class MockProject:
            root_dir = mock_project
            id = "test-project"

        args = argparse.Namespace()
        args.no_auto_fix = False

        with patch('src.scenes.syntax_verifier.SyntaxVerifier._run_typescript_syntax_check', return_value=[]):
            result = _cmd_scenes_verify(args, MockProject())

        assert result == 0
        captured = capsys.readouterr()
        assert "pass" in captured.out.lower()


class TestRealScenePatterns:
    """Tests using patterns from real generated scenes."""

    @pytest.fixture
    def verifier(self, tmp_path):
        return SyntaxVerifier(remotion_dir=tmp_path)

    def test_remotion_scene_pattern(self, verifier):
        """Test a typical Remotion scene structure."""
        content = '''
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { COLORS } from "./styles";

interface HookSceneProps {
  startFrame?: number;
}

export const HookScene: React.FC<HookSceneProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  const opacity = interpolate(localFrame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      <div
        style={{
          opacity,
          fontSize: 48 * scale,
          color: COLORS.text,
        }}
      >
        Hello World
      </div>
    </AbsoluteFill>
  );
};

export default HookScene;
'''
        lines = content.split("\n")

        # Basic syntax checks should pass
        brace_errors = verifier._check_balanced_braces(content, lines, "HookScene.tsx")
        paren_errors = verifier._check_balanced_parens(content, lines, "HookScene.tsx")
        bracket_errors = verifier._check_balanced_brackets(content, lines, "HookScene.tsx")

        assert brace_errors == []
        assert paren_errors == []
        assert bracket_errors == []

        # JSX fragment check should pass (no fragments used)
        jsx_errors = verifier._check_jsx_tags(content, lines, "HookScene.tsx")
        assert jsx_errors == []

    def test_complex_jsx_with_map(self, verifier):
        """Test complex JSX with array mapping."""
        content = '''
return (
  <AbsoluteFill>
    {items.map((item, index) => (
      <div key={index} style={{ top: index * 50 }}>
        <span>{item.name}</span>
        <span>{item.value}</span>
      </div>
    ))}
  </AbsoluteFill>
);
'''
        lines = content.split("\n")
        jsx_errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        assert jsx_errors == []

    def test_conditional_rendering(self, verifier):
        """Test conditional JSX rendering patterns."""
        content = '''
return (
  <div>
    {isVisible && <span>Visible</span>}
    {count > 0 ? (
      <div>Has items</div>
    ) : (
      <div>No items</div>
    )}
  </div>
);
'''
        lines = content.split("\n")
        jsx_errors = verifier._check_jsx_tags(content, lines, "test.tsx")
        brace_errors = verifier._check_balanced_braces(content, lines, "test.tsx")
        assert jsx_errors == []
        assert brace_errors == []


class TestGeneratorIntegration:
    """Tests for automatic syntax verification in SceneGenerator."""

    def test_generator_includes_syntax_verification_in_results(self, tmp_path):
        """Test that generate_all_scenes includes syntax verification results."""
        from src.scenes.generator import SceneGenerator
        import json

        # Create a minimal project structure
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create script
        script_dir = project_dir / "script"
        script_dir.mkdir()
        script = {
            "title": "Test",
            "scenes": [
                {
                    "scene_id": "test_scene",
                    "title": "Test Scene",
                    "scene_type": "hook",
                    "voiceover": "Test narration",
                    "visual_cue": {
                        "description": "Test visual",
                        "elements": ["element1"]
                    }
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Create scenes directory with a valid scene (to skip actual generation)
        scenes_dir = project_dir / "scenes"
        scenes_dir.mkdir()
        valid_scene = '''
import React from "react";
import { AbsoluteFill } from "remotion";

export const TestScene: React.FC = () => {
  return <AbsoluteFill><div>Test</div></AbsoluteFill>;
};

export default TestScene;
'''
        (scenes_dir / "TestScene.tsx").write_text(valid_scene)

        # Create a generator that skips actual LLM generation
        generator = SceneGenerator(
            working_dir=tmp_path,
            timeout=60,
            skip_validation=False,  # Enable validation to test syntax verification
        )

        # Mock the _generate_scene method to avoid actual LLM calls
        # but still test the verification at the end
        original_generate = generator._generate_scene

        def mock_generate_scene(*args, **kwargs):
            # Return a mock result without calling LLM
            return {
                "scene_number": 1,
                "title": "Test Scene",
                "component_name": "TestScene",
                "filename": "TestScene.tsx",
                "path": str(scenes_dir / "TestScene.tsx"),
                "scene_type": "hook",
                "scene_key": "test_scene",
            }

        generator._generate_scene = mock_generate_scene

        # Run generation
        results = generator.generate_all_scenes(
            project_dir=project_dir,
            force=True,
        )

        # Verify syntax_verification is in results
        assert "syntax_verification" in results
        assert "success" in results["syntax_verification"]
        assert "errors" in results["syntax_verification"]
        assert "fixed_files" in results["syntax_verification"]
        assert "unfixed_files" in results["syntax_verification"]

    def test_generator_detects_syntax_errors(self, tmp_path):
        """Test that generator catches syntax errors in generated scenes."""
        from src.scenes.syntax_verifier import SyntaxVerifier

        # Create scenes directory with an invalid scene
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()

        # Create a scene with clear brace mismatch
        invalid_scene = '''
import React from "react";

export const BrokenScene = () => {
  const obj = {
    value: 1,
    nested: {
      x: 2
    // Missing closing brace here
  };
  return <div>Test</div>;
};
'''
        (scenes_dir / "BrokenScene.tsx").write_text(invalid_scene)

        verifier = SyntaxVerifier(remotion_dir=tmp_path)
        result = verifier.verify_scenes(scenes_dir, auto_fix=False)

        # Should detect the syntax error (unclosed brace)
        assert result.success is False
        assert len(result.errors) > 0
        assert any("brace" in str(e).lower() or "Unclosed" in str(e) for e in result.errors)
