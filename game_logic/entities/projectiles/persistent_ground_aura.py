# game_logic/entities/projectiles/persistent_ground_aura.py
import pygame
import logging
from typing import TYPE_CHECKING, List, Dict, Any

from ..entity import Entity
from ...effects.status_effect import StatusEffect

if TYPE_CHECKING:
    from ..enemies.enemy import Enemy
    from ...game_state import GameState

logger = logging.getLogger(__name__)


class PersistentGroundAura(Entity):
    """
    Represents a stationary area of effect that persists on the ground for a
    duration, continuously applying damage and/or effects to enemies within it.
    This is ideal for mechanics like firewalls or poison clouds.
    """

    def __init__(
        self,
        x: float,
        y: float,
        aura_data: Dict[str, Any],
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new PersistentGroundAura.

        Args:
            x (float): The center x-coordinate of the aura.
            y (float): The center y-coordinate of the aura.
            aura_data (Dict[str, Any]): The data block from the tower's attack
                                       definition, containing properties like
                                       duration, radius, dps, etc.
            status_effects_config (Dict[str, Any]): The global status effects config.
        """
        super().__init__(x, y, max_hp=1)

        # --- Aura Properties ---
        self.radius = aura_data.get("radius", 50)
        self.duration_remaining = aura_data.get("duration", 3.0)
        self.dps = aura_data.get("dps", 0)
        self.tick_rate = aura_data.get("tick_rate", 4)  # Ticks per second
        self.effects_data = aura_data.get("effects", {})
        self.status_effects_config = status_effects_config

        # --- Internal State ---
        self.tick_interval = (
            1.0 / self.tick_rate if self.tick_rate > 0 else float("inf")
        )
        self.tick_timer = 0.0  # Start ready to tick immediately
        self.damage_per_tick = self.dps / self.tick_rate if self.tick_rate > 0 else 0

        # --- Visuals (Placeholder) ---
        # A semi-transparent circle serves as a placeholder for future animations.
        self.sprite = pygame.Surface(
            (self.radius * 2, self.radius * 2), pygame.SRCALPHA
        )
        pygame.draw.circle(
            self.sprite, (255, 100, 0, 80), (self.radius, self.radius), self.radius
        )
        self.rect = self.sprite.get_rect(center=(x, y))

        # Future animation state can be managed here
        # self.animation_timer = 0.0
        # self.current_frame = 0

    def update(self, dt: float, game_state: "GameState", all_enemies: List["Enemy"]):
        """
        Ticks down duration and applies effects to enemies in the area.
        """
        # The GameManager's main loop passes all_enemies to every entity's
        # update method, so we accept it here even if game_state isn't used.
        if not self.is_alive:
            return

        # Tick down the total duration of the aura.
        self.duration_remaining -= dt
        if self.duration_remaining <= 0:
            self.kill()
            return

        # Handle the pulsing effect logic.
        self.tick_timer -= dt
        if self.tick_timer <= 0:
            self.tick_timer += self.tick_interval
            self._apply_pulse_effects(all_enemies)

        # Future animation logic would go here
        # self.animation_timer += dt
        # ...

    def _apply_pulse_effects(self, all_enemies: List["Enemy"]):
        """
        Finds all enemies within the radius and applies damage and status effects.
        """
        for enemy in all_enemies:
            if enemy.is_alive and self.pos.distance_to(enemy.pos) <= self.radius:
                # Apply damage per tick
                if self.damage_per_tick > 0:
                    enemy.take_damage(self.damage_per_tick, ignores_armor=True)

                # Apply status effects
                for effect_id, params in self.effects_data.items():
                    if effect_id in self.status_effects_config:
                        effect_def = self.status_effects_config[effect_id]
                        effect = StatusEffect(
                            effect_id=effect_id,
                            effect_data=effect_def,
                            duration=params.get("duration", 1.0),
                            potency=params.get("potency", 1.0),
                        )
                        enemy.apply_status_effect(effect)

    def draw(self, screen: pygame.Surface, camera_offset: pygame.Vector2, zoom: float):
        """
        Draws the aura's visual effect.
        """
        # The base Entity.draw method handles camera offset and zooming perfectly.
        super().draw(screen, camera_offset, zoom)
