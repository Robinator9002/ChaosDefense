# game_logic/entities/tower.py
import pygame
import logging
import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from .entity import Entity
from .projectile import Projectile
from ..effects.status_effect import StatusEffect

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    # The Enemy class is now in a subfolder, so we adjust the import path.
    from .enemies.enemy import Enemy
    from ..game_state import GameState

logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a defensive tower that can target and attack enemies.

    This class has been reworked to correctly pass all necessary upgrade
    information (e.g., source_id for effects, armor_shred, execute thresholds)
    down to the projectiles it creates.
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

        # --- Firing and Targeting State ---
        self.fire_cooldown = 0.0
        self.target: Optional[Enemy] = None

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

        # Load any innate effects from the tower's base definition.
        initial_effects = tower_type_data.get("effects")
        if initial_effects:
            for effect_id, params in initial_effects.items():
                self.on_hit_effects.append({"id": effect_id, **params})

        # --- Create Sprite ---
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
        Updates the tower's logic. Main responsibilities include managing fire
        cooldown, acquiring a target, and firing projectiles.
        """
        super().update(dt, game_state)
        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        if self.target and (
            not self.target.is_alive or self.get_distance_to(self.target) > self.range
        ):
            self.target = None

        if not self.target:
            self.target = self._find_new_target(enemies)

        if self.target and self.fire_cooldown <= 0:
            return self._fire_at_target()
        return []

    def _find_new_target(self, enemies: List["Enemy"]) -> Optional["Enemy"]:
        """Finds the best target from the list of enemies, based on proximity."""
        closest_enemy: Optional["Enemy"] = None
        min_distance = float("inf")
        for enemy in enemies:
            if enemy.is_alive:
                distance = self.get_distance_to(enemy)
                if distance <= self.range and distance < min_distance:
                    min_distance = distance
                    closest_enemy = enemy
        return closest_enemy

    def _fire_at_target(self) -> List[Projectile]:
        """
        Creates and returns a list of projectiles aimed at the current target.
        This is the critical point where all upgrade data is bundled up and
        passed to the new projectile instances.
        """
        if not self.target:
            return []

        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")

        projectiles = []
        for _ in range(self.projectiles_per_shot):
            # --- Create StatusEffect instances for the projectile ---
            effect_instances = []
            for effect_data in self.on_hit_effects:
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
                            # This is the crucial link for on-death effects.
                            source_entity_id=self.entity_id,
                        )
                    )

            # --- Create and return the projectile ---
            new_projectile = Projectile(
                x=self.pos.x,
                y=self.pos.y,
                damage=self.damage,
                target=self.target,
                effects_to_apply=effect_instances,
                pierce_count=self.pierce_count,
                blast_radius=self.blast_radius,
                on_blast_effects_data=self.on_blast_effects,
                status_effects_config=self.status_effects_config,
                # Pass all other direct-damage upgrade effects
                armor_shred=self.armor_shred,
                execute_threshold=self.execute_threshold,
                on_apply_damage=self.on_apply_damage,
            )
            projectiles.append(new_projectile)
        return projectiles
