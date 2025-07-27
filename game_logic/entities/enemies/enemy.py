# game_logic/entities/enemies/enemy.py
import pygame
import logging
from typing import List, Tuple, TYPE_CHECKING, Dict, Any

# Note: The import path for Entity is now relative to the new subfolder.
from ..entity import Entity

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from ...game_state import GameState
    from ...effects.status_effect import StatusEffect

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Represents an enemy unit that moves along a path.

    This class has been reworked to include armor and damage multiplier stats,
    making it compatible with more advanced tower upgrades like armor shred
    and vulnerability effects.
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

        self.base_speed = base_stats.get("speed", 50) * (
            scaling.get("speed", 1.0) ** (level - 1)
        )
        self.speed = self.base_speed

        self.bounty = int(
            base_stats.get("bounty", 0) * (scaling.get("bounty", 1.0) ** (level - 1))
        )
        self.damage = int(base_stats.get("damage", 1) * difficulty_modifier)

        # --- NEW: Add armor and damage multiplier stats ---
        # These are the foundation for new upgrade effects.
        self.base_armor = base_stats.get("armor", 0)
        self.armor = self.base_armor
        self.damage_taken_multiplier = 1.0

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

        logger.debug(
            f"Created Level {self.level} {enemy_type_data.get('name', 'Unknown')} with {self.max_hp} HP and {self.armor} Armor."
        )

    def take_damage(self, amount: int, armor_shred: int = 0):
        """
        Reduces the entity's current HP by a given amount.
        This method is now updated to factor in armor, armor shred from the
        projectile, and any active damage multipliers from status effects.
        """
        if not self.is_alive:
            return

        # 1. Calculate effective armor for this specific hit.
        effective_armor = max(0, self.armor - armor_shred)

        # 2. Reduce incoming damage by armor. Damage cannot be less than 1.
        damage_after_armor = max(1, amount - effective_armor)

        # 3. Apply vulnerability/resistance multipliers from status effects.
        final_damage = int(damage_after_armor * self.damage_taken_multiplier)

        self.current_hp -= final_damage
        if self.current_hp <= 0:
            self.current_hp = 0
            self.kill()

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the enemy, handling stacking logic.
        """
        # Check if an effect of the same type is already active to handle stacking.
        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                # 'refresh' logic: reset duration and take the stronger potency.
                if existing_effect.stacking_logic == "refresh":
                    existing_effect.refresh(
                        new_effect.duration_remaining,
                        new_effect.params.get("multiplier", 1.0),
                    )
                    return  # Effect was refreshed, so we are done.

        # If no existing effect was handled, add the new one to the list.
        self.status_effects.append(new_effect)

    def _update_status_effects(self, dt: float):
        """Updates all active status effects and removes expired ones."""
        if not self.status_effects:
            return

        # Tick down the duration of all active effects.
        for effect in self.status_effects:
            effect.update(dt)

        # Create a new list containing only the effects that are still active.
        self.status_effects = [e for e in self.status_effects if e.is_active]

    def _apply_stat_modifiers(self):
        """
        Calculates final stats for this frame based on active status effects.
        This must be called every frame before the stats are used.
        """
        # Reset modifiers to their base values each frame.
        self.speed = self.base_speed
        self.damage_taken_multiplier = 1.0

        # Apply modifiers from all active effects.
        for effect in self.status_effects:
            if effect.effect_type == "stat_modifier":
                stat = effect.stat_to_modify
                multiplier = effect.params.get("multiplier", 1.0)

                if stat == "speed":
                    self.speed *= multiplier
                elif stat == "damage_taken_multiplier":
                    # This allows effects like "Vulnerability" to work.
                    self.damage_taken_multiplier *= multiplier

    def update(self, dt: float, game_state: "GameState"):
        """
        The main update loop for the enemy entity.
        """
        if not self.is_alive:
            return

        # 1. Update status effects and apply their stat modifications.
        self._update_status_effects(dt)
        self._apply_stat_modifiers()

        # 2. Handle movement along the path.
        if self.current_waypoint_index >= len(self.pixel_path):
            return  # Enemy has reached the end but hasn't been processed yet.

        target_pos = self.pixel_path[self.current_waypoint_index]
        direction = target_pos - self.pos
        distance_to_target = direction.length()

        # Move towards the target, ensuring we don't overshoot it.
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
