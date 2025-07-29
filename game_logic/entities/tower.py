# game_logic/entities/tower.py
import pygame
import logging
import uuid
import random
import math
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Callable

from .entity import Entity

# --- REFACTORED: Import the attack handler module ---
# This module contains the factory functions for creating different attack types.
from ..attacks import attack_handlers

# Use TYPE_CHECKING to avoid circular imports at runtime.
if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from ..game_state import GameState

    # We need to import Entity here for the return type hint of _fire
    from .entity import Entity


logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a universal, data-driven defensive tower.

    This class is now a generic platform for any type of attack. Its behavior
    is determined entirely by the 'attack' object in its configuration data.
    It uses a handler-based system to delegate the creation of specific attack
    entities (projectiles, auras, etc.), making it completely agnostic to the
    mechanics of how it attacks. This allows for extreme modularity and easy
    creation of new, unique tower types purely through JSON configuration.
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
        Initializes a new Tower entity based on its configuration data.
        """
        super().__init__(x, y, max_hp=100)

        # --- Core Tower Identification & Configuration ---
        self.tower_type_id = tower_type_id
        self.name = tower_type_data.get("name", "Unknown Tower")
        self.cost = tower_type_data.get("cost", 0)
        self.status_effects_config = status_effects_config

        # --- REFACTORED: The Attack Behavior System ---
        # The tower stores its entire attack configuration.
        self.attack_data = tower_type_data.get("attack", {})
        attack_specific_data = self.attack_data.get("data", {})

        # The tower's own stats are initialized from the attack data. This is
        # crucial because it allows the existing UpgradeManager and its
        # effect_applicators to modify these attributes directly, which in turn
        # are read by the attack handlers.
        self.damage = attack_specific_data.get("damage", 0)
        self.range = attack_specific_data.get("range", 100)
        self.fire_rate = attack_specific_data.get("fire_rate", 1.0)
        self.blast_radius = attack_specific_data.get("blast_radius", 0)

        # --- Upgrade State Tracking ---
        self.path_a_tier = 0
        self.path_b_tier = 0
        self.total_investment: int = self.cost

        # --- Firing and Targeting State ---
        self.fire_cooldown = 0.0
        self.current_targets: List["Enemy"] = []

        # --- Attributes Modified by Upgrades (initialized to defaults) ---
        # These are initialized here so the upgrade system has attributes to modify.
        # Their values are then passed to the attack handlers.
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

        # --- NEW: Attack Handler Dispatch Table ---
        # This dictionary maps the 'type' string from the attack config to the
        # actual factory function that creates the attack.
        self._attack_handlers: Dict[
            str, Callable[["Tower", "Enemy"], List["Entity"]]
        ] = {
            "standard_projectile": attack_handlers.create_standard_projectile,
            "persistent_ground_aura": attack_handlers.create_persistent_ground_aura,
            "persistent_attached_aura": attack_handlers.create_persistent_attached_aura,
        }

        # --- Visuals ---
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
    ) -> List["Entity"]:
        """
        Updates the tower's logic, finds targets, and fires by delegating
        to the appropriate attack handler.
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
        (This logic remains unchanged, but is now more critical than ever).
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

    def _fire(self) -> List["Entity"]:
        """
        Executes the tower's attack by delegating to a specialized handler.

        This method is the core of the Attack Behavior pattern. It reads the
        attack type from its configuration and uses the dispatch table to call
        the correct factory function, making the tower itself independent of
        the attack's implementation.
        """
        if not self.current_targets:
            return []

        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            # A fire rate of 0 or less means the tower does not fire automatically.
            self.fire_cooldown = float("inf")

        # 1. Get the attack type string from the config (e.g., "standard_projectile").
        attack_type = self.attack_data.get("type")
        if not attack_type:
            logger.error(
                f"Tower '{self.name}' has no 'type' defined in its attack data."
            )
            return []

        # 2. Look up the corresponding handler function in our dispatch table.
        handler = self._attack_handlers.get(attack_type)
        if not handler:
            logger.error(f"No attack handler found for type: '{attack_type}'")
            return []

        # 3. Delegate the creation of the attack entity to the handler.
        # The handler is responsible for reading all necessary data from the tower.
        primary_target = self.current_targets[0]
        attack_entities = handler(self, primary_target)

        logger.debug(
            f"Tower '{self.name}' fired using handler '{attack_type}', creating {len(attack_entities)} entities."
        )

        # 4. Return the list of entities (projectiles, auras, etc.) to be added to the game.
        return attack_entities
