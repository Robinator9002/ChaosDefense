# game_logic/entities/tower.py
import pygame
import logging
from typing import List, Optional, TYPE_CHECKING

from .entity import Entity
from .projectile import Projectile  # Import the new Projectile class

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemy import Enemy
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a defensive tower that can target and attack enemies by firing
    projectiles.
    """

    def __init__(self, x: float, y: float, tile_size: int, tower_type_data: dict):
        """
        Initializes a new Tower entity.

        Args:
            x (float): The pixel x-coordinate of the tower's center.
            y (float): The pixel y-coordinate of the tower's center.
            tile_size (int): The size of a game tile in pixels.
            tower_type_data (dict): The configuration data for this tower type.
        """
        self.tower_type_id = (
            tower_type_data.get("name", "Unknown").lower().replace(" ", "_")
        )
        self.level = 1
        self.cost = tower_type_data.get("cost", 9999)
        self.range = tower_type_data.get("range", 100)
        self.damage = tower_type_data.get("damage", 0)
        self.fire_rate = tower_type_data.get("fire_rate", 1.0)

        tower_sprite = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        pygame.draw.rect(
            tower_sprite, (100, 120, 140), (4, 4, tile_size - 8, tile_size - 8)
        )
        pygame.draw.circle(
            tower_sprite, (200, 200, 220), (tile_size // 2, tile_size // 2), 6
        )

        super().__init__(x, y, max_hp=100, sprite=tower_sprite)

        self.fire_cooldown = 0.0
        self.target: Optional[Enemy] = None

        logger.info(
            f"Created Level {self.level} {tower_type_data.get('name')} "
            f"({self.entity_id}) at position ({x}, {y})."
        )

    def update(
        self, dt: float, game_state: "GameState", enemies: List["Enemy"]
    ) -> Optional[Projectile]:
        """
        Updates the tower's logic and returns a projectile if one is fired.

        Args:
            dt (float): The time elapsed since the last frame.
            game_state (GameState): The current state of the game.
            enemies (List[Enemy]): The list of all active enemies on the map.

        Returns:
            A new Projectile instance if the tower fires, otherwise None.
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
        closest_enemy: Optional[Enemy] = None
        min_distance = float("inf")

        for enemy in enemies:
            distance = self.get_distance_to(enemy)
            if distance <= self.range:
                if distance < min_distance:
                    min_distance = distance
                    closest_enemy = enemy

        return closest_enemy

    def _fire_at_target(self) -> Optional[Projectile]:
        """
        Creates a projectile aimed at the current target and resets the fire cooldown.

        Returns:
            A new Projectile instance.
        """
        if not self.target:
            logger.warning(f"Tower {self.entity_id} tried to fire with no target.")
            return None

        # Reset the cooldown based on the tower's fire rate.
        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")

        # Create and return a new projectile instance.
        new_projectile = Projectile(
            x=self.pos.x, y=self.pos.y, damage=self.damage, target=self.target
        )
        logger.debug(
            f"Tower {self.entity_id} created projectile {new_projectile.entity_id} "
            f"targeting enemy {self.target.entity_id}."
        )
        return new_projectile
