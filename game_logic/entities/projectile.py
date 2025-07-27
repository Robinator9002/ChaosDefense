# game_logic/entities/projectile.py
import pygame
import logging
from typing import TYPE_CHECKING, Optional

from .entity import Entity

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemy import Enemy
    from game_logic.game_state import GameState
    from game_logic.effects.status_effect import StatusEffect

logger = logging.getLogger(__name__)


class Projectile(Entity):
    """
    Represents a projectile fired from a tower towards a specific enemy.
    It can carry a status effect to apply on impact.
    """

    def __init__(
        self,
        x: float,
        y: float,
        damage: int,
        target: "Enemy",
        effect: Optional["StatusEffect"] = None,
    ):
        """
        Initializes a new Projectile.

        Args:
            x (float): The starting x-coordinate (usually the tower's center).
            y (float): The starting y-coordinate (usually the tower's center).
            damage (int): The amount of damage the projectile deals on impact.
            target (Enemy): The enemy entity that the projectile will track.
            effect (Optional[StatusEffect]): The status effect instance to apply on impact.
        """
        # --- Projectile Properties ---
        self.damage = damage
        self.target = target
        self.speed = 300
        self.effect_to_apply = effect  # Store the effect object

        # --- Create Sprite ---
        projectile_sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        # Change color if it has an effect (e.g., light blue for slow)
        color = (
            (173, 216, 230)
            if self.effect_to_apply and self.effect_to_apply.effect_id == "slow"
            else (255, 255, 0)
        )
        pygame.draw.circle(projectile_sprite, color, (4, 4), 4)

        super().__init__(x, y, max_hp=1, sprite=projectile_sprite)
        logger.debug(
            f"Projectile {self.entity_id} created, targeting {target.entity_id}."
        )

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates the projectile's position by moving it towards its target.
        """
        if not self.is_alive or not self.target.is_alive:
            self.kill()
            return

        direction = self.target.pos - self.pos
        distance_to_target = direction.length()

        if distance_to_target < self.speed * dt:
            self._on_impact()
            return

        self.pos += direction.normalize() * self.speed * dt
        super().update(dt, game_state)

    def _on_impact(self):
        """
        Handles the logic for when the projectile hits its target.
        It deals damage and applies any status effect it carries.
        """
        if not self.target.is_alive:
            self.kill()
            return

        # 1. Deal damage
        self.target.take_damage(self.damage)

        # 2. Apply the status effect, if any
        if self.effect_to_apply:
            self.target.apply_status_effect(self.effect_to_apply)
            logger.debug(
                f"Projectile applied '{self.effect_to_apply.effect_id}' to {self.target.entity_id}."
            )

        self.kill()
