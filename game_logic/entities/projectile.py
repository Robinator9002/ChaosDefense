# game_logic/entities/projectile.py
import pygame
import logging
import uuid
import random
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from .entity import Entity
from ..effects.status_effect import StatusEffect

if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from ..game_state import GameState

logger = logging.getLogger(__name__)


class Projectile(Entity):
    """
    Represents a projectile fired from a tower.
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
        armor_shred: int,
        execute_threshold: Optional[Dict[str, float]],
        on_apply_damage: int,
        bonus_damage_per_debuff: int,
        conditional_effects: List[Dict[str, Any]],
        on_hit_area_effects: List[Dict[str, Any]],
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
        self.bonus_damage_per_debuff = bonus_damage_per_debuff
        self.conditional_effects = conditional_effects
        self.on_hit_area_effects = on_hit_area_effects

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

    def update(self, dt: float, game_state: "GameState", all_enemies: List["Enemy"]):
        """
        Updates the projectile's position, handling target loss and retargeting.
        """
        if not self.is_alive:
            return

        if not self.target or not self.target.is_alive:
            new_target = self._find_new_target_nearby(all_enemies)
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
                self._on_impact(self.target, game_state, all_enemies)
            else:
                self.kill()
            return

        self.pos += direction.normalize() * self.speed * dt
        super().update(dt, game_state)

    def _find_new_target_nearby(self, all_enemies: List["Enemy"]) -> Optional["Enemy"]:
        """
        Finds the closest living enemy to the projectile's last known target position.
        """
        potential_targets = []
        for enemy in all_enemies:
            if enemy.is_alive and enemy.entity_id not in self.enemies_hit:
                distance = self.last_known_target_pos.distance_to(enemy.pos)
                if distance <= self.retarget_radius:
                    potential_targets.append((distance, enemy))

        if not potential_targets:
            return None

        return min(potential_targets, key=lambda t: t[0])[1]

    def _on_impact(
        self, hit_enemy: "Enemy", game_state: "GameState", all_enemies: List["Enemy"]
    ):
        """
        Handles all logic for when the projectile hits an enemy.
        """
        if not hit_enemy.is_alive or hit_enemy.entity_id in self.enemies_hit:
            return

        final_damage = self.damage + self.on_apply_damage

        if self.bonus_damage_per_debuff > 0:
            final_damage += self.bonus_damage_per_debuff * len(hit_enemy.status_effects)

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
            if hit_enemy.has_status_effect(cond_effect_data["if_target_has"]):
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
            self._handle_splash_damage(self.pos, game_state, all_enemies)

        for area_effect_data in self.on_hit_area_effects:
            if random.random() <= area_effect_data["chance"]:
                self._handle_area_effect(self.pos, area_effect_data, all_enemies)

        if self.pierce_count > 0:
            self.pierce_count -= 1
            new_target = self._find_next_pierce_target(all_enemies)
            if new_target:
                self.target = new_target
                return

        self.kill()

    def _handle_splash_damage(
        self,
        impact_pos: pygame.Vector2,
        game_state: "GameState",
        all_enemies: List["Enemy"],
    ):
        """Applies damage and effects to all enemies within the blast radius."""
        splash_damage = int(self.damage * 0.5)
        for enemy in all_enemies:
            if enemy.is_alive and enemy.entity_id not in self.enemies_hit:
                if impact_pos.distance_to(enemy.pos) <= self.blast_radius:
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
        all_enemies: List["Enemy"],
    ):
        """Handles generic area of effect abilities like frost nova."""
        radius = area_effect_data["radius"]
        damage = area_effect_data["damage"]
        effect_def = area_effect_data.get("effect")

        for enemy in all_enemies:
            if enemy.is_alive and center_pos.distance_to(enemy.pos) <= radius:
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
