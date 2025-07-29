# game_logic/entities/projectiles/persistent_attached_aura.py
import pygame
import logging
from typing import TYPE_CHECKING, List, Dict, Any

from ..entity import Entity
from ...effects.status_effect import StatusEffect

if TYPE_CHECKING:
    from ..enemies.enemy import Enemy
    from ...game_state import GameState

logger = logging.getLogger(__name__)


class PersistentAttachedAura(Entity):
    """
    Represents an area of effect that attaches to a specific target enemy,
    moving with it and applying effects to all enemies within a radius around it.
    Ideal for mechanics like lightning storms or targeted curses.
    """

    def __init__(
        self,
        target: "Enemy",
        aura_data: Dict[str, Any],
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new PersistentAttachedAura.

        Args:
            target (Enemy): The enemy this aura will attach and follow.
            aura_data (Dict[str, Any]): Data from the tower's attack definition.
            status_effects_config (Dict[str, Any]): The global status effects config.
        """
        # Initialize at the target's current position
        super().__init__(target.pos.x, target.pos.y, max_hp=1)

        # --- Aura Properties ---
        self.target = target
        self.radius = aura_data.get("radius", 50)
        self.duration_remaining = aura_data.get("duration", 3.0)
        self.dps = aura_data.get("dps", 0)
        self.tick_rate = aura_data.get("tick_rate", 4)
        self.effects_data = aura_data.get("effects", {})
        self.status_effects_config = status_effects_config

        # --- Special Mechanic Data ---
        self.bonus_dmg_vs_armor_mult = aura_data.get(
            "bonus_damage_vs_armor_multiplier", 0
        )

        # --- Internal State ---
        self.tick_interval = (
            1.0 / self.tick_rate if self.tick_rate > 0 else float("inf")
        )
        self.tick_timer = 0.0
        self.damage_per_tick = self.dps / self.tick_rate if self.tick_rate > 0 else 0

        # --- Visuals (Placeholder) ---
        self.sprite = pygame.Surface(
            (self.radius * 2, self.radius * 2), pygame.SRCALPHA
        )
        pygame.draw.circle(
            self.sprite, (180, 180, 255, 100), (self.radius, self.radius), self.radius
        )
        self.rect = self.sprite.get_rect(center=self.pos)

    def update(self, dt: float, game_state: "GameState", all_enemies: List["Enemy"]):
        """
        Updates the aura's position to follow its target, ticks down duration,
        and applies pulsing effects.
        """
        if not self.is_alive:
            return

        # Tick down duration.
        self.duration_remaining -= dt
        if self.duration_remaining <= 0:
            self.kill()
            return

        # Attachment logic: Follow the target.
        if self.target and self.target.is_alive:
            self.pos.update(self.target.pos)
        # If the target dies, the aura persists at its last known location.

        # Handle pulsing effect.
        self.tick_timer -= dt
        if self.tick_timer <= 0:
            self.tick_timer += self.tick_interval
            self._apply_pulse_effects(all_enemies)

        # Update the rect's position after moving.
        super().update(dt, game_state)

    def _apply_pulse_effects(self, all_enemies: List["Enemy"]):
        """
        Finds all enemies within the radius and applies damage and effects.
        This version includes special damage calculation logic.
        """
        for enemy in all_enemies:
            if enemy.is_alive and self.pos.distance_to(enemy.pos) <= self.radius:
                # --- Custom Damage Logic for Stormcaller ---
                base_damage = self.damage_per_tick
                bonus_damage = enemy.armor * self.bonus_dmg_vs_armor_mult
                total_damage = base_damage + bonus_damage

                if total_damage > 0:
                    enemy.take_damage(total_damage, ignores_armor=True)

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
        """Draws the aura's visual effect."""
        super().draw(screen, camera_offset, zoom)
