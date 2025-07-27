# game_logic/entities/projectile.py
import pygame
import logging
from typing import TYPE_CHECKING

from .entity import Entity

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemy import Enemy
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Projectile(Entity):
    """
    Represents a projectile fired from a tower towards a specific enemy.

    This entity moves towards its target each frame and deals damage upon impact.
    """

    def __init__(self, x: float, y: float, damage: int, target: "Enemy"):
        """
        Initializes a new Projectile.

        Args:
            x (float): The starting x-coordinate (usually the tower's center).
            y (float): The starting y-coordinate (usually the tower's center).
            damage (int): The amount of damage the projectile deals on impact.
            target (Enemy): The enemy entity that the projectile will track.
        """
        # --- Projectile Properties ---
        self.damage = damage
        self.target = target
        self.speed = 300  # pixels per second, can be configured later

        # --- Create Sprite ---
        # For now, a simple circle sprite.
        projectile_sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(projectile_sprite, (255, 255, 0), (4, 4), 4)  # Yellow circle

        # --- Initialize Parent Entity ---
        # Projectiles have no health; they are destroyed on impact.
        super().__init__(x, y, max_hp=1, sprite=projectile_sprite)

        logger.debug(
            f"Projectile {self.entity_id} created, targeting {target.entity_id}."
        )

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates the projectile's position by moving it towards its target.

        Args:
            dt (float): The time elapsed since the last frame.
            game_state (GameState): The current state of the game.
        """
        if not self.is_alive or not self.target.is_alive:
            # If the projectile or its target is no longer valid, kill the projectile.
            self.kill()
            return

        # --- Homing Logic ---
        direction = self.target.pos - self.pos
        distance_to_target = direction.length()

        # 1. Check for collision.
        # If the distance we will travel this frame is greater than the distance
        # to the target, we consider it a hit.
        if distance_to_target < self.speed * dt:
            self._on_impact()
            return

        # 2. Move towards the target.
        self.pos += direction.normalize() * self.speed * dt

        # Ensure the entity's rect is updated for drawing.
        super().update(dt, game_state)

    def _on_impact(self):
        """
        Handles the logic for when the projectile hits its target.
        """
        if not self.target.is_alive:
            return  # Avoids dealing damage to an already dead target

        logger.debug(
            f"Projectile {self.entity_id} hit target {self.target.entity_id}, "
            f"dealing {self.damage} damage."
        )
        self.target.take_damage(self.damage)
        self.kill()  # The projectile is consumed on impact.
