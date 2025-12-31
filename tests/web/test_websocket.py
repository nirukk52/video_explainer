"""Tests for WebSocket manager."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.web.backend.websocket.manager import WebSocketManager
from src.web.backend.services.job_manager import Job, JobStatus, JobType


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestWebSocketManager:
    """Tests for WebSocketManager."""

    @pytest.mark.asyncio
    async def test_connect(self, ws_manager: WebSocketManager, mock_websocket):
        """Test connecting a client."""
        await ws_manager.connect(mock_websocket, "client-1")
        assert ws_manager.connection_count == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, ws_manager: WebSocketManager, mock_websocket):
        """Test disconnecting a client."""
        await ws_manager.connect(mock_websocket, "client-1")
        ws_manager.disconnect("client-1")
        assert ws_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_subscribe_to_project(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        """Test subscribing to a project."""
        await ws_manager.connect(mock_websocket, "client-1")
        await ws_manager.subscribe_to_project("client-1", "project-1")

        projects = ws_manager.get_subscribed_projects("client-1")
        assert "project-1" in projects

    @pytest.mark.asyncio
    async def test_unsubscribe_from_project(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        """Test unsubscribing from a project."""
        await ws_manager.connect(mock_websocket, "client-1")
        await ws_manager.subscribe_to_project("client-1", "project-1")
        await ws_manager.unsubscribe_from_project("client-1", "project-1")

        projects = ws_manager.get_subscribed_projects("client-1")
        assert "project-1" not in projects

    @pytest.mark.asyncio
    async def test_broadcast_job_update(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        """Test broadcasting job updates to subscribed clients."""
        await ws_manager.connect(mock_websocket, "client-1")
        await ws_manager.subscribe_to_project("client-1", "project-1")

        job = Job(
            id="job-1",
            type=JobType.VOICEOVER,
            project_id="project-1",
            status=JobStatus.RUNNING,
            progress=0.5,
            message="Processing...",
        )

        await ws_manager.broadcast_job_update(job)

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "job_update"
        assert call_args["job"]["job_id"] == "job-1"
        assert call_args["job"]["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_broadcast_only_to_subscribers(
        self, ws_manager: WebSocketManager
    ):
        """Test that broadcasts only go to subscribed clients."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await ws_manager.connect(ws1, "client-1")
        await ws_manager.connect(ws2, "client-2")
        await ws_manager.subscribe_to_project("client-1", "project-1")
        # client-2 is not subscribed to project-1

        job = Job(
            id="job-1",
            type=JobType.VOICEOVER,
            project_id="project-1",
            status=JobStatus.COMPLETED,
        )

        await ws_manager.broadcast_job_update(job)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_client(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        """Test sending a message to a specific client."""
        await ws_manager.connect(mock_websocket, "client-1")

        result = await ws_manager.send_to_client(
            "client-1", {"type": "test", "data": "hello"}
        )

        assert result is True
        mock_websocket.send_json.assert_called_once_with(
            {"type": "test", "data": "hello"}
        )

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(
        self, ws_manager: WebSocketManager
    ):
        """Test sending to a non-existent client."""
        result = await ws_manager.send_to_client(
            "nonexistent", {"type": "test"}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_removes_subscriptions(
        self, ws_manager: WebSocketManager, mock_websocket
    ):
        """Test that disconnect removes all subscriptions."""
        await ws_manager.connect(mock_websocket, "client-1")
        await ws_manager.subscribe_to_project("client-1", "project-1")
        await ws_manager.subscribe_to_project("client-1", "project-2")

        ws_manager.disconnect("client-1")

        projects = ws_manager.get_subscribed_projects("client-1")
        assert projects == []

    @pytest.mark.asyncio
    async def test_handle_send_error(
        self, ws_manager: WebSocketManager
    ):
        """Test handling errors when sending messages."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await ws_manager.connect(mock_ws, "client-1")
        await ws_manager.subscribe_to_project("client-1", "project-1")

        job = Job(
            id="job-1",
            type=JobType.VOICEOVER,
            project_id="project-1",
            status=JobStatus.COMPLETED,
        )

        # Should not raise, should disconnect client
        await ws_manager.broadcast_job_update(job)

        # Client should be disconnected
        assert ws_manager.connection_count == 0
