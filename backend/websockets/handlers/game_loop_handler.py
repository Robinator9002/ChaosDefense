# backend/game_loop_handler.py
import asyncio
import json
import logging
import time
from typing import Dict, Any, List

from fastapi import WebSocket

# --- Project-Specific Imports ---
# These imports are necessary to access the game's core classes and data structures.
# We need to know the 'shape' of these objects to serialize them correctly.
from game_logic.game_manager import GameManager
from game_logic.entities.tower import Tower
from game_logic.entities.enemies.enemy import Enemy
from game_logic.entities.projectiles.projectile import Projectile
from game_logic.entities.projectiles.persistent_ground_aura import PersistentGroundAura
from game_logic.entities.projectiles.persistent_attached_aura import (
    PersistentAttachedAura,
)

logger = logging.getLogger(__name__)

# --- Serialization Functions ---
# These functions are the core of the "translation" process. They take complex
# Python objects from your game and turn them into simple dictionaries that can
# be easily converted to JSON.


def serialize_vector(vector) -> Dict[str, float]:
    """Serializes a pygame.Vector2 into a dictionary."""
    # Pygame is not imported here, so we access x and y attributes directly.
    # This works because your game logic uses Vector2-like objects.
    return {"x": vector.x, "y": vector.y}


def serialize_enemy(enemy: Enemy) -> Dict[str, Any]:
    """Serializes an Enemy object into a JSON-friendly dictionary."""
    return {
        "id": str(enemy.entity_id),
        "type_id": enemy.enemy_type_id,
        "pos": serialize_vector(enemy.pos),
        "hp": enemy.current_hp,
        "max_hp": enemy.max_hp,
        "is_alive": enemy.is_alive,
    }


def serialize_tower(tower: Tower) -> Dict[str, Any]:
    """Serializes a Tower object into a JSON-friendly dictionary."""
    return {
        "id": str(tower.entity_id),
        "type_id": tower.tower_type_id,
        "pos": serialize_vector(tower.pos),
        "range": tower.range,  # For drawing range indicators on the frontend
        "is_alive": tower.is_alive,
    }


def serialize_projectile(
    proj: Projectile | PersistentGroundAura | PersistentAttachedAura,
) -> Dict[str, Any]:
    """Serializes any projectile-like entity into a JSON-friendly dictionary."""
    # This simple serialization works for most visual needs.
    # We can add more specific fields if the frontend requires them.
    return {
        "id": str(proj.entity_id),
        "pos": serialize_vector(proj.pos),
        "is_alive": proj.is_alive,
    }


def serialize_full_game_state(game_manager: GameManager) -> str:
    """
    Creates the master 'game_tick' JSON payload by serializing all relevant
    parts of the current game state.
    """
    gm_state = game_manager.game_state

    # The main payload structure, as defined in our API contract.
    payload = {
        "type": "game_tick",
        "data": {
            "game_state": {
                "gold": gm_state.gold,
                "base_hp": gm_state.base_hp,
                "wave": gm_state.current_wave_number,
                "game_over": gm_state.game_over,
                "victory": gm_state.victory,
            },
            "entities": {
                "towers": [serialize_tower(t) for t in game_manager.towers.values()],
                "enemies": [serialize_enemy(e) for e in game_manager.enemies.values()],
                "projectiles": [
                    serialize_projectile(p) for p in game_manager.projectiles.values()
                ],
            },
        },
    }
    # json.dumps converts the Python dictionary into a JSON string.
    return json.dumps(payload)


def serialize_initial_state(game_manager: GameManager) -> str:
    """
    Creates the 'initial_state' JSON payload sent once at the beginning
    of a game session.
    """
    grid = game_manager.grid

    # Extract tile data into a simple list of dictionaries
    tiles_data = []
    if grid:
        for y in range(grid.height):
            for x in range(grid.width):
                tile = grid.get_tile(x, y)
                if tile:
                    tiles_data.append({"x": tile.x, "y": tile.y, "key": tile.tile_key})

    # Get buildable tower info (ID, name, cost) for the UI
    buildable_towers_info = []
    buildable_ids = game_manager.get_buildable_towers()
    all_tower_configs = game_manager.configs.get("tower_types", {})
    for tower_id in buildable_ids:
        config = all_tower_configs.get(tower_id, {})
        if isinstance(config, dict):
            buildable_towers_info.append(
                {
                    "id": tower_id,
                    "name": config.get("name", "Unknown"),
                    "cost": config.get("cost", 9999),
                }
            )

    payload = {
        "type": "initial_state",
        "data": {
            "grid": {
                "width": grid.width if grid else 0,
                "height": grid.height if grid else 0,
                "tiles": tiles_data,
            },
            "paths": game_manager.paths,
            "buildable_towers": buildable_towers_info,
        },
    }
    return json.dumps(payload)


# --- Game Loop Handler ---
async def game_loop(
    websocket: WebSocket, game_manager: GameManager, client_id: str, manager
):
    """
    The main loop for a single game instance. It runs the simulation,
    serializes the state, and sends it to the client.

    Args:
        websocket (WebSocket): The client's WebSocket connection.
        game_manager (GameManager): The instance of the game engine for this session.
        client_id (str): The unique ID of the connected client.
        manager: The ConnectionManager instance to send messages through.
    """
    # Send the initial state payload once.
    logger.info(f"Sending initial state to client {client_id}...")
    initial_state_json = serialize_initial_state(game_manager)
    await manager.send_personal_message(initial_state_json, client_id)
    logger.info("Initial state sent.")

    last_time = time.perf_counter()
    while not game_manager.game_state.game_over and not game_manager.game_state.victory:
        # Calculate delta time (dt) for smooth, frame-rate independent physics.
        current_time = time.perf_counter()
        dt = current_time - last_time
        last_time = current_time

        # 1. Update the game simulation by one step.
        game_manager.update(dt)

        # 2. Serialize the entire new game state into a JSON string.
        state_json = serialize_full_game_state(game_manager)

        # 3. Send the new state to the client.
        await manager.send_personal_message(state_json, client_id)

        # 4. Sleep to maintain a consistent update rate (~60 ticks per second).
        await asyncio.sleep(1 / 60)

    logger.info(f"Game over for client {client_id}. Loop terminated.")
    # TODO: Send a final 'game_over' message with stats.
