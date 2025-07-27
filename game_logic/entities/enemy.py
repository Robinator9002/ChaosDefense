# game_logic/entities/enemy.py
import pygame
import math
import logging
from typing import List, Tuple, TYPE_CHECKING

from .entity import Entity

# This prevents circular imports, which can happen if other systems need GameState.
if TYPE_CHECKING:
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Represents an enemy unit that moves along a path.

    Inherits from Entity and adds movement logic, pathfinding, and stat
    calculation based on its type, its level, and the global game difficulty.
    """

    def __init__(
        self,
        enemy_type_data: dict,
        level: int,
        path: List[Tuple[int, int]],
        tile_size: int,
        difficulty_modifier: float,
    ):
        """
        Initializes a new Enemy.

        Args:
            enemy_type_data (dict): The data dictionary for this enemy type from enemy_types.json.
            level (int): The level of this specific enemy, used for stat scaling.
            path (List[Tuple[int, int]]): The path of tile coordinates for the enemy to follow.
            tile_size (int): The size of a single tile in pixels.
            difficulty_modifier (float): The global difficulty multiplier from game_settings.json.
        """
        # --- Stat Calculation ---
        base_stats = enemy_type_data.get("base_stats", {})
        scaling = enemy_type_data.get("scaling_per_level", {})
        render_props = enemy_type_data.get("render_props", {})

        # Calculate stats based on level. Formula: base * (multiplier^(level-1))
        # Then, apply the global player difficulty modifier to HP and damage.
        self.level = level
        level_scaled_hp = base_stats.get("hp", 1) * (
            scaling.get("hp", 1.0) ** (level - 1)
        )
        calculated_hp = int(level_scaled_hp * difficulty_modifier)

        self.speed = base_stats.get("speed", 50) * (
            scaling.get("speed", 1.0) ** (level - 1)
        )
        self.bounty = int(
            base_stats.get("bounty", 0) * (scaling.get("bounty", 1.0) ** (level - 1))
        )

        level_scaled_damage = base_stats.get("damage", 1)
        self.damage = int(level_scaled_damage * difficulty_modifier)

        # --- Path and Position Setup ---
        self.path = path
        self.tile_size = tile_size
        # Convert tile-based path to pixel-based path for smooth movement.
        self.pixel_path = [
            pygame.Vector2(x * tile_size + tile_size / 2, y * tile_size + tile_size / 2)
            for x, y in path
        ]

        initial_pos = self.pixel_path[0] if self.pixel_path else pygame.Vector2(0, 0)

        # --- Create Placeholder Sprite from render_props ---
        size = render_props.get("size", 24)
        color = render_props.get("color", (255, 0, 255))
        placeholder_sprite = pygame.Surface((size, size))
        placeholder_sprite.fill(color)

        # Call the parent Entity's constructor with all calculated values.
        super().__init__(
            initial_pos.x, initial_pos.y, calculated_hp, placeholder_sprite
        )

        self.current_waypoint_index = 1  # Start moving towards the second waypoint.

        logger.info(
            f"Created Level {self.level} {enemy_type_data.get('name', 'Unknown')} with {self.max_hp} HP."
        )

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates the enemy's position by moving it along the path.

        Args:
            dt (float): The time elapsed since the last frame, in seconds.
            game_state (GameState): The current state of the game.
        """
        if not self.is_alive or self.current_waypoint_index >= len(self.pixel_path):
            return

        target_pos = self.pixel_path[self.current_waypoint_index]
        direction = target_pos - self.pos

        distance_to_target = direction.length()

        # If we are very close to the target, snap to it and move to the next waypoint.
        # This prevents overshooting and floating point inaccuracies.
        if distance_to_target < self.speed * dt:
            self.pos = target_pos
            self.current_waypoint_index += 1

            # Check if the enemy has reached the end of the path
            if self.current_waypoint_index >= len(self.pixel_path):
                self._on_reach_end(game_state)
                return
        else:
            # Move towards the target at a constant speed.
            self.pos += direction.normalize() * self.speed * dt

        # Ensure the entity's rect is updated for drawing.
        super().update(dt, game_state)

    def _on_reach_end(self, game_state: "GameState"):
        """
        Handles the logic for when the enemy reaches the end of its path.
        It damages the player's base and then "despawns" itself.
        """
        logger.warning(
            f"Enemy {self.entity_id} reached the end. Dealing {self.damage} damage."
        )
        game_state.base_hp -= self.damage

        # Check for game over condition
        if game_state.base_hp <= 0:
            game_state.end_game()

        self.kill()  # The enemy is removed from the game
