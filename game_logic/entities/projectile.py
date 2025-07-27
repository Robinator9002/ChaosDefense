# game_logic/entities/projectile.py
import pygame
import logging
import uuid
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from .entity import Entity
from ..effects.status_effect import StatusEffect

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Projectile(Entity):
    """
    Represents a projectile fired from a tower.

    This class has been significantly upgraded to handle advanced behaviors like
    piercing, splash damage (blast radius), and applying multiple status effects.
    It now tracks which enemies it has already hit to manage its lifecycle,
    especially for piercing shots.
    """

    def __init__(
        self,
        x: float,
        y: float,
        damage: int,
        target: "Enemy",
        effects_to_apply: List[StatusEffect],
        pierce_count: int,
        blast_radius: float,
        on_blast_effects_data: List[Dict[str, Any]],
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new Projectile.

        Args:
            x (float): The starting x-coordinate.
            y (float): The starting y-coordinate.
            damage (int): The base damage the projectile deals on impact.
            target (Enemy): The initial enemy entity the projectile will track.
            effects_to_apply (List[StatusEffect]): A list of status effect instances
                                                   to apply on direct impact.
            pierce_count (int): How many additional enemies the projectile can hit.
            blast_radius (float): The radius for splash damage on impact.
            on_blast_effects_data (List[Dict]): Data for effects to apply to enemies
                                                hit by splash damage.
            status_effects_config (Dict): The global status effects configuration,
                                          needed for creating blast effects.
        """
        # --- Core Projectile Properties ---
        self.damage = damage
        self.target = target
        self.speed = 450  # Increased speed for a better feel
        self.effects_to_apply = effects_to_apply
        self.pierce_count = pierce_count
        self.blast_radius = blast_radius
        self.on_blast_effects_data = on_blast_effects_data
        self.status_effects_config = status_effects_config

        # --- State Tracking ---
        # Keep track of enemies already hit to avoid double-hitting with pierce.
        self.enemies_hit: List[uuid.UUID] = []

        # --- Create Sprite ---
        # The sprite's appearance can be customized based on its properties.
        color = (255, 255, 0)  # Default yellow
        if self.blast_radius > 0:
            color = (255, 165, 0)  # Orange for explosive
        elif self.pierce_count > 0:
            color = (255, 255, 255)  # White for piercing
        elif any(e.effect_id == "slow" for e in self.effects_to_apply):
            color = (173, 216, 230)  # Light blue for slow

        projectile_sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(projectile_sprite, color, (4, 4), 4)

        super().__init__(x, y, max_hp=1, sprite=projectile_sprite)
        logger.debug(
            f"Projectile {self.entity_id} created, targeting {target.entity_id}."
        )

    def update(self, dt: float, game_state: "GameState", all_enemies: List["Enemy"]):
        """
        Updates the projectile's position and checks for impact.
        """
        if not self.is_alive:
            return

        # If the current target is dead, try to find a new one.
        if not self.target or not self.target.is_alive:
            self.kill()  # If original target is gone, projectile fizzles.
            return

        # --- Movement ---
        direction = self.target.pos - self.pos
        distance_to_target = direction.length()

        # --- Impact Check ---
        if distance_to_target < self.speed * dt:
            # If we are closer than one frame of movement, we hit the target.
            self._on_impact(self.target, game_state, all_enemies)
            return

        # Move towards the target.
        self.pos += direction.normalize() * self.speed * dt
        super().update(dt, game_state)

    def _on_impact(
        self, hit_enemy: "Enemy", game_state: "GameState", all_enemies: List["Enemy"]
    ):
        """
        Handles all logic for when the projectile hits an enemy.
        This includes dealing damage, applying effects, handling splash, and piercing.
        """
        if not hit_enemy.is_alive or hit_enemy.entity_id in self.enemies_hit:
            return  # Don't hit dead enemies or enemies we've already hit.

        # 1. Deal direct damage and apply effects to the primary target.
        hit_enemy.take_damage(self.damage)
        for effect in self.effects_to_apply:
            hit_enemy.apply_status_effect(effect)
        self.enemies_hit.append(hit_enemy.entity_id)

        # 2. Handle Splash Damage (Blast Radius)
        if self.blast_radius > 0:
            self._handle_splash_damage(self.pos, game_state, all_enemies)

        # 3. Handle Piercing
        if self.pierce_count > 0:
            self.pierce_count -= 1
            new_target = self._find_next_pierce_target(all_enemies)
            if new_target:
                self.target = new_target  # Re-target and continue moving.
                return  # IMPORTANT: Do not kill the projectile yet.
            else:
                self.kill()  # No more targets to pierce, so it's done.
        else:
            self.kill()  # No piercing ability, so it's done.

    def _handle_splash_damage(
        self,
        impact_pos: pygame.Vector2,
        game_state: "GameState",
        all_enemies: List["Enemy"],
    ):
        """Applies damage and effects to all enemies within the blast radius."""
        splash_damage = int(self.damage * 0.5)  # Splash damage is 50% of base damage.

        for enemy in all_enemies:
            if enemy.entity_id not in self.enemies_hit:
                if impact_pos.distance_to(enemy.pos) <= self.blast_radius:
                    enemy.take_damage(splash_damage)
                    # Apply any on-blast effects
                    for effect_data in self.on_blast_effects_data:
                        effect_id = effect_data["id"]
                        if effect_id in self.status_effects_config:
                            effect_def = self.status_effects_config[effect_id]
                            effect_instance = StatusEffect(
                                effect_id=effect_id,
                                effect_data=effect_def,
                                duration=effect_data.get("duration", 1.0),
                                potency=effect_data.get("potency", 1.0),
                            )
                            enemy.apply_status_effect(effect_instance)

    def _find_next_pierce_target(self, all_enemies: List["Enemy"]) -> Optional["Enemy"]:
        """Finds the next valid target for a piercing shot."""
        closest_enemy: Optional["Enemy"] = None
        min_distance = float("inf")

        for enemy in all_enemies:
            if enemy.is_alive and enemy.entity_id not in self.enemies_hit:
                distance = self.pos.distance_to(enemy.pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_enemy = enemy

        return closest_enemy
