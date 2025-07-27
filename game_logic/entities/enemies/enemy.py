# game_logic/entities/enemy.py
import pygame
import logging
from typing import List, Tuple, TYPE_CHECKING, Dict, Any

from ..entity import Entity

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.effects.status_effect import StatusEffect

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Represents an enemy unit that moves along a path and can be affected
    by status effects.
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
        """
        # --- Stat Calculation ---
        base_stats = enemy_type_data.get("base_stats", {})
        scaling = enemy_type_data.get("scaling_per_level", {})
        render_props = enemy_type_data.get("render_props", {})

        self.level = level
        level_scaled_hp = base_stats.get("hp", 1) * (
            scaling.get("hp", 1.0) ** (level - 1)
        )
        calculated_hp = int(level_scaled_hp * difficulty_modifier)

        # Store the base speed separately so effects can modify the current speed.
        self.base_speed = base_stats.get("speed", 50) * (
            scaling.get("speed", 1.0) ** (level - 1)
        )
        self.speed = self.base_speed  # Current speed starts at base speed.

        self.bounty = int(
            base_stats.get("bounty", 0) * (scaling.get("bounty", 1.0) ** (level - 1))
        )
        self.damage = int(base_stats.get("damage", 1) * difficulty_modifier)

        # --- Path and Position Setup ---
        self.path = path
        self.tile_size = tile_size
        self.pixel_path = [
            pygame.Vector2(x * tile_size + tile_size / 2, y * tile_size + tile_size / 2)
            for x, y in path
        ]
        initial_pos = self.pixel_path[0] if self.pixel_path else pygame.Vector2(0, 0)

        # --- Status Effects ---
        self.status_effects: List["StatusEffect"] = []

        # --- Create Placeholder Sprite ---
        size = render_props.get("size", 24)
        color = render_props.get("color", (255, 0, 255))
        placeholder_sprite = pygame.Surface((size, size))
        placeholder_sprite.fill(color)

        super().__init__(
            initial_pos.x, initial_pos.y, calculated_hp, placeholder_sprite
        )
        self.current_waypoint_index = 1

        logger.info(
            f"Created Level {self.level} {enemy_type_data.get('name', 'Unknown')} with {self.max_hp} HP."
        )

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the enemy, handling stacking logic.
        """
        # Check if an effect of the same type is already active.
        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                if existing_effect.stacking_logic == "refresh":
                    existing_effect.refresh(
                        new_effect.duration_remaining,
                        new_effect.params.get("multiplier", 1.0),
                    )
                    return  # Effect refreshed, no need to add a new one.

        # If no existing effect was refreshed, add the new one.
        self.status_effects.append(new_effect)

    def _update_status_effects(self, dt: float):
        """Updates all active status effects and removes expired ones."""
        if not self.status_effects:
            return

        # Update durations
        for effect in self.status_effects:
            effect.update(dt)

        # Filter out expired effects
        self.status_effects = [e for e in self.status_effects if e.is_active]

    def _apply_stat_modifiers(self):
        """Calculates final stats based on active status effects."""
        # Reset to base stats first
        self.speed = self.base_speed

        # Apply modifiers from effects
        for effect in self.status_effects:
            if (
                effect.effect_type == "stat_modifier"
                and effect.stat_to_modify == "speed"
            ):
                self.speed *= effect.params.get("multiplier", 1.0)

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates the enemy's logic, including effects, and then moves it.
        """
        if not self.is_alive:
            return

        # --- 1. Update and apply status effects ---
        self._update_status_effects(dt)
        self._apply_stat_modifiers()

        # --- 2. Movement Logic ---
        if self.current_waypoint_index >= len(self.pixel_path):
            return

        target_pos = self.pixel_path[self.current_waypoint_index]
        direction = target_pos - self.pos

        # Use the (potentially modified) self.speed for movement
        distance_to_target = direction.length()
        if distance_to_target < self.speed * dt:
            self.pos = target_pos
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.pixel_path):
                self._on_reach_end(game_state)
                return
        else:
            self.pos += direction.normalize() * self.speed * dt

        super().update(dt, game_state)

    def _on_reach_end(self, game_state: "GameState"):
        """Handles logic for when the enemy reaches the end of its path."""
        logger.warning(
            f"Enemy {self.entity_id} reached the end. Dealing {self.damage} damage."
        )
        game_state.base_hp -= self.damage
        if game_state.base_hp <= 0:
            game_state.end_game()
        self.kill()
