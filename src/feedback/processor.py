"""Feedback processor for analyzing and applying feedback."""

import json
import subprocess
from pathlib import Path
from typing import Any

from ..config import LLMConfig
from ..project.loader import Project
from ..understanding.llm_provider import ClaudeCodeLLMProvider, ClaudeCodeError
from .models import FeedbackItem, FeedbackScope, FeedbackStatus
from .prompts import (
    ANALYZE_FEEDBACK_PROMPT,
    APPLY_FEEDBACK_PROMPT,
    APPLY_FEEDBACK_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from .store import FeedbackStore


class FeedbackProcessor:
    """Processes feedback using Claude Code to analyze and apply changes."""

    def __init__(
        self,
        project: Project,
        dry_run: bool = False,
        create_branch: bool = True,
    ):
        """Initialize the feedback processor.

        Args:
            project: The project to apply feedback to
            dry_run: If True, analyze but don't apply changes
            create_branch: If True, create a preview branch for changes
        """
        self.project = project
        self.dry_run = dry_run
        self.create_branch = create_branch
        self.store = FeedbackStore(project.root_dir, project.id)

        # Use repo root as working directory so Claude Code can access both:
        # - projects/{project-id}/ (storyboard, narrations)
        # - remotion/src/scenes/{project-id}/ (scene components)
        # Project root is like: /path/to/video_explainer/projects/llm-inference
        # Repo root is: /path/to/video_explainer
        repo_root = project.root_dir.parent.parent  # Go up from projects/{project-id}

        # Initialize Claude Code provider with REPO root (using Opus 4.5 for best quality)
        llm_config = LLMConfig(provider="claude-code", model="claude-opus-4-5-20251101")
        self.llm = ClaudeCodeLLMProvider(
            llm_config,
            working_dir=repo_root,
            timeout=600,  # 10 minutes for complex changes with Opus
        )

    def process_feedback(self, feedback_text: str) -> FeedbackItem:
        """Process a feedback item from start to finish.

        Args:
            feedback_text: The user's feedback

        Returns:
            The processed FeedbackItem with results
        """
        # Add feedback to store
        item = self.store.add_feedback(feedback_text)
        item.status = FeedbackStatus.PROCESSING

        try:
            # Step 1: Analyze the feedback
            item = self._analyze_feedback(item)

            if self.dry_run:
                # In dry run mode, just return the analysis
                item.status = FeedbackStatus.PENDING
                self.store.update_item(item)
                return item

            # Step 2: Create preview branch if requested
            if self.create_branch:
                branch_name = self._create_preview_branch(item)
                item.preview_branch = branch_name

            # Step 3: Apply the changes
            item = self._apply_changes(item)

            # Step 4: Update status
            if item.files_modified:
                item.status = FeedbackStatus.APPLIED
            elif item.error_message:
                # Keep existing error message from apply step
                item.status = FeedbackStatus.FAILED
            else:
                item.status = FeedbackStatus.FAILED
                item.error_message = "No files were modified"

        except Exception as e:
            item.status = FeedbackStatus.FAILED
            item.error_message = str(e)

        self.store.update_item(item)
        return item

    def _get_scene_list(self) -> list[str]:
        """Get list of scene IDs from the project.

        Returns:
            List of scene IDs
        """
        try:
            storyboard = self.project.load_storyboard()
            scenes = storyboard.get("scenes", [])
            return [scene.get("scene_id", str(i)) for i, scene in enumerate(scenes)]
        except FileNotFoundError:
            # Try narrations if storyboard doesn't exist
            try:
                narrations = self.project.load_narrations()
                return [n.scene_id for n in narrations]
            except FileNotFoundError:
                return []

    def _analyze_feedback(self, item: FeedbackItem) -> FeedbackItem:
        """Analyze feedback to determine scope and affected scenes.

        Args:
            item: The feedback item to analyze

        Returns:
            Updated FeedbackItem with analysis
        """
        scene_list = self._get_scene_list()

        prompt = ANALYZE_FEEDBACK_PROMPT.format(
            feedback_text=item.feedback_text,
            project_id=self.project.id,
            scene_list=", ".join(scene_list) if scene_list else "none found",
        )

        try:
            result = self.llm.generate_json(prompt, system_prompt=SYSTEM_PROMPT)

            # Parse scope
            scope_str = result.get("scope", "scene")
            try:
                item.scope = FeedbackScope(scope_str)
            except ValueError:
                item.scope = FeedbackScope.SCENE

            item.affected_scenes = result.get("affected_scenes", [])
            item.interpretation = result.get("interpretation", "")
            item.suggested_changes = result.get("suggested_changes", {})

        except ClaudeCodeError as e:
            # If analysis fails, set minimal info
            item.interpretation = f"Analysis failed: {e}"
            item.scope = FeedbackScope.SCENE

        return item

    def _create_preview_branch(self, item: FeedbackItem) -> str:
        """Create a git branch for preview changes.

        Args:
            item: The feedback item

        Returns:
            The branch name
        """
        branch_name = f"feedback/{item.id}"

        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.project.root_dir),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Not in a git repo, skip branch creation
                return ""

            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self.project.root_dir),
                capture_output=True,
                check=True,
            )

            return branch_name

        except subprocess.CalledProcessError:
            # Branch creation failed, continue without it
            return ""

    def _apply_changes(self, item: FeedbackItem) -> FeedbackItem:
        """Apply the feedback changes using Claude Code.

        Args:
            item: The feedback item with analysis

        Returns:
            Updated FeedbackItem with applied changes
        """
        prompt = APPLY_FEEDBACK_PROMPT.format(
            feedback_text=item.feedback_text,
            interpretation=item.interpretation,
            suggested_changes=json.dumps(item.suggested_changes, indent=2),
        )

        result = self.llm.generate_with_file_access(
            prompt,
            system_prompt=APPLY_FEEDBACK_SYSTEM_PROMPT,
            allow_writes=True,
        )

        if result.success:
            item.files_modified = result.modified_files
        else:
            item.error_message = result.error_message

        return item

    def list_feedback(self) -> list[FeedbackItem]:
        """List all feedback items for the project.

        Returns:
            List of all FeedbackItem objects
        """
        history = self.store.load()
        return history.items

    def get_feedback(self, item_id: str) -> FeedbackItem | None:
        """Get a specific feedback item.

        Args:
            item_id: The feedback item ID

        Returns:
            The FeedbackItem or None if not found
        """
        return self.store.get_item(item_id)


def process_feedback(
    project: Project,
    feedback_text: str,
    dry_run: bool = False,
    create_branch: bool = True,
) -> FeedbackItem:
    """Convenience function to process feedback.

    Args:
        project: The project to apply feedback to
        feedback_text: The user's feedback
        dry_run: If True, analyze but don't apply changes
        create_branch: If True, create a preview branch for changes

    Returns:
        The processed FeedbackItem
    """
    processor = FeedbackProcessor(
        project,
        dry_run=dry_run,
        create_branch=create_branch,
    )
    return processor.process_feedback(feedback_text)
