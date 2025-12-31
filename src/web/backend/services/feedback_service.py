"""Feedback service for processing natural language feedback."""

from datetime import datetime
from pathlib import Path
from typing import Any

from .job_manager import JobManager, JobType
from ..models.responses import FeedbackItemResponse


class FeedbackService:
    """Service for feedback processing.

    Wraps the existing feedback module without modifying it.
    """

    def __init__(self, job_manager: JobManager, projects_dir: Path | str = Path("projects")):
        """Initialize the feedback service.

        Args:
            job_manager: Job manager for background tasks.
            projects_dir: Path to the projects directory.
        """
        self.job_manager = job_manager
        self.projects_dir = Path(projects_dir)

    def process_feedback(
        self,
        project_id: str,
        feedback_text: str,
        dry_run: bool = False,
    ) -> str:
        """Start feedback processing job.

        Args:
            project_id: The project ID.
            feedback_text: The feedback text.
            dry_run: Whether to analyze without applying.

        Returns:
            The job ID.
        """

        def task(job_manager: JobManager, job_id: str) -> dict[str, Any]:
            from src.project import load_project
            from src.feedback import FeedbackProcessor

            job_manager.update_progress(job_id, 0.1, "Loading project...")

            project = load_project(self.projects_dir / project_id)

            job_manager.update_progress(job_id, 0.2, "Analyzing feedback...")

            processor = FeedbackProcessor(project, dry_run=dry_run, verbose=False)
            result = processor.process_feedback(feedback_text)

            return {
                "id": result.id,
                "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                "scope": result.scope.value if hasattr(result.scope, "value") else str(result.scope) if result.scope else None,
                "affected_scenes": result.affected_scenes or [],
                "interpretation": result.interpretation,
                "files_modified": result.files_modified or [],
                "error_message": result.error_message,
            }

        return self.job_manager.submit_job(JobType.FEEDBACK, project_id, task)

    def list_feedback(self, project_id: str) -> list[FeedbackItemResponse]:
        """List feedback history for a project.

        Args:
            project_id: The project ID.

        Returns:
            List of feedback items.
        """
        from src.project import load_project
        from src.feedback import FeedbackStore

        project = load_project(self.projects_dir / project_id)
        store = FeedbackStore(project.root_dir, project.id)
        history = store.load()

        return [
            FeedbackItemResponse(
                id=item.id,
                feedback_text=item.feedback_text,
                status=item.status.value if hasattr(item.status, "value") else str(item.status),
                scope=item.scope.value if hasattr(item.scope, "value") else str(item.scope) if item.scope else None,
                affected_scenes=item.affected_scenes or [],
                interpretation=item.interpretation,
                files_modified=item.files_modified or [],
                error_message=item.error_message,
                timestamp=datetime.fromisoformat(item.timestamp) if isinstance(item.timestamp, str) else item.timestamp,
            )
            for item in history.items
        ]

    def get_feedback(self, project_id: str, feedback_id: str) -> FeedbackItemResponse | None:
        """Get a specific feedback item.

        Args:
            project_id: The project ID.
            feedback_id: The feedback ID.

        Returns:
            The feedback item, or None if not found.
        """
        from src.project import load_project
        from src.feedback import FeedbackStore

        project = load_project(self.projects_dir / project_id)
        store = FeedbackStore(project.root_dir, project.id)
        item = store.get_item(feedback_id)

        if not item:
            return None

        return FeedbackItemResponse(
            id=item.id,
            feedback_text=item.feedback_text,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            scope=item.scope.value if hasattr(item.scope, "value") else str(item.scope) if item.scope else None,
            affected_scenes=item.affected_scenes or [],
            interpretation=item.interpretation,
            files_modified=item.files_modified or [],
            error_message=item.error_message,
            timestamp=datetime.fromisoformat(item.timestamp) if isinstance(item.timestamp, str) else item.timestamp,
        )
