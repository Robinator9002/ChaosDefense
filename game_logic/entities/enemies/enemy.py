# game_logic/entities/enemies/enemy.py
import pygame
import logging
from typing import List, Tuple, TYPE_CHECKING, Dict, Any

from ..entity import Entity

if TYPE_CHECKING:
    from ...game_state import GameState
    from ...effects.status_effect import StatusEffect

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Represents an enemy unit that moves along a path.
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
        self.base_armor = base_stats.get("armor", 0)
        self.armor = self.base_armor
        self.damage_taken_multiplier = 1.0

        self.bounty = int(
            base_stats.get("bounty", 0) * (scaling.get("bounty", 1.0) ** (level - 1))
        )
        self.damage_to_base = int(base_stats.get("damage", 1) * difficulty_modifier)

        self.path = path
        self.tile_size = tile_size
        self.pixel_path = [
            pygame.Vector2(x * tile_size + tile_size / 2, y * tile_size + tile_size / 2)
            for x, y in path
        ]
        initial_pos = self.pixel_path[0] if self.pixel_path else pygame.Vector2(0, 0)

        self.status_effects: List["StatusEffect"] = []

        size = render_props.get("size", 24)
        color = render_props.get("color", (255, 0, 255))
        placeholder_sprite = pygame.Surface((size, size))
        placeholder_sprite.fill(color)

        super().__init__(
            initial_pos.x, initial_pos.y, calculated_hp, placeholder_sprite
        )
        self.current_waypoint_index = 1

    def has_status_effect(self, effect_id: str) -> bool:
        """Checks if the enemy currently has an active status effect of a given type."""
        return any(effect.effect_id == effect_id for effect in self.status_effects)

    def take_damage(
        self, amount: int, armor_shred: int = 0, ignores_armor: bool = False
    ):
        """
        Reduces the entity's current HP by a given amount.
        """
        if not self.is_alive:
            return

        damage_after_armor = amount
        if not ignores_armor:
            effective_armor = max(0, self.armor - armor_shred)
            damage_after_armor = max(1, amount - effective_armor)

        final_damage = int(damage_after_armor * self.damage_taken_multiplier)

        self.current_hp -= final_damage
        if self.current_hp <= 0:
            self.current_hp = 0
            self.kill()

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the enemy, handling stacking logic.
        """
        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                existing_effect.stack_with(new_effect)
                return

        self.status_effects.append(new_effect)

    def _update_status_effects(self, dt: float):
        """Updates all active status effects and removes expired ones."""
        if not self.status_effects:
            return

        for i in range(len(self.status_effects) - 1, -1, -1):
            effect = self.status_effects[i]
            dot_damage = effect.update(dt)

            if dot_damage > 0:
                self.take_damage(dot_damage, ignores_armor=True)

            if not effect.is_active:
                self.status_effects.pop(i)

    def _apply_stat_modifiers(self):
        """
        Calculates final stats for this frame based on active status effects.
        """
        self.speed = self.base_speed
        self.armor = self.base_armor
        self.damage_taken_multiplier = 1.0

        for effect in self.status_effects:
            if effect.effect_type == "stat_modifier":
                stat = effect.stat_to_modify
                if stat == "speed":
                    self.speed *= effect.potency
                elif stat == "damage_taken_multiplier":
                    self.damage_taken_multiplier *= effect.potency
            elif effect.effect_type == "stat_debuff":
                stat = effect.stat_to_modify
                if stat == "armor":
                    self.armor -= effect.potency

    def update(self, dt: float, game_state: "GameState"):
        """
        The main update loop for the enemy entity.
        """
        if not self.is_alive:
            return

        self._update_status_effects(dt)
        self._apply_stat_modifiers()

        if self.current_waypoint_index >= len(self.pixel_path):
            return

        target_pos = self.pixel_path[self.current_waypoint_index]
        direction = target_pos - self.pos
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
            f"Enemy {self.entity_id} reached the end. Dealing {self.damage_to_base} damage."
        )
        game_state.base_hp -= self.damage_to_base
        if game_state.base_hp <= 0:
            game_state.end_game()
        self.kill()
