# game_logic/entities/tower.py
import pygame
import logging
import uuid
import random
import math
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from .entity import Entity

# --- MODIFIED: Update imports for the new projectile structure ---
# We now import the refactored Projectile class from its new home and the
# ProjectileData DTO that defines the contract between Tower and Projectile.
from .projectiles.projectile import Projectile
from .projectiles.projectile_data import ProjectileData
from ..effects.status_effect import StatusEffect

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from ..game_state import GameState

logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a defensive tower that can target and attack enemies.
    It now creates projectiles by assembling a ProjectileData object,
    decoupling it from the projectile's implementation details.
    """

    def __init__(
        self,
        x: float,
        y: float,
        tile_size: int,
        tower_type_id: str,
        tower_type_data: Dict[str, Any],
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new Tower entity.
        """
        super().__init__(x, y, max_hp=100)

        # --- Core Tower Identification & Base Stats ---
        self.tower_type_id = tower_type_id
        self.name = tower_type_data.get("name", "Unknown Tower")
        self.cost = tower_type_data.get("cost", 0)
        self.damage = tower_type_data.get("damage", 0)
        self.range = tower_type_data.get("range", 100)
        self.fire_rate = tower_type_data.get("fire_rate", 1.0)
        self.blast_radius = tower_type_data.get("blast_radius", 0)
        self.status_effects_config = status_effects_config

        # --- Upgrade State Tracking ---
        self.path_a_tier = 0
        self.path_b_tier = 0
        self.total_investment: int = self.cost

        # --- Firing and Targeting State ---
        self.fire_cooldown = 0.0
        self.current_targets: List[Enemy] = []

        # --- Attributes Modified by Upgrades ---
        self.projectiles_per_shot = 1
        self.pierce_count = 0
        self.armor_shred = 0
        self.execute_threshold: Optional[Dict[str, float]] = None
        self.on_apply_damage = 0
        self.on_death_explosion: Optional[Dict[str, Any]] = None
        self.base_effect_duration_multiplier = 1.0
        self.base_effect_potency_multiplier = 1.0
        self.on_hit_effects: List[Dict[str, Any]] = []
        self.on_blast_effects: List[Dict[str, Any]] = []
        self.bonus_damage_per_debuff = 0
        self.conditional_effects: List[Dict[str, Any]] = []
        self.on_hit_area_effects: List[Dict[str, Any]] = []

        initial_effects = tower_type_data.get("effects")
        if initial_effects:
            for effect_id, params in initial_effects.items():
                self.on_hit_effects.append({"id": effect_id, **params})

        self.sprite = self._create_sprite(tile_size, tower_type_data)
        self.rect = self.sprite.get_rect(center=self.pos)
        logger.info(f"Created Level 1 {self.name} ({self.entity_id}).")

    def _create_sprite(
        self, tile_size: int, tower_data: Dict[str, Any]
    ) -> pygame.Surface:
        """Creates the visual representation for the placed tower."""
        sprite = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        color = tower_data.get("placeholder_color", (128, 128, 128))
        pygame.draw.rect(
            sprite, color, (2, 2, tile_size - 4, tile_size - 4), border_radius=4
        )
        pygame.draw.circle(sprite, (200, 200, 220), (tile_size // 2, tile_size // 2), 6)
        return sprite

    def update(
        self, dt: float, game_state: "GameState", enemies: List["Enemy"]
    ) -> List[Projectile]:
        """
        Updates the tower's logic, finds targets, and fires projectiles.
        """
        super().update(dt, game_state)
        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        self._find_new_targets(enemies)

        if self.current_targets and self.fire_cooldown <= 0:
            return self._fire()
        return []

    def _find_new_targets(self, enemies: List["Enemy"]):
        """
        Finds all valid targets within the tower's range.
        """
        self.current_targets.clear()
        potential_targets = []
        for enemy in enemies:
            if enemy.is_alive:
                distance = self.get_distance_to(enemy)
                if distance <= self.range:
                    potential_targets.append((distance, enemy))

        potential_targets.sort(key=lambda t: t[0])
        self.current_targets = [enemy for distance, enemy in potential_targets]

    def _fire(self) -> List[Projectile]:
        """
        Creates and returns a list of projectiles aimed at the current target(s).
        This method now assembles a ProjectileData object to create projectiles.
        """
        if not self.current_targets:
            return []

        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")

        projectiles_to_fire = []
        num_shots = self.projectiles_per_shot

        # --- REFACTORED: Assemble the ProjectileData "work order" once ---
        # First, create all status effect instances that will be applied.
        effect_instances = []
        for effect_data in self.on_hit_effects:
            if random.random() <= effect_data.get("chance", 1.0):
                effect_id = effect_data["id"]
                if effect_id in self.status_effects_config:
                    effect_definition = self.status_effects_config[effect_id]
                    effect_instances.append(
                        StatusEffect(
                            effect_id=effect_id,
                            effect_data=effect_definition,
                            duration=effect_data.get("duration", 1.0)
                            * self.base_effect_duration_multiplier,
                            potency=effect_data.get("potency", 1.0)
                            * self.base_effect_potency_multiplier,
                            source_entity_id=self.entity_id,
                        )
                    )

        # Now, create the single, clean data object.
        projectile_payload = ProjectileData(
            damage=self.damage,
            effects_to_apply=effect_instances,
            status_effects_config=self.status_effects_config,
            pierce_count=self.pierce_count,
            blast_radius=self.blast_radius,
            armor_shred=self.armor_shred,
            on_blast_effects_data=self.on_blast_effects,
            conditional_effects=self.conditional_effects,
            on_hit_area_effects=self.on_hit_area_effects,
            execute_threshold=self.execute_threshold,
            on_apply_damage=self.on_apply_damage,
            bonus_damage_per_debuff=self.bonus_damage_per_debuff,
        )

        for i in range(num_shots):
            target = self.current_targets[i % len(self.current_targets)]
            origin_pos = self.pos.copy()

            # Handle spread for multi-shot attacks
            if num_shots > 1:
                spread_angle_deg = 15
                angle_offset = ((i / (num_shots - 1)) - 0.5) * spread_angle_deg * 2
                direction_to_target = target.pos - self.pos
                base_angle_rad = math.atan2(
                    direction_to_target.y, direction_to_target.x
                )
                offset_angle_rad = base_angle_rad + math.radians(angle_offset)
                offset_distance = 8
                origin_pos.x += offset_distance * math.cos(offset_angle_rad)
                origin_pos.y += offset_distance * math.sin(offset_angle_rad)

            # --- REFACTORED: Use the new, clean constructor ---
            new_projectile = Projectile(
                x=origin_pos.x,
                y=origin_pos.y,
                target=target,
                data=projectile_payload,  # Pass the single data object
            )
            projectiles_to_fire.append(new_projectile)

        return projectiles_to_fire
