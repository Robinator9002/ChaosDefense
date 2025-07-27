# game_logic/entities/tower.py
import pygame
import logging
from typing import List, Optional, TYPE_CHECKING

from .entity import Entity

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemy import Enemy
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a defensive tower that can target and attack enemies.

    Inherits from Entity and adds logic for targeting, firing, and handling
    its own stats based on its type and level.
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
        # --- Basic Tower Properties ---
        self.tower_type_id = (
            tower_type_data.get("name", "Unknown").lower().replace(" ", "_")
        )
        self.level = 1

        # --- Load Base Stats ---
        self.cost = tower_type_data.get("cost", 9999)
        self.range = tower_type_data.get("range", 100)
        self.damage = tower_type_data.get("damage", 0)
        # Fire rate is in shots per second.
        self.fire_rate = tower_type_data.get("fire_rate", 1.0)

        # --- Create Sprite ---
        # For now, we create a simple colored square.
        # This can be replaced with sprite loading logic later.
        tower_sprite = pygame.Surface((tile_size, tile_size))
        tower_sprite.fill((150, 150, 150))  # Neutral grey for the base tower

        # --- Initialize Parent Entity ---
        # Towers are generally not destructible by enemies, so max_hp is nominal.
        super().__init__(x, y, max_hp=100, sprite=tower_sprite)

        # --- Firing and Targeting State ---
        self.fire_cooldown = 0.0
        self.target: Optional[Enemy] = None

        logger.info(
            f"Created Level {self.level} {tower_type_data.get('name')} "
            f"({self.entity_id}) at position ({x}, {y})."
        )

    def update(self, dt: float, game_state: "GameState", enemies: List["Enemy"]):
        """
        Updates the tower's targeting and firing logic.

        Args:
            dt (float): The time elapsed since the last frame.
            game_state (GameState): The current state of the game.
            enemies (List[Enemy]): The list of all active enemies on the map.
        """
        super().update(dt, game_state)

        # Update the fire cooldown timer.
        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        # --- Targeting Logic ---
        # 1. Check if the current target is still valid.
        if self.target and (
            not self.target.is_alive or self.get_distance_to(self.target) > self.range
        ):
            self.target = None  # Target is dead or out of range.

        # 2. If there's no target, find a new one.
        if not self.target:
            self.target = self._find_new_target(enemies)

        # --- Firing Logic ---
        # If there is a valid target and the tower is ready to fire.
        if self.target and self.fire_cooldown <= 0:
            self._fire_at_target()

    def _find_new_target(self, enemies: List["Enemy"]) -> Optional["Enemy"]:
        """
        Finds the best target from the list of enemies, based on proximity.

        Args:
            enemies (List[Enemy]): A list of all potential enemy targets.

        Returns:
            The closest enemy within range, or None if no valid targets exist.
        """
        closest_enemy: Optional[Enemy] = None
        min_distance = float("inf")

        for enemy in enemies:
            distance = self.get_distance_to(enemy)
            if distance <= self.range:
                if distance < min_distance:
                    min_distance = distance
                    closest_enemy = enemy

        return closest_enemy

    def _fire_at_target(self):
        """
        Applies damage to the current target and resets the fire cooldown.
        """
        if not self.target:
            logger.warning(f"Tower {self.entity_id} tried to fire with no target.")
            return

        # In this implementation, the tower deals damage instantly.
        # This could be expanded to create a Projectile entity instead.
        self.target.take_damage(self.damage)
        logger.debug(
            f"Tower {self.entity_id} dealt {self.damage} damage to enemy {self.target.entity_id}."
        )

        # Reset the cooldown based on the tower's fire rate.
        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            # Avoid division by zero for towers that can't fire.
            self.fire_cooldown = float("inf")
