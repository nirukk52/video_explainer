"""Tests for service layer."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.web.backend.services.project_service import ProjectService
from src.web.backend.services.job_manager import JobManager


class TestProjectService:
    """Tests for ProjectService."""

    def test_list_projects_empty(self, test_projects_dir: Path) -> None:
        """Test listing projects when none exist."""
        service = ProjectService(projects_dir=test_projects_dir)
        projects = service.list_projects()
        assert projects == []

    def test_list_projects(
        self, test_projects_dir: Path, sample_project: Path
    ) -> None:
        """Test listing projects."""
        service = ProjectService(projects_dir=test_projects_dir)
        projects = service.list_projects()
        assert len(projects) == 1
        assert projects[0].id == "test-project"
        assert projects[0].title == "Test Project"

    def test_get_project(
        self, test_projects_dir: Path, sample_project: Path
    ) -> None:
        """Test getting a project."""
        service = ProjectService(projects_dir=test_projects_dir)
        project = service.get_project("test-project")
        assert project.id == "test-project"
        assert project.title == "Test Project"
        assert project.video.width == 1920
        assert project.video.height == 1080

    def test_get_project_not_found(self, test_projects_dir: Path) -> None:
        """Test getting a non-existent project."""
        service = ProjectService(projects_dir=test_projects_dir)
        with pytest.raises(FileNotFoundError):
            service.get_project("nonexistent")

    def test_create_project(self, test_projects_dir: Path) -> None:
        """Test creating a project."""
        service = ProjectService(projects_dir=test_projects_dir)
        project = service.create_project(
            project_id="new-project",
            title="New Project",
            description="A new project",
        )
        assert project.id == "new-project"
        assert project.title == "New Project"

        # Verify files exist
        project_dir = test_projects_dir / "new-project"
        assert project_dir.exists()
        assert (project_dir / "config.json").exists()

    def test_delete_project(
        self, test_projects_dir: Path, sample_project: Path
    ) -> None:
        """Test deleting a project."""
        service = ProjectService(projects_dir=test_projects_dir)
        service.delete_project("test-project")

        # Verify deleted
        assert not sample_project.exists()

    def test_delete_project_not_found(self, test_projects_dir: Path) -> None:
        """Test deleting a non-existent project."""
        service = ProjectService(projects_dir=test_projects_dir)
        with pytest.raises(FileNotFoundError):
            service.delete_project("nonexistent")

    def test_get_narrations(
        self,
        test_projects_dir: Path,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test getting narrations."""
        service = ProjectService(projects_dir=test_projects_dir)
        narrations = service.get_narrations("test-project")
        assert len(narrations) == 2
        assert narrations[0].scene_id == "scene_01"
        assert narrations[0].title == "Introduction"

    def test_get_narrations_empty(
        self, test_projects_dir: Path, sample_project: Path
    ) -> None:
        """Test getting narrations when none exist."""
        service = ProjectService(projects_dir=test_projects_dir)
        narrations = service.get_narrations("test-project")
        assert narrations == []

    def test_update_narration(
        self,
        test_projects_dir: Path,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test updating a narration."""
        service = ProjectService(projects_dir=test_projects_dir)
        narration = service.update_narration(
            project_id="test-project",
            scene_id="scene_01",
            narration="Updated text",
            title="Updated Title",
        )
        assert narration.narration == "Updated text"
        assert narration.title == "Updated Title"

    def test_add_narration(
        self, test_projects_dir: Path, sample_project: Path
    ) -> None:
        """Test adding a narration."""
        service = ProjectService(projects_dir=test_projects_dir)
        narration = service.add_narration(
            project_id="test-project",
            scene_id="new_scene",
            title="New Scene",
            narration="New narration text",
        )
        assert narration.scene_id == "new_scene"
        assert narration.title == "New Scene"

    def test_delete_narration(
        self,
        test_projects_dir: Path,
        sample_project: Path,
        sample_narrations: Path,
    ) -> None:
        """Test deleting a narration."""
        service = ProjectService(projects_dir=test_projects_dir)
        service.delete_narration("test-project", "scene_01")

        narrations = service.get_narrations("test-project")
        assert len(narrations) == 1
        assert narrations[0].scene_id == "scene_02"

    def test_get_storyboard(
        self,
        test_projects_dir: Path,
        sample_project: Path,
        sample_storyboard: Path,
    ) -> None:
        """Test getting a storyboard."""
        service = ProjectService(projects_dir=test_projects_dir)
        storyboard = service.get_storyboard("test-project")
        assert "scenes" in storyboard
        assert len(storyboard["scenes"]) == 2

    def test_update_storyboard(
        self,
        test_projects_dir: Path,
        sample_project: Path,
        sample_storyboard: Path,
    ) -> None:
        """Test updating a storyboard."""
        service = ProjectService(projects_dir=test_projects_dir)
        new_storyboard = {"scenes": [], "total_duration_seconds": 0}
        result = service.update_storyboard("test-project", new_storyboard)
        assert result == new_storyboard
