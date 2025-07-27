# game_logic/entities/tower.py
import pygame
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from .entity import Entity
from .projectile import Projectile
from ..effects.status_effect import StatusEffect

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a defensive tower that can target and attack enemies.

    This class has been significantly updated to support a complex, path-based
    upgrade system. Each tower instance now tracks its own stats, upgrade tiers,
    and a variety of special abilities that can be unlocked, such as piercing
    projectiles, multi-shot capabilities, and on-hit status effects.
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

        Args:
            x (float): The pixel x-coordinate of the tower's center.
            y (float): The pixel y-coordinate of the tower's center.
            tile_size (int): The size of a game tile in pixels.
            tower_type_id (str): The unique identifier for the tower type (e.g., "turret").
            tower_type_data (Dict[str, Any]): The configuration data for this tower type.
            status_effects_config (Dict[str, Any]): The global definitions for all status effects.
        """
        # Initialize the base Entity first.
        super().__init__(x, y, max_hp=100)

        # --- Core Tower Identification & Base Stats ---
        self.tower_type_id = tower_type_id
        self.name = tower_type_data.get("name", "Unknown Tower")
        self.cost = tower_type_data.get("cost", 0)
        self.damage = tower_type_data.get("damage", 0)
        self.range = tower_type_data.get("range", 100)
        self.fire_rate = tower_type_data.get("fire_rate", 1.0)
        self.blast_radius = tower_type_data.get("blast_radius", 0)  # For splash damage
        self.status_effects_config = status_effects_config

        # --- Upgrade State Tracking ---
        self.path_a_tier = 0
        self.path_b_tier = 0

        # --- Firing and Targeting State ---
        self.fire_cooldown = 0.0
        self.target: Optional[Enemy] = None

        # --- Attributes Modified by Upgrades ---
        # These are initialized to their default values and will be changed
        # by the UpgradeManager when an upgrade is applied.
        self.projectiles_per_shot = 1
        self.pierce_count = 0
        self.armor_shred = 0
        self.execute_threshold: Optional[Dict[str, float]] = None
        self.on_apply_damage = 0
        self.on_death_explosion: Optional[Dict[str, Any]] = None

        # Multipliers for effects applied by this tower (e.g., for Frost Tower upgrades)
        self.base_effect_duration_multiplier = 1.0
        self.base_effect_potency_multiplier = 1.0

        # Lists to hold effect data dictionaries to be applied by projectiles/explosions.
        # Format: [{"id": "slow", "potency": 0.4, "duration": 2.0}, ...]
        self.on_hit_effects: List[Dict[str, Any]] = []
        self.on_blast_effects: List[Dict[str, Any]] = []

        # Load any innate effects from the tower's base definition (e.g., Frost Tower's slow)
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

        Returns:
            A list of new Projectile objects if the tower fired, otherwise an empty list.
        """
        super().update(dt, game_state)

        # Tick down the fire cooldown timer.
        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        # Re-evaluate the current target to ensure it's still valid.
        if self.target and (
            not self.target.is_alive or self.get_distance_to(self.target) > self.range
        ):
            self.target = None

        # If there's no valid target, try to find a new one.
        if not self.target:
            self.target = self._find_new_target(enemies)

        # If a valid target exists and the tower is ready to fire, call _fire_at_target.
        if self.target and self.fire_cooldown <= 0:
            return self._fire_at_target()

        return []

    def _find_new_target(self, enemies: List["Enemy"]) -> Optional["Enemy"]:
        """Finds the best target from the list of enemies, based on proximity."""
        # This logic can be replaced by a Strategy pattern in the future for more
        # complex targeting (e.g., strongest, weakest, first, last).
        closest_enemy: Optional["Enemy"] = None
        min_distance = float("inf")
        for enemy in enemies:
            distance = self.get_distance_to(enemy)
            if distance <= self.range and distance < min_distance:
                min_distance = distance
                closest_enemy = enemy
        return closest_enemy

    def _fire_at_target(self) -> List[Projectile]:
        """
        Creates and returns a list of projectiles aimed at the current target.
        This method now supports multi-shot and constructs projectiles with all
        necessary stats and effects based on the tower's current upgrades.
        """
        if not self.target:
            return []

        # Reset the fire cooldown based on the tower's fire rate.
        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")  # A fire rate of 0 means it never fires.

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
            )
            projectiles.append(new_projectile)

        return projectiles
