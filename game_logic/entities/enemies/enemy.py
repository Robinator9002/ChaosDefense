# game_logic/entities/enemies/enemy.py
import pygame
import logging
from typing import List, Tuple, TYPE_CHECKING, Dict, Any, Optional

from ..entity import Entity

if TYPE_CHECKING:
    from ...game_state import GameState
    from ...game_ai.targeting.targeting_manager import TargetingManager


logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Represents an enemy unit that moves along a path.

    REFACTORED: With the new intelligent EffectHandler, this class no longer
    requires dummy tower-specific stats (like base_damage) to function correctly.
    It now also includes logic to draw its own health bar when damaged.
    """

    def __init__(
        self,
        enemy_type_data: dict,
        level: int,
        path: List[Tuple[int, int]],
        tile_size: int,
        difficulty_modifier: float,
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new Enemy.
        """
        base_stats = enemy_type_data.get("base_stats", {})
        scaling = enemy_type_data.get("scaling_per_level_add", {})
        render_props = enemy_type_data.get("render_props", {})

        self.name = enemy_type_data.get("name", "Unknown Enemy")
        self.enemy_type_id = enemy_type_data.get("id", "unknown")
        self.level = level

        hp_increase = scaling.get("hp", 0)
        level_scaled_hp = base_stats.get("hp", 1) + (hp_increase * (level - 1))
        calculated_hp = int(level_scaled_hp * difficulty_modifier)

        speed_increase = scaling.get("speed", 0)
        # These are the entity's core stats. The EffectHandler will snapshot them.
        self.speed = base_stats.get("speed", 50) + (speed_increase * (level - 1))

        armor_increase = scaling.get("armor", 0)
        level_scaled_armor = base_stats.get("armor", 0) + (armor_increase * (level - 1))
        self.armor = int(level_scaled_armor)

        bounty_increase = scaling.get("bounty", 0)
        self.bounty = int(base_stats.get("bounty", 0) + (bounty_increase * (level - 1)))
        self.damage_to_base = int(base_stats.get("damage", 1) * difficulty_modifier)
        self.immunities: List[str] = base_stats.get("immunities", [])

        self.damage_taken_multiplier = 1.0

        self.path = path
        self.tile_size = tile_size
        self.pixel_path = [
            pygame.Vector2(x * tile_size + tile_size / 2, y * tile_size + tile_size / 2)
            for x, y in path
        ]
        initial_pos = self.pixel_path[0] if self.pixel_path else pygame.Vector2(0, 0)
        self.current_waypoint_index = 1

        size = render_props.get("size", 24)
        color = render_props.get("color", (255, 0, 255))
        placeholder_sprite = pygame.Surface((size, size))
        placeholder_sprite.fill(color)

        # The super().__init__ call must come after the core stats are set,
        # so the EffectHandler can take an accurate initial snapshot.
        super().__init__(
            initial_pos.x, initial_pos.y, calculated_hp, placeholder_sprite
        )

        self.auras = enemy_type_data.get("auras", [])
        self.status_effects_config = status_effects_config

    def take_damage(
        self, amount: int, armor_shred: int = 0, ignores_armor: bool = False
    ):
        """
        Reduces the entity's current HP, factoring in armor.
        """
        if not self.is_alive:
            return

        damage_after_armor = amount
        if not ignores_armor:
            effective_armor = max(0, self.armor - armor_shred)
            damage_after_armor = max(1, amount - effective_armor)

        final_damage = int(damage_after_armor * self.damage_taken_multiplier)
        super().take_damage(final_damage, ignores_armor=True)

    def update(
        self, dt: float, game_state: "GameState", targeting_manager: "TargetingManager"
    ) -> Optional["Enemy"]:
        """
        The main update loop for the enemy entity.
        """
        if not self.is_alive:
            return None

        super().update(dt, game_state, targeting_manager)

        # --- Movement Logic ---
        if self.current_waypoint_index >= len(self.pixel_path):
            return None

        target_pos = self.pixel_path[self.current_waypoint_index]
        direction = target_pos - self.pos
        distance_to_target = direction.length()

        if distance_to_target < self.speed * dt:
            self.pos = target_pos
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.pixel_path):
                return self._on_reach_end(game_state)
        else:
            self.pos += direction.normalize() * self.speed * dt

        return None

    def _on_reach_end(self, game_state: "GameState") -> "Enemy":
        """
        Handles logic for when the enemy reaches the end of its path.
        """
        logger.warning(
            f"Enemy {self.name} ({self.entity_id}) reached the end. Dealing {self.damage_to_base} damage."
        )
        game_state.base_hp -= self.damage_to_base
        if game_state.base_hp <= 0:
            game_state.end_game()
        self.kill()
        return self

    def draw(self, screen: pygame.Surface, camera_offset: pygame.Vector2, zoom: float):
        """
        Draws the enemy and its health bar to the screen.
        """
        # First, call the parent Entity's draw method to draw the main sprite.
        super().draw(screen, camera_offset, zoom)

        # --- Health Bar Logic ---
        # Only draw the health bar if the enemy is alive and has taken damage.
        if self.is_alive and self.current_hp < self.max_hp:
            # Calculate the on-screen position and dimensions.
            screen_pos = (self.pos * zoom) + camera_offset
            bar_width = self.rect.width * zoom * 0.8
            bar_height = max(2, 4 * zoom)  # Ensure bar is visible even when zoomed out.

            # Position the health bar above the enemy sprite.
            bar_x = screen_pos.x - bar_width / 2
            bar_y = (
                screen_pos.y - (self.rect.height * zoom / 2) - bar_height - (2 * zoom)
            )

            # Calculate the width of the foreground (current health) bar.
            health_percentage = self.current_hp / self.max_hp
            current_health_width = bar_width * health_percentage

            # Define colors for the health bar.
            background_color = (139, 0, 0)  # Dark Red
            foreground_color = (255, 0, 0)  # Red

            # Draw the background bar (the empty part).
            pygame.draw.rect(
                screen, background_color, (bar_x, bar_y, bar_width, bar_height)
            )
            # Draw the foreground bar (the current health).
            pygame.draw.rect(
                screen,
                foreground_color,
                (bar_x, bar_y, current_health_width, bar_height),
            )
