"""Tests for the job manager."""

import time
from typing import Any

import pytest

from src.web.backend.services.job_manager import (
    JobManager,
    JobStatus,
    JobType,
)


class TestJobManager:
    """Tests for JobManager."""

    def test_submit_job(self, job_manager: JobManager) -> None:
        """Test submitting a job."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {"result": "success"}

        job_id = job_manager.submit_job(JobType.VOICEOVER, "test-project", task)
        assert job_id.startswith("job_")

        # Wait for completion
        time.sleep(0.1)
        job = job_manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.result == {"result": "success"}

    def test_submit_job_failure(self, job_manager: JobManager) -> None:
        """Test job that fails."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            raise ValueError("Test error")

        job_id = job_manager.submit_job(JobType.RENDER, "test-project", task)

        # Wait for failure
        time.sleep(0.1)
        job = job_manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "Test error"

    def test_update_progress(self, job_manager: JobManager) -> None:
        """Test updating job progress."""
        progress_updates = []

        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            jm.update_progress(job_id, 0.5, "Halfway done")
            progress_updates.append((0.5, "Halfway done"))
            return {"result": "done"}

        job_id = job_manager.submit_job(JobType.FEEDBACK, "test-project", task)

        # Wait for completion
        time.sleep(0.1)
        assert len(progress_updates) == 1
        assert progress_updates[0] == (0.5, "Halfway done")

    def test_list_jobs(self, job_manager: JobManager) -> None:
        """Test listing jobs."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {}

        job_manager.submit_job(JobType.VOICEOVER, "project-1", task)
        job_manager.submit_job(JobType.RENDER, "project-2", task)

        # Wait for completion
        time.sleep(0.1)

        all_jobs = job_manager.list_jobs()
        assert len(all_jobs) == 2

        project1_jobs = job_manager.list_jobs(project_id="project-1")
        assert len(project1_jobs) == 1
        assert project1_jobs[0].project_id == "project-1"

    def test_get_job_not_found(self, job_manager: JobManager) -> None:
        """Test getting a non-existent job."""
        job = job_manager.get_job("nonexistent")
        assert job is None

    def test_cancel_job(self, job_manager: JobManager) -> None:
        """Test cancelling a job."""
        def slow_task(jm: JobManager, job_id: str) -> dict[str, Any]:
            time.sleep(10)
            return {}

        job_id = job_manager.submit_job(JobType.RENDER, "test-project", slow_task)

        # Cancel immediately
        result = job_manager.cancel_job(job_id)
        assert result is True

        job = job_manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.CANCELLED

    def test_cancel_completed_job(self, job_manager: JobManager) -> None:
        """Test cancelling a completed job fails."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {}

        job_id = job_manager.submit_job(JobType.VOICEOVER, "test-project", task)

        # Wait for completion
        time.sleep(0.1)

        result = job_manager.cancel_job(job_id)
        assert result is False

    def test_cleanup_old_jobs(self, job_manager: JobManager) -> None:
        """Test cleaning up old jobs."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {}

        job_manager.submit_job(JobType.VOICEOVER, "test-project", task)

        # Wait for completion
        time.sleep(0.1)

        # Cleanup with 0 second max age (should remove all)
        removed = job_manager.cleanup_old_jobs(max_age_seconds=0)
        assert removed == 1

        jobs = job_manager.list_jobs()
        assert len(jobs) == 0

    def test_job_types(self, job_manager: JobManager) -> None:
        """Test all job types."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {}

        for job_type in JobType:
            job_id = job_manager.submit_job(job_type, "test-project", task)
            job = job_manager.get_job(job_id)
            assert job.type == job_type
