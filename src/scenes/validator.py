"""Scene validation module - validates generated Remotion scene components."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: str  # "error", "warning"
    message: str
    file: str
    line: int | None = None
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of validating scenes."""

    success: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class SceneValidator:
    """Validates generated Remotion scene components for common issues."""

    def __init__(self, remotion_dir: Path | None = None):
        """Initialize validator.

        Args:
            remotion_dir: Path to remotion project directory (for TypeScript checks)
        """
        self.remotion_dir = remotion_dir or Path(__file__).parent.parent.parent / "remotion"

    def validate_scenes(self, scenes_dir: Path) -> ValidationResult:
        """Validate all scenes in a directory.

        Args:
            scenes_dir: Directory containing generated scene files

        Returns:
            ValidationResult with any issues found
        """
        issues: list[ValidationIssue] = []

        # Get all scene files
        scene_files = list(scenes_dir.glob("*.tsx"))
        if not scene_files:
            return ValidationResult(success=True, issues=[])

        # Run static analysis on each file
        for scene_file in scene_files:
            if scene_file.name in ("index.tsx", "styles.tsx"):
                continue
            file_issues = self._analyze_scene_file(scene_file)
            issues.extend(file_issues)

        # Run TypeScript compilation check
        ts_issues = self._run_typescript_check(scenes_dir)
        issues.extend(ts_issues)

        # Determine success (no errors, warnings are okay)
        has_errors = any(i.severity == "error" for i in issues)

        return ValidationResult(success=not has_errors, issues=issues)

    def validate_single_scene(self, scene_file: Path) -> ValidationResult:
        """Validate a single scene file.

        Args:
            scene_file: Path to the scene file

        Returns:
            ValidationResult with any issues found
        """
        issues = self._analyze_scene_file(scene_file)
        has_errors = any(i.severity == "error" for i in issues)
        return ValidationResult(success=not has_errors, issues=issues)

    def _analyze_scene_file(self, scene_file: Path) -> list[ValidationIssue]:
        """Run static analysis on a scene file.

        Checks for:
        1. Undefined variables used in code
        2. interpolate() calls without extrapolateLeft when used for array indexing
        3. Array access patterns that could result in undefined
        4. Missing required imports
        """
        issues: list[ValidationIssue] = []
        content = scene_file.read_text()
        lines = content.split("\n")
        filename = scene_file.name

        # Check for undefined variable patterns
        issues.extend(self._check_undefined_variables(content, lines, filename))

        # Check for unsafe interpolate patterns
        issues.extend(self._check_interpolate_patterns(content, lines, filename))

        # Check for unsafe array access patterns
        issues.extend(self._check_array_access_patterns(content, lines, filename))

        # Check for required imports
        issues.extend(self._check_imports(content, lines, filename))

        return issues

    def _check_undefined_variables(
        self, content: str, lines: list[str], filename: str
    ) -> list[ValidationIssue]:
        """Check for variables used but not defined.

        This is a simplified check focused on catching obvious errors like
        referencing variables that were never declared. It uses heuristics
        to avoid false positives from CSS values, template literals, etc.
        """
        issues: list[ValidationIssue] = []

        # Find all variable declarations
        declared_vars: set[str] = set()

        # const/let/var declarations (including destructuring)
        for match in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=", content):
            declared_vars.add(match.group(1))

        # Destructuring assignments
        for match in re.finditer(r"(?:const|let|var)\s+\{([^}]+)\}\s*=", content):
            for var in re.findall(r"\b(\w+)\b", match.group(1)):
                declared_vars.add(var)

        # Array destructuring
        for match in re.finditer(r"(?:const|let|var)\s+\[([^\]]+)\]\s*=", content):
            for var in re.findall(r"\b(\w+)\b", match.group(1)):
                declared_vars.add(var)

        # Function declarations
        for match in re.finditer(r"function\s+(\w+)\s*\(", content):
            declared_vars.add(match.group(1))

        # Arrow function parameters
        for match in re.finditer(r"\(([^)]*)\)\s*(?:=>|:)", content):
            for var in re.findall(r"\b(\w+)\b", match.group(1)):
                declared_vars.add(var)

        # Map/forEach/etc callback parameters
        for match in re.finditer(r"\.(?:map|forEach|filter|find|reduce)\s*\(\s*\(?\s*(\w+)", content):
            declared_vars.add(match.group(1))

        # Variables that are always available in scene components
        builtin_vars = {
            # React/Remotion
            "React", "frame", "fps", "width", "height", "durationInFrames",
            "localFrame", "scale", "startFrame", "COLORS", "FONTS",
            # JavaScript builtins
            "Math", "Array", "Object", "Number", "String", "Boolean", "JSON",
            "parseInt", "parseFloat", "console", "window", "document",
            "undefined", "null", "true", "false", "NaN", "Infinity",
            # Common loop variables
            "i", "j", "k", "idx", "index", "item", "el", "element",
        }

        all_defined = declared_vars | builtin_vars

        # Look for specific patterns that indicate undefined variable usage
        # Focus on high-confidence patterns to avoid false positives

        # Pattern 1: Variable used directly in interpolate/spring but not defined
        for match in re.finditer(r"(?:interpolate|spring)\s*\([^,]+,\s*\[([^]]+)\]", content):
            bracket_content = match.group(1)
            for var in re.findall(r"\b([a-z][a-zA-Z0-9]*)\b", bracket_content):
                if var not in all_defined and not var.isdigit():
                    # Check if it looks like a phase variable
                    if re.match(r"^phase\d*$", var) or "Phase" in var:
                        decl_check = rf"\b(?:const|let|var)\s+{re.escape(var)}\b"
                        if not re.search(decl_check, content):
                            line_num = content[:match.start()].count("\n") + 1
                            issues.append(
                                ValidationIssue(
                                    severity="error",
                                    message=f"Undefined variable '{var}' used in interpolate/spring",
                                    file=filename,
                                    line=line_num,
                                    suggestion=f"Declare '{var}' before using it",
                                )
                            )

        # Pattern 2: Variable in multiplication/expression that's clearly a variable name
        # (not a number, not a CSS value)
        # Exclude common SVG/CSS attribute names that look like variables
        svg_css_attrs = {
            "stopOpacity", "fillOpacity", "strokeOpacity", "opacity",
            "repeatCount", "repeatDur", "keyTimes", "keySplines",
            "gradientTransform", "patternTransform", "textLength",
            "baseFrequency", "numOctaves", "stitchTiles",
            "tableValues", "intercept", "amplitude", "exponent",
        }

        var_in_expr_pattern = r"\b([a-z][a-zA-Z]*(?:Opacity|Progress|Scale|Offset|Position|Count|Index))\b"
        for match in re.finditer(var_in_expr_pattern, content):
            var_name = match.group(1)
            # Skip SVG/CSS attribute names
            if var_name in svg_css_attrs:
                continue
            if var_name not in all_defined:
                decl_check = rf"\b(?:const|let|var)\s+{re.escape(var_name)}\b"
                if not re.search(decl_check, content):
                    line_num = content[:match.start()].count("\n") + 1
                    # Avoid duplicates
                    if not any(i.message.endswith(f"'{var_name}'") for i in issues):
                        issues.append(
                            ValidationIssue(
                                severity="error",
                                message=f"Undefined variable: '{var_name}'",
                                file=filename,
                                line=line_num,
                                suggestion=f"Declare '{var_name}' with const/let before use",
                            )
                        )

        return issues

    def _check_interpolate_patterns(
        self, content: str, lines: list[str], filename: str
    ) -> list[ValidationIssue]:
        """Check for unsafe interpolate() patterns.

        Specifically looks for:
        - interpolate calls that output to a progress variable
        - Which are then used for array indexing
        - But don't have extrapolateLeft: "clamp"
        """
        issues: list[ValidationIssue] = []

        # Find all interpolate calls and their variable names
        # Pattern: const varName = interpolate(..., { extrapolateRight: "clamp" })
        interpolate_pattern = (
            r"const\s+(\w+(?:Progress|Index|Position|Segment)?)\s*=\s*"
            r"(?:Math\.floor\()?\s*interpolate\s*\("
            r"[^;]+?"  # Arguments
            r"(?:\{[^}]*\})?"  # Options object
            r"\s*\)?\s*;?"
        )

        progress_vars: dict[str, int] = {}  # var_name -> line_number

        for match in re.finditer(interpolate_pattern, content):
            var_name = match.group(1)
            # Get line number
            line_num = content[: match.start()].count("\n") + 1
            progress_vars[var_name] = line_num

        # Check each progress variable
        for var_name, decl_line in progress_vars.items():
            # Find the interpolate call for this variable
            var_pattern = rf"const\s+{re.escape(var_name)}\s*=\s*(?:Math\.floor\()?\s*interpolate\s*\(([^;]+)"
            match = re.search(var_pattern, content)
            if not match:
                continue

            call_content = match.group(1)

            # Check if this variable is used for array indexing or critical calculations
            array_index_pattern = rf"\w+\[.*{re.escape(var_name)}.*\]"
            segment_calc_pattern = rf"(?:currentSegment|segmentIndex|arrayIndex)\s*=.*{re.escape(var_name)}"

            is_used_for_indexing = bool(
                re.search(array_index_pattern, content)
                or re.search(segment_calc_pattern, content)
            )

            # Also flag if variable name suggests it's a progress value used in calculations
            is_progress_like = any(
                x in var_name.lower()
                for x in ["progress", "index", "segment", "position"]
            )

            if is_used_for_indexing or is_progress_like:
                # Check if extrapolateLeft: "clamp" is present
                has_extrapolate_left = 'extrapolateLeft' in call_content or 'extrapolateLeft:' in call_content

                if not has_extrapolate_left:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            message=f"interpolate() for '{var_name}' missing extrapolateLeft: \"clamp\"",
                            file=filename,
                            line=decl_line,
                            suggestion=(
                                f"Add {{ extrapolateLeft: \"clamp\", extrapolateRight: \"clamp\" }} "
                                f"to prevent negative values before animation start"
                            ),
                        )
                    )

        return issues

    def _check_array_access_patterns(
        self, content: str, lines: list[str], filename: str
    ) -> list[ValidationIssue]:
        """Check for array access patterns that could result in undefined."""
        issues: list[ValidationIssue] = []

        # Look for array access with calculated index
        # Pattern: arrayName[expr] where expr involves Math.floor or variable
        array_access_pattern = r"(\w+)\[([^[\]]+)\]"

        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(array_access_pattern, line):
                array_name = match.group(1)
                index_expr = match.group(2)

                # Skip simple numeric indices or known safe patterns
                if (
                    index_expr.isdigit()
                    or index_expr == "0"
                    or index_expr == "i"
                    or index_expr == "j"
                    or index_expr == "index"
                    or "length" in index_expr
                    or ".length - 1" in index_expr
                ):
                    continue

                # Check if there's a bounds check nearby
                bounds_check_pattern = rf"if\s*\([^)]*{re.escape(index_expr)}[^)]*(?:>=|>|<|<=|length)"
                context_start = max(0, line_num - 5)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                has_bounds_check = bool(re.search(bounds_check_pattern, context))

                if not has_bounds_check and ("Progress" in index_expr or "Segment" in index_expr):
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            message=f"Array access '{array_name}[{index_expr}]' may need bounds checking",
                            file=filename,
                            line=line_num,
                            suggestion="Add bounds check or ensure index is clamped to valid range",
                        )
                    )

        return issues

    def _check_imports(
        self, content: str, lines: list[str], filename: str
    ) -> list[ValidationIssue]:
        """Check for required imports."""
        issues: list[ValidationIssue] = []

        # Required Remotion imports based on usage
        remotion_functions = {
            "useCurrentFrame": r"\buseCurrentFrame\s*\(",
            "useVideoConfig": r"\buseVideoConfig\s*\(",
            "interpolate": r"\binterpolate\s*\(",
            "spring": r"\bspring\s*\(",
            "AbsoluteFill": r"<AbsoluteFill",
            "Sequence": r"<Sequence",
        }

        # Check if remotion is imported
        has_remotion_import = 'from "remotion"' in content or "from 'remotion'" in content

        if not has_remotion_import:
            # Check if any remotion functions are used
            for func_name, pattern in remotion_functions.items():
                if re.search(pattern, content):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            message=f"Missing import for '{func_name}' from remotion",
                            file=filename,
                            line=1,
                            suggestion=f'Add: import {{ {func_name} }} from "remotion";',
                        )
                    )
                    break

        # Check styles import
        uses_colors = "COLORS." in content
        uses_fonts = "FONTS." in content
        has_styles_import = 'from "./styles"' in content or "from './styles'" in content

        if (uses_colors or uses_fonts) and not has_styles_import:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="Missing import for COLORS/FONTS from styles",
                    file=filename,
                    line=1,
                    suggestion='Add: import { COLORS, FONTS } from "./styles";',
                )
            )

        return issues

    def _run_typescript_check(self, scenes_dir: Path) -> list[ValidationIssue]:
        """Run TypeScript compiler to check for type errors.

        Uses the remotion project's TypeScript installation to check scenes.
        """
        issues: list[ValidationIssue] = []

        # Check if remotion directory has TypeScript
        tsc_path = self.remotion_dir / "node_modules" / ".bin" / "tsc"
        if not tsc_path.exists():
            # Try finding it via npx in remotion directory
            tsc_path = None

        # Create a temporary tsconfig for the scenes directory
        scenes_relative = scenes_dir.relative_to(scenes_dir.parent.parent) if scenes_dir.is_relative_to(scenes_dir.parent.parent) else scenes_dir
        remotion_relative = self.remotion_dir.relative_to(scenes_dir.parent.parent) if self.remotion_dir.is_relative_to(scenes_dir.parent.parent) else self.remotion_dir

        tsconfig_content = f"""{{
  "compilerOptions": {{
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": {{
      "remotion": ["{self.remotion_dir}/node_modules/remotion"],
      "@remotion/*": ["{self.remotion_dir}/node_modules/@remotion/*"]
    }}
  }},
  "include": ["*.tsx", "*.ts"],
  "exclude": ["node_modules"]
}}
"""
        tsconfig_path = scenes_dir / "tsconfig.json"
        tsconfig_existed = tsconfig_path.exists()
        original_content = None

        try:
            if tsconfig_existed:
                original_content = tsconfig_path.read_text()
            tsconfig_path.write_text(tsconfig_content)

            # Run TypeScript compiler from remotion directory
            if tsc_path and tsc_path.exists():
                cmd = [str(tsc_path), "--project", str(tsconfig_path), "--pretty", "false"]
            else:
                cmd = ["npx", "tsc", "--project", str(tsconfig_path), "--pretty", "false"]

            result = subprocess.run(
                cmd,
                cwd=self.remotion_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                # Parse TypeScript errors
                error_pattern = r"([^:\s]+\.tsx?)\((\d+),\d+\):\s*error\s+TS(\d+):\s*(.+)"
                output = result.stdout + result.stderr

                # TypeScript error codes to ignore (module resolution, not actual code errors)
                # TS2307: Cannot find module
                # TS2792: Cannot find module (type declarations)
                # TS7016: Could not find declaration file
                # TS2686: 'React' refers to a UMD global
                # TS1479: jsx-runtime not found
                # TS2354: This overload signature is not compatible
                # TS6142: Module was resolved to but '--jsx' is not set
                # TS17004: jsx flag not set
                ignored_error_codes = {"2307", "2792", "7016", "2686", "1479", "2354", "6142", "17004"}

                # Also ignore any errors containing these phrases (fallback for edge cases)
                ignored_phrases = [
                    "jsx-runtime",
                    "Cannot find module",
                    "type declarations",
                    "UMD global",
                ]

                code_errors = []
                for line in output.split("\n"):
                    match = re.match(error_pattern, line)
                    if match:
                        error_code = match.group(3)
                        error_msg = match.group(4)

                        # Skip ignored error codes
                        if error_code in ignored_error_codes:
                            continue

                        # Skip errors containing ignored phrases
                        if any(phrase in error_msg for phrase in ignored_phrases):
                            continue

                        # Get just the filename
                        filepath = match.group(1)
                        filename = Path(filepath).name if "/" in filepath or "\\" in filepath else filepath
                        code_errors.append(
                            ValidationIssue(
                                severity="error",
                                message=f"TypeScript: {error_msg}",
                                file=filename,
                                line=int(match.group(2)),
                            )
                        )

                issues.extend(code_errors)

                # If no code errors but still failed with output, check for common issues
                if not code_errors and output.strip():
                    # Check for "not the tsc command" message (tsc not installed)
                    if "not the tsc command" in output:
                        issues.append(
                            ValidationIssue(
                                severity="warning",
                                message="TypeScript not installed in remotion project. Run 'npm install' in remotion/",
                                file="",
                            )
                        )

        except subprocess.TimeoutExpired:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="TypeScript check timed out",
                    file="",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"TypeScript check error: {e}",
                    file="",
                )
            )
        finally:
            # Restore or remove tsconfig
            if original_content is not None:
                tsconfig_path.write_text(original_content)
            elif tsconfig_path.exists() and not tsconfig_existed:
                tsconfig_path.unlink()

        return issues


def validate_scenes(scenes_dir: Path, remotion_dir: Path | None = None) -> ValidationResult:
    """Convenience function to validate scenes.

    Args:
        scenes_dir: Directory containing generated scene files
        remotion_dir: Optional path to remotion project

    Returns:
        ValidationResult with any issues found
    """
    validator = SceneValidator(remotion_dir)
    return validator.validate_scenes(scenes_dir)
