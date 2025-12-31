"""Background job manager for long-running operations.

Manages voiceover generation, rendering, feedback processing, etc.
Jobs run in a thread pool and report progress via callbacks.
"""

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..websocket.manager import WebSocketManager


class JobStatus(str, Enum):
    """Status of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Type of background job."""

    VOICEOVER = "voiceover"
    RENDER = "render"
    FEEDBACK = "feedback"
    SOUND = "sound"


@dataclass
class Job:
    """A background job."""

    id: str
    type: JobType
    project_id: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    _future: Future | None = field(default=None, repr=False)


class JobManager:
    """Manages background jobs with progress tracking.

    Jobs are executed in a thread pool and can report progress
    updates which are broadcast via WebSocket.
    """

    def __init__(self, max_workers: int = 4):
        """Initialize the job manager.

        Args:
            max_workers: Maximum number of concurrent jobs.
        """
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._ws_manager: "WebSocketManager | None" = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_websocket_manager(self, ws_manager: "WebSocketManager") -> None:
        """Set the WebSocket manager for broadcasting updates.

        Args:
            ws_manager: WebSocket manager instance.
        """
        self._ws_manager = ws_manager

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for async callbacks.

        Args:
            loop: The asyncio event loop.
        """
        self._loop = loop

    def submit_job(
        self,
        job_type: JobType,
        project_id: str,
        task: Callable[["JobManager", str], dict[str, Any]],
    ) -> str:
        """Submit a background job.

        Args:
            job_type: Type of job (voiceover, render, etc.).
            project_id: ID of the project this job belongs to.
            task: Callable that takes (job_manager, job_id) and returns result dict.

        Returns:
            The job ID.
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(
            id=job_id,
            type=job_type,
            project_id=project_id,
            message="Job queued",
        )

        with self._lock:
            self._jobs[job_id] = job

        def run_task() -> dict[str, Any]:
            try:
                self.update_status(job_id, JobStatus.RUNNING, "Job started")
                result = task(self, job_id)
                self.update_status(job_id, JobStatus.COMPLETED, "Job completed", result=result)
                return result
            except Exception as e:
                self.update_status(job_id, JobStatus.FAILED, str(e), error=str(e))
                raise

        future = self._executor.submit(run_task)
        job._future = future

        return job_id

    def update_progress(self, job_id: str, progress: float, message: str) -> None:
        """Update job progress.

        Args:
            job_id: The job ID.
            progress: Progress from 0.0 to 1.0.
            message: Status message.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = min(max(progress, 0.0), 1.0)
                job.message = message
                job.updated_at = datetime.now()
                self._broadcast_update(job)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        message: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status.

        Args:
            job_id: The job ID.
            status: New status.
            message: Status message.
            result: Optional result dict (for completed jobs).
            error: Optional error message (for failed jobs).
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.message = message
                job.updated_at = datetime.now()
                if result is not None:
                    job.result = result
                    job.progress = 1.0
                if error is not None:
                    job.error = error
                self._broadcast_update(job)

    def _broadcast_update(self, job: Job) -> None:
        """Broadcast job update via WebSocket.

        Args:
            job: The job to broadcast.
        """
        if self._ws_manager and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._ws_manager.broadcast_job_update(job),
                    self._loop,
                )
            except Exception:
                # Ignore broadcast errors (client may have disconnected)
                pass

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: The job ID.

        Returns:
            The job, or None if not found.
        """
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, project_id: str | None = None) -> list[Job]:
        """List all jobs, optionally filtered by project.

        Args:
            project_id: Optional project ID to filter by.

        Returns:
            List of jobs.
        """
        with self._lock:
            jobs = list(self._jobs.values())
            if project_id:
                jobs = [j for j in jobs if j.project_id == project_id]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: The job ID.

        Returns:
            True if the job was cancelled, False otherwise.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
                return False
            if job._future:
                job._future.cancel()
            job.status = JobStatus.CANCELLED
            job.message = "Job cancelled"
            job.updated_at = datetime.now()
            return True

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> int:
        """Remove old completed/failed jobs.

        Args:
            max_age_seconds: Maximum age of jobs to keep.

        Returns:
            Number of jobs removed.
        """
        cutoff = datetime.now()
        removed = 0
        with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    age = (cutoff - job.updated_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(job_id)
            for job_id in to_remove:
                del self._jobs[job_id]
                removed += 1
        return removed

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the job manager.

        Args:
            wait: Whether to wait for running jobs to complete.
        """
        self._executor.shutdown(wait=wait)
