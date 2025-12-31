"""Tests for jobs API endpoints."""

import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.web.backend.services.job_manager import JobManager, JobType


class TestJobsAPI:
    """Tests for /api/v1/jobs endpoints."""

    def test_list_jobs_empty(self, test_client: TestClient) -> None:
        """Test listing jobs when none exist."""
        response = test_client.get("/api/v1/jobs")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_with_data(
        self, test_client: TestClient, job_manager: JobManager
    ) -> None:
        """Test listing jobs when jobs exist."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {"test": "result"}

        job_manager.submit_job(JobType.VOICEOVER, "test-project", task)
        time.sleep(0.1)  # Wait for job to complete

        response = test_client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["type"] == "voiceover"
        assert jobs[0]["status"] == "completed"

    def test_list_jobs_filter_by_project(
        self, test_client: TestClient, job_manager: JobManager
    ) -> None:
        """Test filtering jobs by project ID."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {}

        job_manager.submit_job(JobType.VOICEOVER, "project-1", task)
        job_manager.submit_job(JobType.RENDER, "project-2", task)
        time.sleep(0.1)

        response = test_client.get("/api/v1/jobs?project_id=project-1")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["project_id"] == "project-1"

    def test_get_job(
        self, test_client: TestClient, job_manager: JobManager
    ) -> None:
        """Test getting a specific job."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {"result": "success"}

        job_id = job_manager.submit_job(JobType.FEEDBACK, "test-project", task)
        time.sleep(0.1)

        response = test_client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        assert job["job_id"] == job_id
        assert job["type"] == "feedback"
        assert job["status"] == "completed"
        assert job["result"] == {"result": "success"}

    def test_get_job_not_found(self, test_client: TestClient) -> None:
        """Test getting a non-existent job."""
        response = test_client.get("/api/v1/jobs/nonexistent")
        assert response.status_code == 404

    def test_cancel_job(
        self, test_client: TestClient, job_manager: JobManager
    ) -> None:
        """Test cancelling a running job."""
        def slow_task(jm: JobManager, job_id: str) -> dict[str, Any]:
            time.sleep(10)
            return {}

        job_id = job_manager.submit_job(JobType.RENDER, "test-project", slow_task)

        response = test_client.delete(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 204

        # Verify cancelled
        job = job_manager.get_job(job_id)
        assert job.status.value == "cancelled"

    def test_cancel_job_not_found(self, test_client: TestClient) -> None:
        """Test cancelling a non-existent job."""
        response = test_client.delete("/api/v1/jobs/nonexistent")
        assert response.status_code == 404

    def test_cancel_completed_job(
        self, test_client: TestClient, job_manager: JobManager
    ) -> None:
        """Test cancelling a completed job fails."""
        def task(jm: JobManager, job_id: str) -> dict[str, Any]:
            return {}

        job_id = job_manager.submit_job(JobType.VOICEOVER, "test-project", task)
        time.sleep(0.1)

        response = test_client.delete(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 400
