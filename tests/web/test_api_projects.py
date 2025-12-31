"""Tests for project API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestProjectsAPI:
    """Tests for /api/v1/projects endpoints."""

    def test_list_projects_empty(self, test_client: TestClient) -> None:
        """Test listing projects when none exist."""
        response = test_client.get("/api/v1/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test listing projects when projects exist."""
        response = test_client.get("/api/v1/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["id"] == "test-project"
        assert projects[0]["title"] == "Test Project"

    def test_create_project(self, test_client: TestClient) -> None:
        """Test creating a new project."""
        response = test_client.post(
            "/api/v1/projects",
            json={
                "id": "new-project",
                "title": "New Project",
                "description": "A new test project",
            },
        )
        assert response.status_code == 201
        project = response.json()
        assert project["id"] == "new-project"
        assert project["title"] == "New Project"
        assert project["description"] == "A new test project"

    def test_create_project_duplicate(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test creating a project with duplicate ID."""
        response = test_client.post(
            "/api/v1/projects",
            json={
                "id": "test-project",
                "title": "Duplicate Project",
            },
        )
        assert response.status_code == 409

    def test_get_project(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test getting a specific project."""
        response = test_client.get("/api/v1/projects/test-project")
        assert response.status_code == 200
        project = response.json()
        assert project["id"] == "test-project"
        assert project["title"] == "Test Project"
        assert project["video"]["width"] == 1920
        assert project["video"]["height"] == 1080

    def test_get_project_not_found(self, test_client: TestClient) -> None:
        """Test getting a non-existent project."""
        response = test_client.get("/api/v1/projects/nonexistent")
        assert response.status_code == 404

    def test_delete_project(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test deleting a project."""
        response = test_client.delete("/api/v1/projects/test-project")
        assert response.status_code == 204

        # Verify deleted
        response = test_client.get("/api/v1/projects/test-project")
        assert response.status_code == 404

    def test_delete_project_not_found(self, test_client: TestClient) -> None:
        """Test deleting a non-existent project."""
        response = test_client.delete("/api/v1/projects/nonexistent")
        assert response.status_code == 404


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, test_client: TestClient) -> None:
        """Test health check returns ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
