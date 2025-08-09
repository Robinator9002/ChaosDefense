# backend/websockets/connection_manager.py
import logging
from typing import Dict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections. This class encapsulates all logic for
    tracking, adding, and removing client connections, allowing the main server
    logic to remain clean.
    """

    def __init__(self):
        """Initializes the ConnectionManager with a dictionary to hold connections."""
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accepts a new WebSocket connection and adds it to the active pool.

        Args:
            websocket (WebSocket): The WebSocket object from FastAPI.
            client_id (str): The unique identifier for the connecting client.
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"New connection accepted from client_id: {client_id}")

    def disconnect(self, client_id: str):
        """
        Removes a WebSocket connection from the active pool.

        Args:
            client_id (str): The unique identifier of the client to disconnect.
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Connection closed for client_id: {client_id}")

    async def send_personal_message(self, message: str, client_id: str):
        """
        Sends a message to a specific, single client.

        It checks if the client is still connected before attempting to send,
        preventing errors if a client disconnects unexpectedly.

        Args:
            message (str): The message (as a string) to send.
            client_id (str): The identifier of the target client.
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            # Ensure the websocket is still in a valid, connected state.
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
            else:
                logger.warning(
                    f"Attempted to send message to disconnected client: {client_id}"
                )
