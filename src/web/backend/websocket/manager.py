"""WebSocket connection manager for real-time updates.

Handles client connections and broadcasts job updates
to subscribed clients.
"""

import json
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from ..services.job_manager import Job


class WebSocketManager:
    """Manages WebSocket connections and subscriptions.

    Clients can subscribe to specific projects to receive
    real-time updates about job progress.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        self._connections: dict[str, WebSocket] = {}
        self._project_subscriptions: dict[str, set[str]] = {}  # project_id -> client_ids

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            client_id: Unique client identifier.
        """
        await websocket.accept()
        self._connections[client_id] = websocket

    def disconnect(self, client_id: str) -> None:
        """Handle client disconnection.

        Args:
            client_id: The client identifier.
        """
        self._connections.pop(client_id, None)
        # Remove from all subscriptions
        for subscribers in self._project_subscriptions.values():
            subscribers.discard(client_id)

    async def subscribe_to_project(self, client_id: str, project_id: str) -> None:
        """Subscribe a client to a project's updates.

        Args:
            client_id: The client identifier.
            project_id: The project to subscribe to.
        """
        if project_id not in self._project_subscriptions:
            self._project_subscriptions[project_id] = set()
        self._project_subscriptions[project_id].add(client_id)

    async def unsubscribe_from_project(self, client_id: str, project_id: str) -> None:
        """Unsubscribe a client from a project.

        Args:
            client_id: The client identifier.
            project_id: The project to unsubscribe from.
        """
        if project_id in self._project_subscriptions:
            self._project_subscriptions[project_id].discard(client_id)

    async def broadcast_job_update(self, job: "Job") -> None:
        """Broadcast a job update to subscribed clients.

        Args:
            job: The job with updated status.
        """
        project_id = job.project_id
        subscribers = self._project_subscriptions.get(project_id, set())

        message = {
            "type": "job_update",
            "job": {
                "job_id": job.id,
                "type": job.type.value,
                "project_id": job.project_id,
                "status": job.status.value,
                "progress": job.progress,
                "message": job.message,
                "result": job.result,
                "error": job.error,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            },
        }

        disconnected = []
        for client_id in subscribers:
            websocket = self._connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    async def send_to_client(self, client_id: str, message: dict) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: The client identifier.
            message: The message to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        websocket = self._connections.get(client_id)
        if not websocket:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            self.disconnect(client_id)
            return False

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def get_subscribed_projects(self, client_id: str) -> list[str]:
        """Get projects a client is subscribed to.

        Args:
            client_id: The client identifier.

        Returns:
            List of project IDs.
        """
        return [
            project_id
            for project_id, subscribers in self._project_subscriptions.items()
            if client_id in subscribers
        ]
