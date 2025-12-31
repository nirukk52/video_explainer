"""Tests for narration API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestNarrationsAPI:
    """Tests for /api/v1/projects/{id}/narrations endpoints."""

    def test_list_narrations(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test listing narrations for a project."""
        response = test_client.get("/api/v1/projects/test-project/narrations")
        assert response.status_code == 200
        narrations = response.json()
        assert len(narrations) == 2
        assert narrations[0]["scene_id"] == "scene_01"
        assert narrations[0]["title"] == "Introduction"
        assert narrations[1]["scene_id"] == "scene_02"

    def test_list_narrations_empty(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test listing narrations when none exist."""
        response = test_client.get("/api/v1/projects/test-project/narrations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_narrations_project_not_found(
        self, test_client: TestClient
    ) -> None:
        """Test listing narrations for non-existent project."""
        response = test_client.get("/api/v1/projects/nonexistent/narrations")
        assert response.status_code == 404

    def test_get_narration(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test getting a specific narration."""
        response = test_client.get(
            "/api/v1/projects/test-project/narrations/scene_01"
        )
        assert response.status_code == 200
        narration = response.json()
        assert narration["scene_id"] == "scene_01"
        assert narration["title"] == "Introduction"
        assert narration["narration"] == "Welcome to this test video."

    def test_get_narration_not_found(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test getting a non-existent narration."""
        response = test_client.get(
            "/api/v1/projects/test-project/narrations/nonexistent"
        )
        assert response.status_code == 404

    def test_add_narration(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test adding a new narration."""
        response = test_client.post(
            "/api/v1/projects/test-project/narrations",
            json={
                "scene_id": "scene_new",
                "title": "New Scene",
                "narration": "This is a new scene.",
                "duration_seconds": 20,
            },
        )
        assert response.status_code == 201
        narration = response.json()
        assert narration["scene_id"] == "scene_new"
        assert narration["title"] == "New Scene"

    def test_add_narration_duplicate(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test adding a narration with duplicate scene ID."""
        response = test_client.post(
            "/api/v1/projects/test-project/narrations",
            json={
                "scene_id": "scene_01",
                "title": "Duplicate Scene",
                "narration": "This should fail.",
            },
        )
        assert response.status_code == 409

    def test_update_narration(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test updating a narration."""
        response = test_client.put(
            "/api/v1/projects/test-project/narrations/scene_01",
            json={
                "narration": "Updated narration text.",
                "title": "Updated Title",
            },
        )
        assert response.status_code == 200
        narration = response.json()
        assert narration["narration"] == "Updated narration text."
        assert narration["title"] == "Updated Title"

    def test_update_narration_not_found(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test updating a non-existent narration."""
        response = test_client.put(
            "/api/v1/projects/test-project/narrations/nonexistent",
            json={"narration": "Updated text."},
        )
        assert response.status_code == 404

    def test_delete_narration(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test deleting a narration."""
        response = test_client.delete(
            "/api/v1/projects/test-project/narrations/scene_01"
        )
        assert response.status_code == 204

        # Verify deleted
        response = test_client.get(
            "/api/v1/projects/test-project/narrations/scene_01"
        )
        assert response.status_code == 404

    def test_delete_narration_not_found(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test deleting a non-existent narration."""
        response = test_client.delete(
            "/api/v1/projects/test-project/narrations/nonexistent"
        )
        assert response.status_code == 404
