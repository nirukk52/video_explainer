"""Syntax verification and auto-fix module for generated scene components.

This module provides syntax verification for generated TSX scene files,
detecting syntax errors and attempting to fix them automatically.
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SyntaxError:
    """A syntax error found in a scene file."""

    file: str
    line: int
    column: int
    message: str
    code: str | None = None  # Error code (e.g., TS1005)
    severity: str = "error"

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}:{self.column}"
        return f"{loc}: {self.message}"


@dataclass
class VerificationResult:
    """Result of syntax verification."""

    success: bool
    errors: list[SyntaxError] = field(default_factory=list)
    fixed_files: list[str] = field(default_factory=list)
    unfixed_files: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def files_with_errors(self) -> set[str]:
        return {e.file for e in self.errors}


class SyntaxVerifier:
    """Verifies and fixes syntax errors in generated scene components."""

    # Common syntax patterns that can be auto-fixed
    AUTO_FIX_PATTERNS = [
        # Missing semicolon after import
        (r'(import\s+[^;]+)\n(?=import|const|let|var|function|export)', r'\1;\n'),
        # Double semicolons
        (r';;', r';'),
        # Missing closing brace in style object (common LLM error)
        (r'(style=\{\{[^}]+)\}\s*>', r'\1}}>'),
        # Unescaped > in JSX text (outside of expressions)
        (r'>(\s*\w+\s*)>(\s*\w+)', r'>{`\1>\2`}'),
        # Unescaped < in JSX text
        (r'<(\s*\w+\s*)<(\s*\w+)', r'<{`\1<\2`}'),
        # Extra closing braces before JSX close
        (r'\}\}\}>', r'}}>'),
        # Missing opening brace in JSX expression
        (r'=\{([^{}]+)\}\}>', r'={{\1}}>'),
    ]

    def __init__(self, remotion_dir: Path | None = None):
        """Initialize the syntax verifier.

        Args:
            remotion_dir: Path to remotion project directory (for TypeScript checks)
        """
        self.remotion_dir = remotion_dir or Path(__file__).parent.parent.parent / "remotion"

    def verify_scenes(
        self,
        scenes_dir: Path,
        auto_fix: bool = True,
    ) -> VerificationResult:
        """Verify all scene files in a directory for syntax errors.

        Args:
            scenes_dir: Directory containing scene files
            auto_fix: Whether to attempt automatic fixes

        Returns:
            VerificationResult with errors and fix status
        """
        result = VerificationResult(success=True)

        # Get all scene files
        scene_files = list(scenes_dir.glob("*.tsx"))
        scene_files.extend(scenes_dir.glob("*.ts"))

        if not scene_files:
            return result

        # First pass: Run TypeScript compiler to get syntax errors
        ts_errors = self._run_typescript_syntax_check(scenes_dir)

        # Second pass: Run basic syntax checks (catches issues TypeScript might miss
        # or when TypeScript isn't available)
        basic_errors = self._run_basic_syntax_check(scenes_dir)

        # Combine errors, avoiding duplicates
        all_errors = ts_errors.copy()
        seen_locations = {(e.file, e.line) for e in ts_errors}
        for error in basic_errors:
            if (error.file, error.line) not in seen_locations:
                all_errors.append(error)

        if not all_errors:
            return result  # No errors found

        # Group errors by file
        errors_by_file: dict[str, list[SyntaxError]] = {}
        for error in all_errors:
            if error.file not in errors_by_file:
                errors_by_file[error.file] = []
            errors_by_file[error.file].append(error)

        result.errors = all_errors
        result.success = False

        if not auto_fix:
            result.unfixed_files = list(errors_by_file.keys())
            return result

        # Attempt to fix each file with errors
        for filename, file_errors in errors_by_file.items():
            file_path = scenes_dir / filename
            if not file_path.exists():
                result.unfixed_files.append(filename)
                continue

            fixed = self._attempt_auto_fix(file_path, file_errors)
            if fixed:
                result.fixed_files.append(filename)
            else:
                result.unfixed_files.append(filename)

        # Re-verify after fixes
        if result.fixed_files:
            remaining_errors = self._run_typescript_syntax_check(scenes_dir)
            result.errors = remaining_errors
            result.success = len(remaining_errors) == 0

            # Update unfixed files based on remaining errors
            still_broken = {e.file for e in remaining_errors}
            result.fixed_files = [f for f in result.fixed_files if f not in still_broken]
            result.unfixed_files = list(still_broken)

        return result

    def verify_single_file(
        self,
        file_path: Path,
        auto_fix: bool = True,
    ) -> VerificationResult:
        """Verify a single file for syntax errors.

        Args:
            file_path: Path to the file to verify
            auto_fix: Whether to attempt automatic fixes

        Returns:
            VerificationResult with errors and fix status
        """
        result = VerificationResult(success=True)

        if not file_path.exists():
            result.errors.append(
                SyntaxError(
                    file=file_path.name,
                    line=0,
                    column=0,
                    message=f"File not found: {file_path}",
                )
            )
            result.success = False
            return result

        # Run syntax check on the single file
        errors = self._check_file_syntax(file_path)

        if not errors:
            return result

        result.errors = errors
        result.success = False

        if not auto_fix:
            result.unfixed_files = [file_path.name]
            return result

        # Attempt auto-fix
        fixed = self._attempt_auto_fix(file_path, errors)
        if fixed:
            result.fixed_files.append(file_path.name)
            # Re-verify
            remaining_errors = self._check_file_syntax(file_path)
            result.errors = remaining_errors
            result.success = len(remaining_errors) == 0
            if remaining_errors:
                result.unfixed_files = [file_path.name]
                result.fixed_files = []
        else:
            result.unfixed_files = [file_path.name]

        return result

    def _run_typescript_syntax_check(self, scenes_dir: Path) -> list[SyntaxError]:
        """Run TypeScript compiler in syntax-only mode.

        Args:
            scenes_dir: Directory containing scene files

        Returns:
            List of syntax errors found
        """
        errors: list[SyntaxError] = []

        # Create a minimal tsconfig for syntax checking only
        tsconfig_content = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": false,
    "skipLibCheck": true,
    "noEmit": true,
    "isolatedModules": true,
    "allowJs": true
  },
  "include": ["*.tsx", "*.ts"],
  "exclude": ["node_modules"]
}
"""
        tsconfig_path = scenes_dir / "tsconfig.syntax.json"
        tsconfig_existed = tsconfig_path.exists()
        original_content = None

        try:
            if tsconfig_existed:
                original_content = tsconfig_path.read_text()
            tsconfig_path.write_text(tsconfig_content)

            # Find tsc
            tsc_path = self.remotion_dir / "node_modules" / ".bin" / "tsc"
            if tsc_path.exists():
                cmd = [str(tsc_path), "--project", str(tsconfig_path), "--pretty", "false"]
            else:
                cmd = ["npx", "tsc", "--project", str(tsconfig_path), "--pretty", "false"]

            result = subprocess.run(
                cmd,
                cwd=scenes_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                errors = self._parse_typescript_errors(result.stdout + result.stderr)

        except subprocess.TimeoutExpired:
            errors.append(
                SyntaxError(
                    file="",
                    line=0,
                    column=0,
                    message="TypeScript syntax check timed out",
                    severity="warning",
                )
            )
        except FileNotFoundError:
            # TypeScript not installed - try alternative check
            errors = self._run_basic_syntax_check(scenes_dir)
        except Exception as e:
            errors.append(
                SyntaxError(
                    file="",
                    line=0,
                    column=0,
                    message=f"Syntax check error: {e}",
                    severity="warning",
                )
            )
        finally:
            # Cleanup
            if original_content is not None:
                tsconfig_path.write_text(original_content)
            elif tsconfig_path.exists() and not tsconfig_existed:
                tsconfig_path.unlink()

        return errors

    def _check_file_syntax(self, file_path: Path) -> list[SyntaxError]:
        """Check syntax of a single file.

        Args:
            file_path: Path to the file

        Returns:
            List of syntax errors
        """
        errors: list[SyntaxError] = []

        # First try TypeScript if available
        try:
            tsc_path = self.remotion_dir / "node_modules" / ".bin" / "tsc"
            if tsc_path.exists():
                cmd = [str(tsc_path), "--noEmit", "--pretty", "false", str(file_path)]
            else:
                cmd = ["npx", "tsc", "--noEmit", "--pretty", "false", str(file_path)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                errors = self._parse_typescript_errors(
                    result.stdout + result.stderr,
                    base_filename=file_path.name
                )

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fall back to basic checks
            errors = self._run_basic_syntax_check_file(file_path)

        return errors

    def _parse_typescript_errors(
        self,
        output: str,
        base_filename: str | None = None
    ) -> list[SyntaxError]:
        """Parse TypeScript compiler output for errors.

        Args:
            output: TypeScript compiler output
            base_filename: Optional base filename for relative paths

        Returns:
            List of parsed errors
        """
        errors: list[SyntaxError] = []

        # TypeScript error format: file(line,col): error TSxxxx: message
        error_pattern = r"([^:\s(]+\.tsx?)\((\d+),(\d+)\):\s*error\s+(TS\d+):\s*(.+)"

        # Only include syntax-related error codes
        # TS1xxx are syntax/parse errors
        syntax_error_codes = {
            "TS1002",  # Unterminated string literal
            "TS1003",  # Identifier expected
            "TS1005",  # 'x' expected (missing punctuation)
            "TS1009",  # Trailing comma not allowed
            "TS1010",  # Asterisk expected
            "TS1011",  # Element access expression should take an argument
            "TS1012",  # Unexpected token
            "TS1014",  # Rest parameter must be last
            "TS1015",  # Parameter cannot have question mark
            "TS1016",  # Required parameter cannot follow optional
            "TS1019",  # Duplicate identifier
            "TS1029",  # Unexpected token (modifier)
            "TS1035",  # Comments are not permitted
            "TS1036",  # Statements not allowed in ambient context
            "TS1039",  # Initializers are not allowed in ambient
            "TS1042",  # Modifier cannot appear
            "TS1046",  # Top-level declarations require export
            "TS1048",  # Cannot access before declaration
            "TS1068",  # Unexpected token
            "TS1109",  # Expression expected
            "TS1110",  # Type expected
            "TS1126",  # Unexpected end of text
            "TS1127",  # Invalid character
            "TS1128",  # Declaration or statement expected
            "TS1136",  # Property assignment expected
            "TS1137",  # Expression or comma expected
            "TS1138",  # Unexpected keyword
            "TS1141",  # String literal expected
            "TS1160",  # Unterminated template literal
            "TS1161",  # Unterminated regular expression
            "TS1185",  # Merge conflict marker
            "TS1381",  # Unexpected token in type
            "TS17002",  # Expected corresponding JSX closing tag
            "TS17008",  # JSX element has no corresponding closing tag
            "TS17009",  # Expected corresponding JSX closing tag
            "TS17014",  # JSX expressions may not use the comma operator
        }

        for line in output.split("\n"):
            match = re.match(error_pattern, line)
            if match:
                filepath = match.group(1)
                filename = Path(filepath).name if "/" in filepath or "\\" in filepath else filepath
                error_code = match.group(4)

                # Only include syntax errors (TS1xxx) and JSX errors (TS17xxx)
                if error_code.startswith("TS1") or error_code.startswith("TS17"):
                    errors.append(
                        SyntaxError(
                            file=filename,
                            line=int(match.group(2)),
                            column=int(match.group(3)),
                            message=match.group(5),
                            code=error_code,
                        )
                    )

        return errors

    def _run_basic_syntax_check(self, scenes_dir: Path) -> list[SyntaxError]:
        """Run basic syntax checks without TypeScript.

        Checks for common syntax issues that can be detected with regex.

        Args:
            scenes_dir: Directory containing scene files

        Returns:
            List of syntax errors
        """
        errors: list[SyntaxError] = []

        for file_path in scenes_dir.glob("*.tsx"):
            file_errors = self._run_basic_syntax_check_file(file_path)
            errors.extend(file_errors)

        return errors

    def _run_basic_syntax_check_file(self, file_path: Path) -> list[SyntaxError]:
        """Run basic syntax checks on a single file.

        Args:
            file_path: Path to the file

        Returns:
            List of syntax errors
        """
        errors: list[SyntaxError] = []
        content = file_path.read_text()
        lines = content.split("\n")
        filename = file_path.name

        # Check for balanced braces
        brace_errors = self._check_balanced_braces(content, lines, filename)
        errors.extend(brace_errors)

        # Check for balanced parentheses
        paren_errors = self._check_balanced_parens(content, lines, filename)
        errors.extend(paren_errors)

        # Check for balanced brackets
        bracket_errors = self._check_balanced_brackets(content, lines, filename)
        errors.extend(bracket_errors)

        # Check for unclosed JSX tags
        jsx_errors = self._check_jsx_tags(content, lines, filename)
        errors.extend(jsx_errors)

        # Check for unclosed strings
        string_errors = self._check_unclosed_strings(content, lines, filename)
        errors.extend(string_errors)

        return errors

    def _check_balanced_braces(
        self, content: str, lines: list[str], filename: str
    ) -> list[SyntaxError]:
        """Check for balanced curly braces."""
        errors: list[SyntaxError] = []
        stack: list[tuple[int, int]] = []  # (line, column) of opening braces

        in_string = False
        string_char = None
        in_template = False
        # Track nested ${} expressions in template literals
        # Each entry is the brace depth when we entered that expression
        template_expr_stack: list[int] = []

        for line_num, line in enumerate(lines, 1):
            col = 0
            while col < len(line):
                char = line[col]

                # Handle escape sequences
                if col > 0 and line[col - 1] == "\\":
                    col += 1
                    continue

                # Handle strings
                if char in ('"', "'", "`"):
                    if not in_string:
                        in_string = True
                        string_char = char
                        if char == "`":
                            in_template = True
                    elif char == string_char:
                        # Check we're not inside a template expression
                        if not (in_template and template_expr_stack):
                            in_string = False
                            string_char = None
                            if char == "`":
                                in_template = False
                        elif in_template and char == "`":
                            # Closing the template while in expression - shouldn't happen in valid code
                            in_string = False
                            string_char = None
                            in_template = False
                            template_expr_stack.clear()
                    col += 1
                    continue

                # Handle template literal expressions ${...}
                if in_template and not template_expr_stack and char == "$" and col + 1 < len(line) and line[col + 1] == "{":
                    # Entering a template expression - save current brace depth
                    template_expr_stack.append(len(stack))
                    col += 2  # Skip both $ and {
                    continue

                # Count braces
                if not in_string or template_expr_stack:
                    if char == "{":
                        stack.append((line_num, col + 1))
                    elif char == "}":
                        if template_expr_stack and len(stack) == template_expr_stack[-1]:
                            # This } closes the template expression, not a regular brace
                            template_expr_stack.pop()
                        elif stack:
                            stack.pop()
                        else:
                            errors.append(
                                SyntaxError(
                                    file=filename,
                                    line=line_num,
                                    column=col + 1,
                                    message="Unexpected closing brace '}'",
                                    code="BRACE_MISMATCH",
                                )
                            )

                col += 1

        # Report unclosed braces
        for line_num, col in stack:
            errors.append(
                SyntaxError(
                    file=filename,
                    line=line_num,
                    column=col,
                    message="Unclosed opening brace '{'",
                    code="BRACE_MISMATCH",
                )
            )

        return errors

    def _check_balanced_parens(
        self, content: str, lines: list[str], filename: str
    ) -> list[SyntaxError]:
        """Check for balanced parentheses."""
        errors: list[SyntaxError] = []
        stack: list[tuple[int, int]] = []

        in_string = False
        string_char = None

        for line_num, line in enumerate(lines, 1):
            for col, char in enumerate(line):
                # Handle strings
                if char in ('"', "'", "`") and (col == 0 or line[col - 1] != "\\"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False

                if not in_string:
                    if char == "(":
                        stack.append((line_num, col + 1))
                    elif char == ")":
                        if stack:
                            stack.pop()
                        else:
                            errors.append(
                                SyntaxError(
                                    file=filename,
                                    line=line_num,
                                    column=col + 1,
                                    message="Unexpected closing parenthesis ')'",
                                    code="PAREN_MISMATCH",
                                )
                            )

        for line_num, col in stack:
            errors.append(
                SyntaxError(
                    file=filename,
                    line=line_num,
                    column=col,
                    message="Unclosed opening parenthesis '('",
                    code="PAREN_MISMATCH",
                )
            )

        return errors

    def _check_balanced_brackets(
        self, content: str, lines: list[str], filename: str
    ) -> list[SyntaxError]:
        """Check for balanced square brackets."""
        errors: list[SyntaxError] = []
        stack: list[tuple[int, int]] = []

        in_string = False
        string_char = None

        for line_num, line in enumerate(lines, 1):
            for col, char in enumerate(line):
                if char in ('"', "'", "`") and (col == 0 or line[col - 1] != "\\"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False

                if not in_string:
                    if char == "[":
                        stack.append((line_num, col + 1))
                    elif char == "]":
                        if stack:
                            stack.pop()
                        else:
                            errors.append(
                                SyntaxError(
                                    file=filename,
                                    line=line_num,
                                    column=col + 1,
                                    message="Unexpected closing bracket ']'",
                                    code="BRACKET_MISMATCH",
                                )
                            )

        for line_num, col in stack:
            errors.append(
                SyntaxError(
                    file=filename,
                    line=line_num,
                    column=col,
                    message="Unclosed opening bracket '['",
                    code="BRACKET_MISMATCH",
                )
            )

        return errors

    def _check_jsx_tags(
        self, content: str, lines: list[str], filename: str
    ) -> list[SyntaxError]:
        """Check for unclosed JSX tags.

        This is a simplified check that catches obvious mismatches.
        For complete JSX validation, TypeScript compiler is preferred.
        """
        errors: list[SyntaxError] = []

        # This check is simplified because JSX can be complex:
        # - Multi-line tags with attributes
        # - TypeScript generics that look like tags
        # - Fragment shorthand <>...</>
        # - Conditional rendering patterns

        # For now, we only check for basic patterns on single lines
        # The TypeScript compiler handles the complex cases

        # Pattern for single-line self-closing tags that are clearly wrong
        # e.g., <div> with no content or closing tag on the same line
        single_line_unclosed = r"<([A-Z][a-zA-Z0-9]*|[a-z][a-z0-9-]*)\s*>(?!.*</\1>)(?!.*/>)"

        # Check for obvious fragment issues: <> without </>
        fragment_opens = content.count("<>")
        fragment_closes = content.count("</>")

        if fragment_opens != fragment_closes:
            if fragment_opens > fragment_closes:
                errors.append(
                    SyntaxError(
                        file=filename,
                        line=1,
                        column=1,
                        message="Unmatched JSX fragment '<>' - missing closing '</>'",
                        code="JSX_FRAGMENT",
                    )
                )
            else:
                errors.append(
                    SyntaxError(
                        file=filename,
                        line=1,
                        column=1,
                        message="Unmatched JSX fragment '</>' - missing opening '<>'",
                        code="JSX_FRAGMENT",
                    )
                )

        # Skip detailed tag matching for now - too many false positives
        # The TypeScript compiler will catch real JSX errors
        return errors

    def _check_unclosed_strings(
        self, content: str, lines: list[str], filename: str
    ) -> list[SyntaxError]:
        """Check for unclosed string literals."""
        errors: list[SyntaxError] = []

        for line_num, line in enumerate(lines, 1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # Check for unterminated strings (simple check)
            # Count unescaped quotes
            in_string = False
            string_char = None
            string_start = 0

            for col, char in enumerate(line):
                if char in ('"', "'") and (col == 0 or line[col - 1] != "\\"):
                    if not in_string:
                        in_string = True
                        string_char = char
                        string_start = col
                    elif char == string_char:
                        in_string = False

            # If line ends while in a non-template string, it's an error
            if in_string and string_char != "`":
                errors.append(
                    SyntaxError(
                        file=filename,
                        line=line_num,
                        column=string_start + 1,
                        message="Unterminated string literal",
                        code="STRING_UNCLOSED",
                    )
                )

        return errors

    def _attempt_auto_fix(
        self, file_path: Path, errors: list[SyntaxError]
    ) -> bool:
        """Attempt to automatically fix syntax errors.

        Args:
            file_path: Path to the file to fix
            errors: List of errors to fix

        Returns:
            True if any fixes were applied
        """
        content = file_path.read_text()
        original_content = content
        fixed = False

        # Apply pattern-based fixes
        for pattern, replacement in self.AUTO_FIX_PATTERNS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                fixed = True

        # Fix specific error types
        for error in errors:
            if error.code == "TS1005" and "expected" in error.message.lower():
                # Missing punctuation - try to fix
                fix_result = self._fix_missing_punctuation(content, error)
                if fix_result:
                    content = fix_result
                    fixed = True

            elif error.code in ("TS17002", "TS17008", "TS17009", "JSX_UNCLOSED"):
                # Unclosed JSX tag - try to fix
                fix_result = self._fix_unclosed_jsx(content, error)
                if fix_result:
                    content = fix_result
                    fixed = True

            elif error.code == "BRACE_MISMATCH":
                fix_result = self._fix_brace_mismatch(content, error)
                if fix_result:
                    content = fix_result
                    fixed = True

        if fixed and content != original_content:
            file_path.write_text(content)
            return True

        return False

    def _fix_missing_punctuation(self, content: str, error: SyntaxError) -> str | None:
        """Try to fix missing punctuation errors."""
        lines = content.split("\n")
        if error.line <= 0 or error.line > len(lines):
            return None

        line = lines[error.line - 1]

        # Extract what's expected from the message
        # e.g., "';' expected" or "',' expected"
        match = re.search(r"'(.)'.*expected", error.message)
        if match:
            expected = match.group(1)
            col = error.column - 1

            # Insert the expected character at the position
            if col <= len(line):
                new_line = line[:col] + expected + line[col:]
                lines[error.line - 1] = new_line
                return "\n".join(lines)

        return None

    def _fix_unclosed_jsx(self, content: str, error: SyntaxError) -> str | None:
        """Try to fix unclosed JSX tags."""
        lines = content.split("\n")
        if error.line <= 0 or error.line > len(lines):
            return None

        # Extract tag name from error message
        match = re.search(r"<([A-Za-z][A-Za-z0-9]*)", error.message)
        if not match:
            return None

        tag_name = match.group(1)

        # Find the line with the unclosed tag and try to close it
        # This is a simplified fix - just adds closing tag at end of return block
        line = lines[error.line - 1]

        # If the tag appears to be self-closeable, convert to self-closing
        if re.search(rf"<{tag_name}\s*[^>]*[^/]>", line):
            # Try converting to self-closing if it has no children
            new_line = re.sub(rf"<{tag_name}(\s*[^>]*)>", rf"<{tag_name}\1 />", line)
            if new_line != line:
                lines[error.line - 1] = new_line
                return "\n".join(lines)

        return None

    def _fix_brace_mismatch(self, content: str, error: SyntaxError) -> str | None:
        """Try to fix brace mismatch errors."""
        lines = content.split("\n")
        if error.line <= 0 or error.line > len(lines):
            return None

        if "Unclosed" in error.message:
            # Need to add a closing brace somewhere
            # Try adding at the end of the current scope
            # This is a heuristic - add } before the next statement at same indent
            line = lines[error.line - 1]
            indent = len(line) - len(line.lstrip())

            # Look for a good place to add the closing brace
            for i in range(error.line, len(lines)):
                check_line = lines[i]
                if check_line.strip() and not check_line.strip().startswith("//"):
                    check_indent = len(check_line) - len(check_line.lstrip())
                    if check_indent <= indent and i > error.line:
                        # Insert closing brace before this line
                        lines.insert(i, " " * indent + "}")
                        return "\n".join(lines)

        elif "Unexpected" in error.message:
            # Extra closing brace - try removing it
            line = lines[error.line - 1]
            col = error.column - 1
            if col < len(line) and line[col] == "}":
                new_line = line[:col] + line[col + 1:]
                lines[error.line - 1] = new_line
                return "\n".join(lines)

        return None


def verify_scenes(
    scenes_dir: Path,
    remotion_dir: Path | None = None,
    auto_fix: bool = True,
) -> VerificationResult:
    """Convenience function to verify scene syntax.

    Args:
        scenes_dir: Directory containing scene files
        remotion_dir: Optional path to remotion project
        auto_fix: Whether to attempt automatic fixes

    Returns:
        VerificationResult with errors and fix status
    """
    verifier = SyntaxVerifier(remotion_dir)
    return verifier.verify_scenes(scenes_dir, auto_fix=auto_fix)
