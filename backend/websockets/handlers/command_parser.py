# backend/command_parser.py
import json
import logging
import uuid
from typing import Dict, Any, Callable

from game_logic.game_manager import GameManager

logger = logging.getLogger(__name__)

# --- Command Handler Functions ---
# Each function here corresponds to a specific "action" that the client can send.
# They are responsible for validating the payload and calling the correct
# method on the GameManager instance.


def handle_place_tower(gm: GameManager, payload: Dict[str, Any]):
    """Handles the 'place_tower' command from the client."""
    try:
        tower_type_id = payload["tower_type_id"]
        tile_x = int(payload["tile_x"])
        tile_y = int(payload["tile_y"])
        logger.info(
            f"Attempting to place tower '{tower_type_id}' at ({tile_x}, {tile_y})"
        )
        gm.place_tower(tower_type_id, tile_x, tile_y)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Invalid 'place_tower' payload: {payload}. Error: {e}")


def handle_upgrade_tower(gm: GameManager, payload: Dict[str, Any]):
    """Handles the 'upgrade_tower' command from the client."""
    try:
        # The client sends UUIDs as strings, so we must convert them back.
        tower_id = uuid.UUID(payload["tower_id"])
        upgrade_id = payload["upgrade_id"]
        logger.info(f"Attempting to apply upgrade '{upgrade_id}' to tower {tower_id}")
        gm.purchase_tower_upgrade(tower_id, upgrade_id)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Invalid 'upgrade_tower' payload: {payload}. Error: {e}")


def handle_salvage_tower(gm: GameManager, payload: Dict[str, Any]):
    """Handles the 'salvage_tower' command from the client."""
    try:
        tower_id = uuid.UUID(payload["tower_id"])
        logger.info(f"Attempting to salvage tower {tower_id}")
        gm.salvage_tower(tower_id)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Invalid 'salvage_tower' payload: {payload}. Error: {e}")


def handle_set_tower_persona(gm: GameManager, payload: Dict[str, Any]):
    """Handles the 'set_tower_persona' command from the client."""
    try:
        tower_id = uuid.UUID(payload["tower_id"])
        new_persona_id = payload["new_persona_id"]
        logger.info(
            f"Attempting to set persona for tower {tower_id} to '{new_persona_id}'"
        )
        gm.change_tower_persona(tower_id, new_persona_id)
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Invalid 'set_tower_persona' payload: {payload}. Error: {e}")


# --- Action to Handler Mapping ---
# This dictionary is a clean way to map the "action" string from the client's
# JSON message to the appropriate handler function defined above.
ACTION_HANDLERS: Dict[str, Callable[[GameManager, Dict[str, Any]], None]] = {
    "place_tower": handle_place_tower,
    "upgrade_tower": handle_upgrade_tower,
    "salvage_tower": handle_salvage_tower,
    "set_tower_persona": handle_set_tower_persona,
    # TODO: Add handlers for 'start_next_wave', 'pause_game', etc.
}


# --- Main Parsing Function ---
async def handle_message(game_manager: GameManager, raw_data: str):
    """
    Parses a raw message from a WebSocket, determines the requested action,
    and calls the corresponding handler.

    Args:
        game_manager (GameManager): The active game instance for this client.
        raw_data (str): The raw JSON string received from the client.
    """
    try:
        message = json.loads(raw_data)
        action = message.get("action")
        payload = message.get("payload", {})

        if not action:
            logger.warning(f"Received message with no action: {message}")
            return

        handler = ACTION_HANDLERS.get(action)
        if handler:
            # Call the appropriate handler function (e.g., handle_place_tower)
            handler(game_manager, payload)
        else:
            logger.warning(f"No handler found for action: '{action}'")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from message: {raw_data}")
    except Exception as e:
        logger.critical(
            f"An unexpected error occurred in command handling: {e}", exc_info=True
        )
