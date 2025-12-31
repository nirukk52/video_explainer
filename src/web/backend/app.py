"""FastAPI application factory."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import WebConfig
from .dependencies import get_config, get_job_manager, get_websocket_manager
from .routers import (
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    job_manager = get_job_manager()
    ws_manager = get_websocket_manager()
    job_manager.set_websocket_manager(ws_manager)
    job_manager.set_event_loop(asyncio.get_event_loop())

    yield

    # Shutdown
    job_manager.shutdown(wait=True)


def create_app(config: WebConfig | None = None) -> FastAPI:
    """Create the FastAPI application.

    Args:
        config: Optional configuration. Uses defaults if not provided.

    Returns:
        The FastAPI application.
    """
    if config is None:
        config = get_config()

    app = FastAPI(
        title="Video Explainer API",
        description="API for managing video explainer projects",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
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
        """Health check endpoint."""
        return {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
        """WebSocket endpoint for real-time updates."""
        ws_manager = get_websocket_manager()
        cid = client_id or f"client_{id(websocket)}"

        await ws_manager.connect(websocket, cid)
        try:
            while True:
                data = await websocket.receive_json()
                # Handle subscription messages
                if data.get("type") == "subscribe":
                    project_id = data.get("project_id")
                    if project_id:
                        await ws_manager.subscribe_to_project(cid, project_id)
                elif data.get("type") == "unsubscribe":
                    project_id = data.get("project_id")
                    if project_id:
                        await ws_manager.unsubscribe_from_project(cid, project_id)
        except WebSocketDisconnect:
            ws_manager.disconnect(cid)

    return app
