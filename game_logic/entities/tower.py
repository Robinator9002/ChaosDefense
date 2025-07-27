# game_logic/entities/tower.py
import pygame
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from .entity import Entity
from .projectile import Projectile
from ..effects.status_effect import StatusEffect  # Import the StatusEffect class

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemy import Enemy
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a defensive tower that can target and attack enemies by firing
    projectiles, which can carry status effects.
    """

    def __init__(
        self,
        x: float,
        y: float,
        tile_size: int,
        tower_type_data: Dict[str, Any],
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new Tower entity.

        Args:
            x (float): The pixel x-coordinate of the tower's center.
            y (float): The pixel y-coordinate of the tower's center.
            tile_size (int): The size of a game tile in pixels.
            tower_type_data (Dict[str, Any]): The configuration data for this tower type.
            status_effects_config (Dict[str, Any]): The global definitions for all status effects.
        """
        super().__init__(x, y, max_hp=100)  # Call super() first

        self.tower_type_id = (
            tower_type_data.get("name", "Unknown").lower().replace(" ", "_")
        )
        self.level = 1
        self.cost = tower_type_data.get("cost", 0)
        self.range = tower_type_data.get("range", 100)
        self.damage = tower_type_data.get("damage", 0)
        self.fire_rate = tower_type_data.get("fire_rate", 1.0)

        # Store the effect data from the tower's config and the global effect definitions
        self.effects_to_apply_data = tower_type_data.get("effects")
        self.status_effects_config = status_effects_config

        # --- Create Sprite ---
        self.sprite = self._create_sprite(tile_size, tower_type_data)

        # --- Firing and Targeting State ---
        self.fire_cooldown = 0.0
        self.target: Optional[Enemy] = None

        logger.info(
            f"Created Level {self.level} {tower_type_data.get('name')} ({self.entity_id})."
        )

    def _create_sprite(
        self, tile_size: int, tower_data: Dict[str, Any]
    ) -> pygame.Surface:
        """Creates the visual representation for the placed tower."""
        sprite = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        color = tower_data.get("placeholder_color", (128, 128, 128))
        pygame.draw.rect(
            sprite, color, (2, 2, tile_size - 4, tile_size - 4), border_radius=4
        )
        pygame.draw.circle(sprite, (200, 200, 220), (tile_size // 2, tile_size // 2), 6)
        return sprite

    def update(
        self, dt: float, game_state: "GameState", enemies: List["Enemy"]
    ) -> Optional[Projectile]:
        """
        Updates the tower's logic and returns a projectile if one is fired.
        """
        super().update(dt, game_state)

        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        if self.target and (
            not self.target.is_alive or self.get_distance_to(self.target) > self.range
        ):
            self.target = None

        if not self.target:
            self.target = self._find_new_target(enemies)

        if self.target and self.fire_cooldown <= 0:
            return self._fire_at_target()

        return None

    def _find_new_target(self, enemies: List["Enemy"]) -> Optional["Enemy"]:
        """Finds the best target from the list of enemies, based on proximity."""
        closest_enemy: Optional["Enemy"] = None
        min_distance = float("inf")
        for enemy in enemies:
            distance = self.get_distance_to(enemy)
            if distance <= self.range and distance < min_distance:
                min_distance = distance
                closest_enemy = enemy
        return closest_enemy

    def _fire_at_target(self) -> Optional[Projectile]:
        """
        Creates a projectile aimed at the current target, potentially with a status effect.
        """
        if not self.target:
            return None

        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")

        # --- Create StatusEffect instance if applicable ---
        effect_instance = None
        if self.effects_to_apply_data:
            # Assumes one effect per tower for now. Can be expanded to a loop.
            effect_id, effect_params = next(iter(self.effects_to_apply_data.items()))

            if effect_id in self.status_effects_config:
                effect_definition = self.status_effects_config[effect_id]
                effect_instance = StatusEffect(
                    effect_id=effect_id,
                    effect_data=effect_definition,
                    duration=effect_params.get("duration", 1.0),
                    potency=effect_params.get("potency", 1.0),
                )

        # --- Create and return the projectile ---
        new_projectile = Projectile(
            x=self.pos.x,
            y=self.pos.y,
            damage=self.damage,
            target=self.target,
            effect=effect_instance,
        )
        return new_projectile
