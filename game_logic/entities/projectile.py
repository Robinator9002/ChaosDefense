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
    from ..game_state import GameState

logger = logging.getLogger(__name__)


class Projectile(Entity):
    """
    Represents a projectile fired from a tower.

    This class has been significantly reworked to handle complex damage
    calculation (execute thresholds, on-apply damage bonuses) and to pass
    special properties like armor shred to the target upon impact. It is the
    primary vehicle for delivering a tower's upgraded abilities.
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
        # NEW: Added parameters to carry all upgrade effects
        armor_shred: int,
        execute_threshold: Optional[Dict[str, float]],
        on_apply_damage: int,
    ):
        """
        Initializes a new, more complex Projectile.
        """
        super().__init__(x, y, max_hp=1)
        self.damage = damage
        self.target = target
        self.speed = 450
        self.effects_to_apply = effects_to_apply
        self.pierce_count = pierce_count
        self.blast_radius = blast_radius
        self.on_blast_effects_data = on_blast_effects_data
        self.status_effects_config = status_effects_config
        self.armor_shred = armor_shred
        self.execute_threshold = execute_threshold
        self.on_apply_damage = on_apply_damage

        # State tracking for piercing shots
        self.enemies_hit: List[uuid.UUID] = []

        # --- Create Sprite ---
        color = (255, 255, 0)  # Default yellow
        if self.blast_radius > 0:
            color = (255, 165, 0)
        elif self.pierce_count > 0:
            color = (255, 255, 255)
        elif any(e.effect_id == "slow" for e in self.effects_to_apply):
            color = (173, 216, 230)
        self.sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.sprite, color, (4, 4), 4)
        self.rect = self.sprite.get_rect(center=(x, y))

    def update(self, dt: float, game_state: "GameState", all_enemies: List["Enemy"]):
        """
        Updates the projectile's position and checks for impact.
        """
        if not self.is_alive:
            return
        if not self.target or not self.target.is_alive:
            self.kill()
            return

        direction = self.target.pos - self.pos
        distance_to_target = direction.length()

        # Check for impact
        if distance_to_target < self.speed * dt:
            self._on_impact(self.target, game_state, all_enemies)
            return

        # Move towards the target
        self.pos += direction.normalize() * self.speed * dt
        super().update(dt, game_state)

    def _on_impact(
        self, hit_enemy: "Enemy", game_state: "GameState", all_enemies: List["Enemy"]
    ):
        """
        Handles all logic for when the projectile hits an enemy. This is the
        core of the effect delivery system.
        """
        if not hit_enemy.is_alive or hit_enemy.entity_id in self.enemies_hit:
            return

        # --- 1. Calculate Final Damage ---
        # Start with base damage and add any on-apply bonuses.
        final_damage = self.damage + self.on_apply_damage

        # Check for execute threshold upgrade.
        if self.execute_threshold:
            hp_percent = hit_enemy.current_hp / hit_enemy.max_hp
            if hp_percent <= self.execute_threshold["percentage"]:
                final_damage = int(
                    final_damage * self.execute_threshold["damage_multiplier"]
                )
                logger.debug(f"Executioner bonus applied! Damage: {final_damage}")

        # --- 2. Deal Damage and Apply Effects ---
        # The enemy's take_damage method now handles armor calculation.
        hit_enemy.take_damage(final_damage, armor_shred=self.armor_shred)
        for effect in self.effects_to_apply:
            hit_enemy.apply_status_effect(effect)
        self.enemies_hit.append(hit_enemy.entity_id)

        # --- 3. Handle Splash Damage ---
        if self.blast_radius > 0:
            self._handle_splash_damage(self.pos, game_state, all_enemies)

        # --- 4. Handle Piercing ---
        if self.pierce_count > 0:
            self.pierce_count -= 1
            new_target = self._find_next_pierce_target(all_enemies)
            if new_target:
                self.target = new_target
                return  # Stay alive and re-target.

        # If not piercing or no new target found, the projectile is destroyed.
        self.kill()

    def _handle_splash_damage(
        self,
        impact_pos: pygame.Vector2,
        game_state: "GameState",
        all_enemies: List["Enemy"],
    ):
        """Applies damage and effects to all enemies within the blast radius."""
        # Splash damage is typically a percentage of the projectile's base damage.
        splash_damage = int(self.damage * 0.5)

        for enemy in all_enemies:
            # Ensure we don't hit the primary target again or other dead enemies.
            if enemy.is_alive and enemy.entity_id not in self.enemies_hit:
                if impact_pos.distance_to(enemy.pos) <= self.blast_radius:
                    # Splash damage does not typically shred armor.
                    enemy.take_damage(splash_damage)

                    # Apply any on-blast effects (e.g., from Artillery's Shrapnel Shells).
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
        """Finds the next valid target for a piercing shot, which is the
        closest enemy that has not yet been hit by this projectile."""
        closest_enemy: Optional["Enemy"] = None
        min_distance = float("inf")

        for enemy in all_enemies:
            if enemy.is_alive and enemy.entity_id not in self.enemies_hit:
                distance = self.pos.distance_to(enemy.pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_enemy = enemy
        return closest_enemy
