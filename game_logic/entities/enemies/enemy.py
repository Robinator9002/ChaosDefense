# game_logic/entities/enemies/enemy.py
import pygame
import logging
from typing import List, Tuple, TYPE_CHECKING, Dict, Any

from ..entity import Entity

if TYPE_CHECKING:
    from ...game_state import GameState

    # StatusEffect is no longer directly managed here, but is needed for type hints.
    from ...effects.status_effect import StatusEffect

logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Represents an enemy unit that moves along a path.

    REFACTORED: This class has been dramatically simplified. It no longer
    manages its own status effects. Instead, it inherits the universal
    EffectHandler component from the base Entity class, which handles all
    buff/debuff logic automatically.
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
        scaling = enemy_type_data.get("scaling_per_level_add", {})
        render_props = enemy_type_data.get("render_props", {})

        self.name = enemy_type_data.get("name", "Unknown Enemy")
        self.level = level

        # --- Base Stat Calculation ---
        # These 'base' stats are the permanent, unmodified values for the enemy.
        hp_increase = scaling.get("hp", 0)
        level_scaled_hp = base_stats.get("hp", 1) + (hp_increase * (level - 1))
        calculated_hp = int(level_scaled_hp * difficulty_modifier)

        speed_increase = scaling.get("speed", 0)
        self.base_speed = base_stats.get("speed", 50) + (speed_increase * (level - 1))

        armor_increase = scaling.get("armor", 0)
        level_scaled_armor = base_stats.get("armor", 0) + (armor_increase * (level - 1))
        self.base_armor = int(level_scaled_armor)

        bounty_increase = scaling.get("bounty", 0)
        self.bounty = int(base_stats.get("bounty", 0) + (bounty_increase * (level - 1)))
        self.damage_to_base = int(base_stats.get("damage", 1) * difficulty_modifier)
        self.immunities: List[str] = base_stats.get("immunities", [])

        # --- Dynamic Stat Initialization ---
        # These are the 'live' stats that will be modified by the EffectHandler each frame.
        self.speed = self.base_speed
        self.armor = self.base_armor
        self.damage_taken_multiplier = 1.0

        # --- Pathing and Position ---
        self.path = path
        self.tile_size = tile_size
        self.pixel_path = [
            pygame.Vector2(x * tile_size + tile_size / 2, y * tile_size + tile_size / 2)
            for x, y in path
        ]
        initial_pos = self.pixel_path[0] if self.pixel_path else pygame.Vector2(0, 0)
        self.current_waypoint_index = 1

        # --- Visuals ---
        size = render_props.get("size", 24)
        color = render_props.get("color", (255, 0, 255))
        placeholder_sprite = pygame.Surface((size, size))
        placeholder_sprite.fill(color)

        # Initialize the parent Entity AFTER all stats are calculated.
        super().__init__(
            initial_pos.x, initial_pos.y, calculated_hp, placeholder_sprite
        )

    # The apply_status_effect method is now inherited from Entity.

    def take_damage(
        self, amount: int, armor_shred: int = 0, ignores_armor: bool = False
    ):
        """
        Reduces the entity's current HP, factoring in armor. This method
        overrides the base Entity's simpler take_damage.
        """
        if not self.is_alive:
            return

        damage_after_armor = amount
        if not ignores_armor:
            effective_armor = max(0, self.armor - armor_shred)
            damage_after_armor = max(1, amount - effective_armor)

        final_damage = int(damage_after_armor * self.damage_taken_multiplier)

        # Call the base class's take_damage to handle the HP reduction and death.
        # We pass ignores_armor=True because we have already calculated armor here.
        super().take_damage(final_damage, ignores_armor=True)

    def update(
        self,
        dt: float,
        game_state: "GameState",
        all_enemies: List["Entity"] = [],
        all_towers: List["Entity"] = [],
    ):
        """
        The main update loop for the enemy entity.
        """
        if not self.is_alive:
            return

        # The parent update call now handles all status effect logic.
        super().update(dt, game_state)

        # --- Movement Logic ---
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

    def _on_reach_end(self, game_state: "GameState"):
        """Handles logic for when the enemy reaches the end of its path."""
        logger.warning(
            f"Enemy {self.name} ({self.entity_id}) reached the end. Dealing {self.damage_to_base} damage."
        )
        game_state.base_hp -= self.damage_to_base
        if game_state.base_hp <= 0:
            game_state.end_game()
        self.kill()
