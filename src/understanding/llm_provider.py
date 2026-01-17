"""LLM Provider abstraction and implementations."""

import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Config, LLMConfig
from ..models import ContentAnalysis, Concept, Script, ScriptScene, VisualCue


class ClaudeCodeError(Exception):
    """Error from Claude Code CLI execution."""

    pass


@dataclass
class ClaudeCodeResult:
    """Result from Claude Code execution with file access."""

    response: str
    modified_files: list[str] = field(default_factory=list)
    success: bool = True
    error_message: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            The generated text response
        """
        pass

    @abstractmethod
    def generate_json(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        """Generate a JSON response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            Parsed JSON response as a dictionary
        """
        pass


class MockLLMProvider(LLMProvider):
    """Mock LLM provider that returns generic responses for testing.

    This provider returns realistic but generic mock responses suitable
    for testing the pipeline without requiring an actual LLM API.
    """

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a mock response based on prompt patterns."""
        return "This is a mock LLM response for testing purposes."

    def generate_json(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        """Generate mock JSON responses for known prompt patterns.

        Pattern matching order is important:
        1. Storyboard (most specific - contains "storyboard" keyword)
        2. Script (contains "script" + "create/generate", but NOT "storyboard")
        3. Content analysis (contains "analyze" + "content/document")
        """
        prompt_lower = prompt.lower()

        # Storyboard generation request (check first - most specific)
        if "storyboard" in prompt_lower or "scene id:" in prompt_lower:
            return self._mock_storyboard_generation(prompt)

        # Script generation request (check before analysis - scripts may contain "analyze")
        if "script" in prompt_lower and (
            "generate" in prompt_lower or "create" in prompt_lower
        ):
            return self._mock_script_generation(prompt)

        # Content analysis request
        if "analyze" in prompt_lower and (
            "content" in prompt_lower or "document" in prompt_lower
        ):
            return self._mock_content_analysis(prompt)

        # Default empty response
        return {}

    def _mock_content_analysis(self, prompt: str) -> dict[str, Any]:
        """Return mock content analysis based on document content."""
        return {
            "core_thesis": "This document explains a technical concept with practical applications.",
            "key_concepts": [
                {
                    "name": "Core Concept",
                    "explanation": "The fundamental idea that drives the topic.",
                    "complexity": 5,
                    "prerequisites": ["basic understanding"],
                    "analogies": ["Like a simple real-world example"],
                    "visual_potential": "high",
                },
                {
                    "name": "Supporting Concept",
                    "explanation": "A related idea that helps understand the core concept.",
                    "complexity": 4,
                    "prerequisites": ["core concept"],
                    "analogies": ["Similar to another familiar concept"],
                    "visual_potential": "medium",
                },
                {
                    "name": "Application",
                    "explanation": "How this concept is used in practice.",
                    "complexity": 6,
                    "prerequisites": ["core concept", "supporting concept"],
                    "analogies": ["Like using a tool for a job"],
                    "visual_potential": "high",
                },
            ],
            "target_audience": "Technical professionals and enthusiasts",
            "estimated_duration_minutes": 3,
            "complexity_score": 5,
        }

    def _mock_script_generation(self, prompt: str) -> dict[str, Any]:
        """Return mock script for testing."""
        return {
            "title": "Understanding the Core Concept",
            "total_duration_seconds": 180,
            "source_document": "document.md",
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_type": "hook",
                    "title": "The Problem",
                    "voiceover": "Every day, we encounter this challenge. What if there was a better way?",
                    "visual_cue": {
                        "description": "Show the problem visually",
                        "visual_type": "animation",
                        "elements": ["problem_illustration"],
                        "duration_seconds": 15.0,
                    },
                    "duration_seconds": 15.0,
                    "notes": "Build intrigue",
                },
                {
                    "scene_id": 2,
                    "scene_type": "context",
                    "title": "Background",
                    "voiceover": "To understand the solution, we first need to understand the context.",
                    "visual_cue": {
                        "description": "Show background context",
                        "visual_type": "animation",
                        "elements": ["context_diagram"],
                        "duration_seconds": 20.0,
                    },
                    "duration_seconds": 20.0,
                    "notes": "Set the stage",
                },
                {
                    "scene_id": 3,
                    "scene_type": "explanation",
                    "title": "The Core Concept",
                    "voiceover": "Here's how it works. The key insight is understanding the relationship between components.",
                    "visual_cue": {
                        "description": "Explain the core concept with visuals",
                        "visual_type": "animation",
                        "elements": ["concept_visualization"],
                        "duration_seconds": 30.0,
                    },
                    "duration_seconds": 30.0,
                    "notes": "Main explanation",
                },
                {
                    "scene_id": 4,
                    "scene_type": "insight",
                    "title": "The Key Insight",
                    "voiceover": "This is the breakthrough. Once you understand this, everything else falls into place.",
                    "visual_cue": {
                        "description": "Highlight the key insight",
                        "visual_type": "animation",
                        "elements": ["insight_highlight"],
                        "duration_seconds": 25.0,
                    },
                    "duration_seconds": 25.0,
                    "notes": "Aha moment",
                },
                {
                    "scene_id": 5,
                    "scene_type": "conclusion",
                    "title": "Putting It Together",
                    "voiceover": "Now you understand the concept. Let's see how it applies in practice.",
                    "visual_cue": {
                        "description": "Summary and application",
                        "visual_type": "animation",
                        "elements": ["summary"],
                        "duration_seconds": 20.0,
                    },
                    "duration_seconds": 20.0,
                    "notes": "Wrap up",
                },
            ],
        }

    def _mock_storyboard_generation(self, prompt: str = "") -> dict[str, Any]:
        """Return mock storyboard beats for testing."""
        return {
            "id": "test_storyboard",
            "title": "Test Storyboard",
            "duration_seconds": 60,
            "beats": [
                {
                    "id": "setup",
                    "start_seconds": 0,
                    "end_seconds": 10,
                    "voiceover": "Introduction to the concept.",
                    "elements": [
                        {
                            "id": "title",
                            "component": "title_card",
                            "props": {"heading": "Test Video", "subheading": "A demonstration"},
                            "position": {"x": "center", "y": "center"},
                            "enter": {"type": "fade", "duration_seconds": 0.5},
                            "exit": {"type": "fade", "duration_seconds": 0.5},
                        }
                    ],
                },
                {
                    "id": "main",
                    "start_seconds": 10,
                    "end_seconds": 50,
                    "voiceover": "The main explanation of the concept.",
                    "elements": [
                        {
                            "id": "content",
                            "component": "text_reveal",
                            "props": {"text": "Main content here"},
                            "position": {"x": "center", "y": "center"},
                        }
                    ],
                },
                {
                    "id": "conclusion",
                    "start_seconds": 50,
                    "end_seconds": 60,
                    "voiceover": "Summary and takeaways.",
                    "elements": [
                        {
                            "id": "outro",
                            "component": "title_card",
                            "props": {"heading": "Thank You"},
                            "position": {"x": "center", "y": "center"},
                        }
                    ],
                },
            ],
            "style": {
                "background_color": "#0f0f1a",
                "primary_color": "#00d9ff",
                "secondary_color": "#ff6b35",
                "font_family": "Inter",
            },
        }


