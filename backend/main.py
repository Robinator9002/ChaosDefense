# backend/main.py
import asyncio
import logging
import sys
from pathlib import Path
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# --- Path Setup ---
# This ensures the backend can find the 'game_logic' module.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# --- Local Module Imports ---
# Imports from our new, structured backend directory.
from backend.core.config import load_all_game_configs
from backend.websockets.connection_manager import ConnectionManager
from backend.websockets.handlers.game_loop_handler import game_loop
from backend.websockets.handlers.command_parser import handle_message

# --- Game Logic Imports ---
# Imports from your existing, core game logic.
from game_logic.game_manager import GameManager
from game_logic.progression.player_data_manager import PlayerDataManager
from game_logic.progression.progression_manager import ProgressionManager

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- FastAPI Application Initialization ---
app = FastAPI()
manager = ConnectionManager()
ALL_CONFIGS = load_all_game_configs()


async def read_messages_loop(websocket: WebSocket, game_manager: GameManager):
    """
    Listens for incoming commands from the client and passes them to the parser.
    """
    try:
        while True:
            raw_data = await websocket.receive_text()
            # The handle_message function from our parser module does all the work.
            await handle_message(game_manager, raw_data)
    except WebSocketDisconnect:
        logger.info("Client disconnected. Read loop terminated.")
    except Exception as e:
        logger.error(f"Error in read_messages_loop: {e}", exc_info=True)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    The main entry point for a client connecting to the game server.
    It orchestrates the setup and teardown of a full game session.
    """
    await manager.connect(websocket, client_id)
    game_task = None
    read_task = None

    try:
        # --- Initialize Game Instance for this Session ---
        logger.info(f"Initializing game instance for client: {client_id}")
        saves_path = PROJECT_ROOT / "configs" / "saves"
        player_data_manager = PlayerDataManager(
            save_path=saves_path / "player_data.json",
            game_settings=ALL_CONFIGS["game_settings"],
        )
        progression_manager = ProgressionManager(
            player_data_manager=player_data_manager,
            all_tower_configs=ALL_CONFIGS["tower_types"],
            global_upgrades_config=ALL_CONFIGS["global_upgrades"],
        )
        # TODO: The level_id will be sent by the client. Hardcoded for now.
        game_manager = GameManager(
            all_configs=ALL_CONFIGS,
            progression_manager=progression_manager,
            level_id="Forest",
        )

        # --- Create and run concurrent tasks for game loop and message reading ---
        game_task = asyncio.create_task(
            game_loop(websocket, game_manager, client_id, manager)
        )
        read_task = asyncio.create_task(read_messages_loop(websocket, game_manager))

        # Wait for either task to complete (e.g., game over or disconnect).
        done, pending = await asyncio.wait(
            [game_task, read_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Clean up any pending tasks to prevent them from running forever.
        for task in pending:
            task.cancel()

    except Exception as e:
        logger.critical(
            f"An unhandled error occurred in the main WebSocket endpoint for {client_id}: {e}",
            exc_info=True,
        )
    finally:
        # --- Final Cleanup ---
        # Ensure the client is disconnected and all tasks are cancelled.
        if game_task and not game_task.done():
            game_task.cancel()
        if read_task and not read_task.done():
            read_task.cancel()
        manager.disconnect(client_id)
        logger.info(f"Session cleaned up for client {client_id}")
