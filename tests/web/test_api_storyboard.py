"""Tests for storyboard API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestStoryboardAPI:
    """Tests for /api/v1/projects/{id}/storyboard endpoints."""

    def test_get_storyboard(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_storyboard: Path,
    ) -> None:
        """Test getting a storyboard."""
        response = test_client.get("/api/v1/projects/test-project/storyboard")
        assert response.status_code == 200
        storyboard = response.json()
        assert "scenes" in storyboard
        assert len(storyboard["scenes"]) == 2
        assert storyboard["total_duration_seconds"] == 45

    def test_get_storyboard_not_found(
        self, test_client: TestClient, sample_project: Path
    ) -> None:
        """Test getting a storyboard that doesn't exist."""
        response = test_client.get("/api/v1/projects/test-project/storyboard")
        assert response.status_code == 404

    def test_get_storyboard_project_not_found(
        self, test_client: TestClient
    ) -> None:
        """Test getting storyboard for non-existent project."""
        response = test_client.get("/api/v1/projects/nonexistent/storyboard")
        assert response.status_code == 404

    def test_update_storyboard(
        self,
        test_client: TestClient,
        sample_project: Path,
        sample_storyboard: Path,
    ) -> None:
        """Test updating a storyboard."""
        new_storyboard = {
            "scenes": [
                {
                    "id": "scene_01",
                    "title": "Updated Introduction",
                    "audio_duration_seconds": 20,
                },
            ],
            "total_duration_seconds": 20,
        }

        response = test_client.put(
            "/api/v1/projects/test-project/storyboard",
            json=new_storyboard,
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["scenes"]) == 1
        assert result["scenes"][0]["title"] == "Updated Introduction"
        assert result["total_duration_seconds"] == 20

    def test_update_storyboard_project_not_found(
        self, test_client: TestClient
    ) -> None:
        """Test updating storyboard for non-existent project."""
        response = test_client.put(
            "/api/v1/projects/nonexistent/storyboard",
            json={"scenes": []},
        )
        assert response.status_code == 404
