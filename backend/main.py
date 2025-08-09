# backend/main.py
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

# --- Path Setup ---
# This is a crucial step to ensure that the backend application can find and
# import modules from the 'game_logic' directory. We add the project's root
# directory to Python's system path.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# --- Project-Specific Imports ---
# Now that the path is set up, we can import the core components from your game logic.
# We are effectively treating the 'game_logic' directory as a library.
# Note: We remove pygame imports as the backend is headless.
from game_logic.game_manager import GameManager
from game_logic.progression.player_data_manager import PlayerDataManager
from game_logic.progression.progression_manager import ProgressionManager
from game_logic.upgrades.upgrade_loader import load_all_upgrades

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Configuration Loading ---
# This utility function and the subsequent loading logic are adapted from your
# original main.py to ensure the backend starts with the same configuration data.
def load_config(path: Path) -> dict:
    """Loads a single JSON configuration file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config file at {path}: {e}")
        raise


def load_all_game_configs() -> Dict[str, Any]:
    """Loads all necessary game configurations from the disk."""
    logger.info("--- Loading All Game Configurations for Backend ---")
    config_path = PROJECT_ROOT / "configs"
    tower_upgrade_dir = config_path / "upgrades" / "towers"

    all_configs = {
        "game_settings": load_config(config_path / "gameplay/game_settings.json"),
        "level_styles": load_config(config_path / "levels/level_styles.json"),
        "enemy_types": load_config(config_path / "entities/enemies/enemy_types.json"),
        "boss_types": load_config(config_path / "entities/enemies/boss_types.json"),
        "buffer_types": load_config(config_path / "entities/enemies/buffer_types.json"),
        "tower_types": load_config(config_path / "entities/tower_types.json"),
        "targeting_ai": load_config(config_path / "targeting/targeting_ai.json"),
        "formations": load_config(config_path / "ai/formations.json"),
        "upgrade_definitions": load_all_upgrades([tower_upgrade_dir]),
        "difficulty_scaling": load_config(
            config_path / "scaling/difficulty_scaling.json"
        ),
        "wave_scaling": load_config(config_path / "scaling/wave_scaling.json"),
        "status_effects": load_config(config_path / "gameplay/status_effects.json"),
        "global_upgrades": load_config(config_path / "upgrades/global_upgrades.json"),
    }
    logger.info("--- All configurations loaded successfully. ---")
    return all_configs


# --- WebSocket Connection Management ---
class ConnectionManager:
    """
    Manages active WebSocket connections. This simple class allows us to keep
    track of connected clients, although for this game, we'll typically have
    only one client per game instance.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accepts a new WebSocket connection and stores it."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"New connection accepted: {client_id}")

    def disconnect(self, client_id: str):
        """Removes a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Connection closed: {client_id}")

    async def send_personal_message(self, message: str, client_id: str):
        """Sends a message to a specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)


# --- FastAPI Application Setup ---
app = FastAPI()
manager = ConnectionManager()
ALL_CONFIGS = load_all_game_configs()


# --- WebSocket Endpoint ---
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    This is the main entry point for a client connecting to the game server.
    It establishes a WebSocket connection and manages the lifecycle of a
    single game session.
    """
    await manager.connect(websocket, client_id)

    try:
        # --- Initialize Game Instance ---
        # For each new connection, we create a fresh, independent instance of the game.
        logger.info(f"Initializing game instance for client: {client_id}")

        # Initialize progression systems (same as in your original main.py)
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

        # Instantiate the core game engine.
        # TODO: The level_id will eventually be sent by the client from the menu.
        # For now, we hardcode it to start a specific level for testing.
        game_manager = GameManager(
            all_configs=ALL_CONFIGS,
            progression_manager=progression_manager,
            level_id="Forest",  # Hardcoded for now
        )

        # --- Concurrently Run Game Logic and Listen for Client Commands ---
        # We use asyncio.gather to run two coroutines at the same time:
        # 1. game_loop: Runs the game simulation and sends state updates to the client.
        # 2. read_messages: Listens for incoming commands from the client.
        # These will be fleshed out in the next steps of our plan.

        # Placeholder for the game loop logic (to be moved to game_loop_handler.py)
        async def game_loop(ws: WebSocket, gm: GameManager):
            while True:
                # In the next step, this will call gm.update() and send serialized state.
                await asyncio.sleep(1 / 60)  # ~60 FPS

        # Placeholder for the command reading logic (to be moved to command_parser.py)
        async def read_messages(ws: WebSocket, gm: GameManager):
            while True:
                data = await ws.receive_text()
                # In the next step, this will parse the data and call gm methods.
                logger.info(f"Received command: {data}")

        await asyncio.gather(
            game_loop(websocket, game_manager), read_messages(websocket, game_manager)
        )

    except WebSocketDisconnect:
        logger.warning(f"Client {client_id} disconnected unexpectedly.")
    finally:
        # --- Cleanup ---
        # Ensures that the client is properly disconnected from the manager
        # when the game session ends, for any reason.
        manager.disconnect(client_id)