class ClaudeCodeLLMProvider(LLMProvider):
    """LLM provider using Claude Code CLI in headless mode.

    This provider executes the claude CLI tool to generate responses,
    with the ability to read and modify files in the working directory.
    """

    DEFAULT_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    def __init__(
        self,
        config: LLMConfig,
        working_dir: Path | None = None,
        timeout: int = 300,
    ):
        """Initialize the Claude Code provider.

        Args:
            config: LLM configuration
            working_dir: Working directory for file operations (default: cwd)
            timeout: Command timeout in seconds (default: 300)
        """
        super().__init__(config)
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a text response via Claude Code CLI.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            The generated text response

        Raises:
            ClaudeCodeError: If the CLI command fails
        """
        cmd = self._build_command(prompt, system_prompt, tools=[])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.working_dir),
            timeout=self.timeout,
        )

        if result.returncode != 0:
            raise ClaudeCodeError(f"Claude Code failed: {result.stderr}")

        return result.stdout.strip()

    def generate_json(
        self, prompt: str, system_prompt: str | None = None
    ) -> dict[str, Any]:
        """Generate a JSON response via Claude Code CLI.

        The prompt is augmented to request JSON output, and the response
        is parsed to extract the JSON content.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            Parsed JSON response as a dictionary

        Raises:
            ClaudeCodeError: If the CLI command fails or JSON parsing fails
        """
        json_prompt = f"{prompt}\n\nRespond with valid JSON only. No markdown code blocks."
        cmd = self._build_command(json_prompt, system_prompt, tools=[])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.working_dir),
            timeout=self.timeout,
        )

        if result.returncode != 0:
            raise ClaudeCodeError(f"Claude Code failed: {result.stderr}")

        return self._parse_json_response(result.stdout)

    def generate_with_file_access(
        self,
        prompt: str,
        system_prompt: str | None = None,
        allow_writes: bool = False,
    ) -> ClaudeCodeResult:
        """Generate a response with file read/write capabilities.

        This method allows Claude Code to read and optionally modify files
        in the working directory.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            allow_writes: If True, allows Write and Edit tools

        Returns:
            ClaudeCodeResult with response and list of modified files
        """
        if allow_writes:
            tools = self.DEFAULT_TOOLS
        else:
            tools = ["Read", "Glob", "Grep"]

        cmd = self._build_command(prompt, system_prompt, tools=tools)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.working_dir),
                timeout=self.timeout,
            )

            if result.returncode != 0:
                return ClaudeCodeResult(
                    response="",
                    success=False,
                    error_message=f"Claude Code failed: {result.stderr}",
                )

            # Extract modified files from output if writes were allowed
            modified_files = []
            if allow_writes:
                modified_files = self._extract_modified_files(result.stdout)

            return ClaudeCodeResult(
                response=result.stdout.strip(),
                modified_files=modified_files,
                success=True,
            )

        except subprocess.TimeoutExpired:
            return ClaudeCodeResult(
                response="",
                success=False,
                error_message=f"Claude Code timed out after {self.timeout}s",
            )

    def _build_command(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[str] | None = None,
    ) -> list[str]:
        """Build the claude CLI command.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            tools: List of allowed tools (empty list = no tools)

        Returns:
            Command as list of strings
        """
        cmd = ["claude", "--print", "-p", prompt]

        # Add model if specified in config
        if self.config.model:
            cmd.extend(["--model", self.config.model])

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Only add tools if list is non-empty
        if tools:
            cmd.extend(["--allowedTools", ",".join(tools)])
            cmd.append("--dangerously-skip-permissions")

        return cmd

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from Claude Code response.

        Handles responses that may include markdown code blocks.

        Args:
            response: Raw response text

        Returns:
            Parsed JSON dictionary

        Raises:
            ClaudeCodeError: If JSON parsing fails
        """
        text = response.strip()

        # Try to extract JSON from markdown code blocks
        json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(json_block_pattern, text)
        if matches:
            text = matches[0].strip()

        # Try to find JSON object or array
        json_pattern = r"(\{[\s\S]*\}|\[[\s\S]*\])"
        json_match = re.search(json_pattern, text)
        if json_match:
            text = json_match.group(1)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ClaudeCodeError(f"Failed to parse JSON response: {e}\nResponse: {response[:500]}")

    def _extract_modified_files(self, output: str) -> list[str]:
        """Extract list of modified files from Claude Code output.

        Uses git to detect actual file modifications, which is more reliable
        than parsing CLI output.

        Args:
            output: Raw CLI output (used as fallback)

        Returns:
            List of modified file paths
        """
        modified = []

        # Primary method: Use git to detect modified files
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                cwd=str(self.working_dir),
                timeout=10,
            )
            if result.returncode == 0:
                git_modified = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
                if git_modified:
                    return git_modified
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Fall back to output parsing

        # Fallback: Look for common patterns in output
        patterns = [
            r"(?:Wrote|Created|Updated|Modified|Edited)\s+['\"]?([^\s'\"]+)['\"]?",
            r"Writing to\s+['\"]?([^\s'\"]+)['\"]?",
            r"File saved:\s+['\"]?([^\s'\"]+)['\"]?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            modified.extend(matches)

        return list(set(modified))  # Remove duplicates


def get_llm_provider(config: Config | None = None) -> LLMProvider:
    """Get the appropriate LLM provider based on configuration.

    Args:
        config: Configuration object. If None, loads default config.

    Returns:
        An LLM provider instance.

    Raises:
        ValueError: If provider name is not recognized.
    """
    if config is None:
        from ..config import load_config

        config = load_config()

    provider_name = config.llm.provider.lower()

    if provider_name == "mock":
        return MockLLMProvider(config.llm)
    elif provider_name == "claude-code":
        return ClaudeCodeLLMProvider(config.llm)
    elif provider_name == "anthropic":
        # TODO: Implement AnthropicLLMProvider
        raise NotImplementedError("Anthropic provider not yet implemented")
    elif provider_name == "openai":
        # TODO: Implement OpenAILLMProvider
        raise NotImplementedError("OpenAI provider not yet implemented")
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
