"""Test fixtures for web backend tests."""

import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from src.web.backend.app import create_app
from src.web.backend.config import WebConfig
from src.web.backend.services.job_manager import JobManager
from src.web.backend.websocket.manager import WebSocketManager
from src.web.backend import dependencies


@pytest.fixture
def test_projects_dir(tmp_path: Path) -> Path:
    """Create a temporary projects directory."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return projects_dir


@pytest.fixture
def sample_project(test_projects_dir: Path) -> Path:
    """Create a sample project for testing."""
    project_id = "test-project"
    project_dir = test_projects_dir / project_id
    project_dir.mkdir()

    # Create config.json with paths (project loader expects config.json)
    project_config = {
        "id": project_id,
        "title": "Test Project",
        "description": "A test project",
        "version": "1.0.0",
        "video": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "target_duration_seconds": 300,
        },
        "tts": {
            "provider": "edge",
            "voice_id": "en-US-JennyNeural",
        },
        "style": {
            "background_color": "#1a1a2e",
            "primary_color": "#4dabf7",
            "secondary_color": "#f06595",
            "font_family": "Inter",
        },
        "paths": {
            "narration": "narration.json",
            "storyboard": "storyboard.json",
            "voiceover": "voiceover/",
            "output": "output/",
            "final_video": "output/final.mp4",
        },
    }
    with open(project_dir / "config.json", "w") as f:
        json.dump(project_config, f, indent=2)

    # Create output directory
    (project_dir / "output").mkdir()

    return project_dir


@pytest.fixture
def sample_narrations(sample_project: Path) -> Path:
    """Create sample narrations for a project."""
    narrations = {
        "scenes": [
            {
                "scene_id": "scene_01",
                "title": "Introduction",
                "duration_seconds": 15,
                "narration": "Welcome to this test video.",
            },
            {
                "scene_id": "scene_02",
                "title": "Main Content",
                "duration_seconds": 30,
                "narration": "This is the main content of the video.",
            },
        ]
    }
    narration_path = sample_project / "narration.json"
    with open(narration_path, "w") as f:
        json.dump(narrations, f, indent=2)
    return narration_path


@pytest.fixture
def sample_storyboard(sample_project: Path) -> Path:
    """Create a sample storyboard for a project."""
    storyboard = {
        "scenes": [
            {
                "id": "scene_01",
                "title": "Introduction",
                "audio_duration_seconds": 15,
            },
            {
                "id": "scene_02",
                "title": "Main Content",
                "audio_duration_seconds": 30,
            },
        ],
        "total_duration_seconds": 45,
    }
    storyboard_path = sample_project / "storyboard.json"
    with open(storyboard_path, "w") as f:
        json.dump(storyboard, f, indent=2)
    return storyboard_path


@pytest.fixture
def test_config(test_projects_dir: Path) -> WebConfig:
    """Create a test configuration."""
    return WebConfig(
        host="127.0.0.1",
        port=8000,
        projects_dir=test_projects_dir,
        cors_origins=["*"],
    )


@pytest.fixture
def job_manager() -> JobManager:
    """Create a fresh job manager for testing."""
    return JobManager(max_workers=2)


@pytest.fixture
def ws_manager() -> WebSocketManager:
    """Create a fresh WebSocket manager for testing."""
    return WebSocketManager()


@pytest.fixture
def test_client(
    test_config: WebConfig,
    job_manager: JobManager,
    ws_manager: WebSocketManager,
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    from src.web.backend.app import create_app
    from src.web.backend.dependencies import (
        get_config,
        get_job_manager,
        get_websocket_manager,
    )

    # Clear any cached dependencies
    dependencies.get_config.cache_clear()
    dependencies.get_job_manager.cache_clear()
    dependencies.get_websocket_manager.cache_clear()

    job_manager.set_websocket_manager(ws_manager)

    # Create app without lifespan to avoid dependency issues
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from src.web.backend.routers import (
        projects_router,
        narrations_router,
        voiceovers_router,
        render_router,
        feedback_router,
        sound_router,
        files_router,
        jobs_router,
        storyboard_router,
    )

    app = FastAPI(title="Video Explainer API - Test")

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(narrations_router, prefix="/api/v1")
    app.include_router(voiceovers_router, prefix="/api/v1")
    app.include_router(render_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(sound_router, prefix="/api/v1")
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(storyboard_router, prefix="/api/v1")

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # Override dependencies
    app.dependency_overrides[get_config] = lambda: test_config
    app.dependency_overrides[get_job_manager] = lambda: job_manager
    app.dependency_overrides[get_websocket_manager] = lambda: ws_manager

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    job_manager.shutdown(wait=False)
