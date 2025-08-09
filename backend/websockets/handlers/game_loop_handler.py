# backend/websockets/handlers/game_loop_handler.py
import asyncio
import json
import logging
import time
from typing import Dict, Any, List

from fastapi import WebSocket

# --- Project-Specific Imports ---
from game_logic.game_manager import GameManager
from game_logic.entities.tower import Tower
from game_logic.entities.enemies.enemy import Enemy
from game_logic.entities.projectiles.projectile import Projectile
from game_logic.entities.projectiles.persistent_ground_aura import PersistentGroundAura
from game_logic.entities.projectiles.persistent_attached_aura import (
    PersistentAttachedAura,
)
from ..connection_manager import ConnectionManager


logger = logging.getLogger(__name__)

# --- Serialization Functions ---


def serialize_vector(vector) -> Dict[str, float]:
    """Serializes a pygame.Vector2 into a dictionary."""
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
    """Serializes a Tower object with enriched data for the UpgradePanel."""
    return {
        "id": str(tower.entity_id),
        "type_id": tower.tower_type_id,
        "name": tower.name,
        "pos": serialize_vector(tower.pos),
        "range": tower.range,
        "is_alive": tower.is_alive,
        "path_a_tier": tower.path_a_tier,
        "path_b_tier": tower.path_b_tier,
        "stats": {
            "damage": tower.damage,
            "fire_rate": tower.fire_rate,
            "blast_radius": tower.blast_radius,
            "pierce": tower.pierce_count,
        },
    }


def serialize_projectile(
    proj: Projectile | PersistentGroundAura | PersistentAttachedAura,
) -> Dict[str, Any]:
    """Serializes any projectile-like entity into a JSON-friendly dictionary."""
    return {
        "id": str(proj.entity_id),
        "pos": serialize_vector(proj.pos),
        "is_alive": proj.is_alive,
    }


def serialize_full_game_state(game_manager: GameManager) -> str:
    """Creates the master 'game_tick' JSON payload."""
    gm_state = game_manager.game_state
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
    return json.dumps(payload)


def serialize_initial_state(game_manager: GameManager) -> str:
    """Creates the 'initial_state' JSON payload, now including upgrade definitions."""
    grid = game_manager.grid
    tiles_data = []
    if grid:
        for y in range(grid.height):
            for x in range(grid.width):
                tile = grid.get_tile(x, y)
                if tile:
                    # FIX: Changed 'tile.key' to 'tile.tile_key' to match the Tile class attribute.
                    tiles_data.append({"x": tile.x, "y": tile.y, "key": tile.tile_key})

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
            "upgrade_definitions": game_manager.configs.get("upgrade_definitions", {}),
        },
    }
    return json.dumps(payload)


# --- Game Loop Handler ---
async def game_loop(
    websocket: WebSocket,
    game_manager: GameManager,
    client_id: str,
    manager: ConnectionManager,
):
    """The main loop for a single game instance."""
    logger.info(f"Sending initial state to client {client_id}...")
    initial_state_json = serialize_initial_state(game_manager)
    await manager.send_personal_message(initial_state_json, client_id)
    logger.info("Initial state sent.")

    last_time = time.perf_counter()
    while not game_manager.game_state.game_over and not game_manager.game_state.victory:
        current_time = time.perf_counter()
        dt = current_time - last_time
        last_time = current_time

        game_manager.update(dt)
        state_json = serialize_full_game_state(game_manager)
        await manager.send_personal_message(state_json, client_id)
        await asyncio.sleep(1 / 60)

    logger.info(f"Game over for client {client_id}. Loop terminated.")
    # TODO: Send a final 'game_over' message with stats.
