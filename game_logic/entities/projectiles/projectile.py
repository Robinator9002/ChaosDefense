# game_logic/entities/projectiles/projectile.py
import pygame
import logging
import uuid
import random
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from ..entity import Entity
from ...effects.status_effect import StatusEffect
from .projectile_data import ProjectileData

if TYPE_CHECKING:
    from ..enemies.enemy import Enemy
    from ...game_state import GameState
    from ...game_ai.targeting.targeting_manager import TargetingManager


logger = logging.getLogger(__name__)


class Projectile(Entity):
    """
    Represents a projectile fired from a tower.

    REFACTORED: Its update signature is now compatible with the new
    GameManager loop, accepting the TargetingManager.
    """

    def __init__(
        self,
        x: float,
        y: float,
        target: "Enemy",
        data: ProjectileData,
    ):
        """
        Initializes a new Projectile based on a ProjectileData object.
        """
        super().__init__(x, y, max_hp=1)

        self.damage = data.damage
        self.effects_to_apply = data.effects_to_apply
        self.status_effects_config = data.status_effects_config
        self.pierce_count = data.pierce_count
        self.blast_radius = data.blast_radius
        self.armor_shred = data.armor_shred
        self.on_blast_effects_data = data.on_blast_effects_data
        self.conditional_effects = data.conditional_effects
        self.on_hit_area_effects = data.on_hit_area_effects
        self.execute_threshold = data.execute_threshold
        self.on_apply_damage = data.on_apply_damage
        self.bonus_damage_per_debuff = data.bonus_damage_per_debuff

        self.target = target
        self.speed = 450
        self.last_known_target_pos = target.pos.copy()
        self.retarget_radius = 120
        self.enemies_hit: List[uuid.UUID] = []

        color = (255, 255, 0)
        if self.blast_radius > 0:
            color = (255, 165, 0)
        elif self.pierce_count > 0:
            color = (255, 255, 255)
        elif any(e.effect_id == "slow" for e in self.effects_to_apply):
            color = (173, 216, 230)
        self.sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.sprite, color, (4, 4), 4)
        self.rect = self.sprite.get_rect(center=(x, y))

    def update(
        self, dt: float, game_state: "GameState", targeting_manager: "TargetingManager"
    ):
        """
        Updates the projectile's position, handling target loss and retargeting.
        """
        if not self.is_alive:
            return

        if not self.target or not self.target.is_alive:
            new_target = self._find_new_target_nearby(targeting_manager)
            if new_target:
                self.target = new_target
            else:
                self.target = None

        destination = self.last_known_target_pos
        if self.target:
            destination = self.target.pos
            self.last_known_target_pos = self.target.pos.copy()

        direction = destination - self.pos
        distance_to_destination = direction.length()

        if distance_to_destination < self.speed * dt:
            if self.target:
                self._on_impact(self.target, game_state, targeting_manager)
            else:
                self.kill()
            return

        self.pos += direction.normalize() * self.speed * dt
        super().update(dt, game_state, targeting_manager)

    def _find_new_target_nearby(
        self, targeting_manager: "TargetingManager"
    ) -> Optional["Enemy"]:
        """Finds a new target using an efficient query."""
        potential_targets = targeting_manager.get_nearby_enemies(
            self.last_known_target_pos, self.retarget_radius
        )
        valid_targets = [
            t
            for t in potential_targets
            if t.is_alive and t.entity_id not in self.enemies_hit
        ]
        if not valid_targets:
            return None
        return min(
            valid_targets,
            key=lambda t: self.last_known_target_pos.distance_squared_to(t.pos),
        )

    def _on_impact(
        self,
        hit_enemy: "Enemy",
        game_state: "GameState",
        targeting_manager: "TargetingManager",
    ):
        """Handles all logic for when the projectile hits an enemy."""
        if not hit_enemy.is_alive or hit_enemy.entity_id in self.enemies_hit:
            return

        final_damage = self.damage + self.on_apply_damage

        if self.bonus_damage_per_debuff > 0:
            final_damage += self.bonus_damage_per_debuff * len(
                hit_enemy.effect_handler.status_effects
            )

        if self.execute_threshold:
            hp_percent = hit_enemy.current_hp / hit_enemy.max_hp
            if hp_percent <= self.execute_threshold["percentage"]:
                final_damage = int(
                    final_damage * self.execute_threshold["damage_multiplier"]
                )

        hit_enemy.take_damage(final_damage, armor_shred=self.armor_shred)

        for effect in self.effects_to_apply:
            hit_enemy.apply_status_effect(effect)

        for cond_effect_data in self.conditional_effects:
            if any(
                eff.effect_id == cond_effect_data["if_target_has"]
                for eff in hit_enemy.effect_handler.status_effects
            ):
                if random.random() <= cond_effect_data["chance"]:
                    effect_def = cond_effect_data["effect"]
                    if effect_def["id"] in self.status_effects_config:
                        effect_instance = StatusEffect(
                            effect_id=effect_def["id"],
                            effect_data=self.status_effects_config[effect_def["id"]],
                            duration=effect_def.get("duration", 1.0),
                            potency=effect_def.get("potency", 1.0),
                        )
                        hit_enemy.apply_status_effect(effect_instance)

        self.enemies_hit.append(hit_enemy.entity_id)

        if self.blast_radius > 0:
            self._handle_splash_damage(self.pos, game_state, targeting_manager)

        for area_effect_data in self.on_hit_area_effects:
            if random.random() <= area_effect_data["chance"]:
                self._handle_area_effect(self.pos, area_effect_data, targeting_manager)

        if self.pierce_count > 0:
            self.pierce_count -= 1
            new_target = self._find_next_pierce_target(targeting_manager)
            if new_target:
                self.target = new_target
                return

        self.kill()

    def _handle_splash_damage(
        self,
        impact_pos: pygame.Vector2,
        game_state: "GameState",
        targeting_manager: "TargetingManager",
    ):
        """Applies damage and effects to all enemies within the blast radius."""
        splash_damage = int(self.damage * 0.5)
        nearby_enemies = targeting_manager.get_nearby_enemies(
            impact_pos, self.blast_radius
        )
        for enemy in nearby_enemies:
            if enemy.entity_id not in self.enemies_hit:
                enemy.take_damage(splash_damage)
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

    def _handle_area_effect(
        self,
        center_pos: pygame.Vector2,
        area_effect_data: Dict[str, Any],
        targeting_manager: "TargetingManager",
    ):
        """Handles generic area of effect abilities like frost nova."""
        radius = area_effect_data["radius"]
        damage = area_effect_data["damage"]
        effect_def = area_effect_data.get("effect")
        nearby_enemies = targeting_manager.get_nearby_enemies(center_pos, radius)

        for enemy in nearby_enemies:
            if damage > 0:
                enemy.take_damage(damage)
            if effect_def and effect_def["id"] in self.status_effects_config:
                effect_instance = StatusEffect(
                    effect_id=effect_def["id"],
                    effect_data=self.status_effects_config[effect_def["id"]],
                    duration=effect_def.get("duration", 1.0),
                    potency=effect_def.get("potency", 1.0),
                )
                enemy.apply_status_effect(effect_instance)

    def _find_next_pierce_target(
        self, targeting_manager: "TargetingManager"
    ) -> Optional["Enemy"]:
        """
        Finds the next valid target for a piercing shot using an efficient
        spatial query.
        """
        # --- OPTIMIZED: Use a spatial query instead of a full map scan (Issue #9) ---
        # Define a reasonable radius to search for the next target.
        pierce_search_radius = 150
        potential_targets = targeting_manager.get_nearby_enemies(
            self.pos, pierce_search_radius
        )

        # Filter out enemies that have already been hit by this projectile.
        valid_targets = [
            e for e in potential_targets if e.entity_id not in self.enemies_hit
        ]

        if not valid_targets:
            return None

        # Return the closest valid target.
        return min(valid_targets, key=lambda e: self.pos.distance_squared_to(e.pos))
