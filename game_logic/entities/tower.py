# game_logic/entities/tower.py
import pygame
import logging
import uuid
import random
import math
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Callable

from .entity import Entity
from ..attacks import attack_handlers

if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from ..game_state import GameState
    from .entity import Entity


logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a universal, data-driven defensive tower.

    REFACTORED: This class is now a full citizen of the universal EffectHandler
    system inherited from Entity. It distinguishes between permanent 'base' stats
    (modified by upgrades) and temporary 'live' stats (modified by buffs),
    allowing it to be affected by friendly support towers.
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

        self.tower_type_id = tower_type_id
        self.name = tower_type_data.get("name", "Unknown Tower")
        self.cost = tower_type_data.get("cost", 0)
        self.status_effects_config = status_effects_config
        self.attack_data = tower_type_data.get("attack", {})

        attack_specific_data = self.attack_data.get("data", {})

        # --- Base vs. Dynamic Stats for Buffs ---
        self.base_damage = attack_specific_data.get("damage", 0)
        self.base_range = attack_specific_data.get("range", 100)
        self.base_fire_rate = attack_specific_data.get("fire_rate", 1.0)

        self.damage = self.base_damage
        self.range = self.base_range
        self.fire_rate = self.base_fire_rate

        self.blast_radius = attack_specific_data.get("blast_radius", 0)

        self.path_a_tier = 0
        self.path_b_tier = 0
        self.total_investment: int = self.cost
        self.fire_cooldown = 0.0
        self.current_targets: List["Enemy"] = []

        # --- Attributes Modified by Upgrades ---
        self.projectiles_per_shot = 1
        self.pierce_count = 0
        self.armor_shred = 0
        self.execute_threshold: Optional[Dict[str, float]] = None
        self.on_apply_damage = 0
        self.on_death_explosion: Optional[Dict[str, Any]] = None

        # --- NEW: Add base and live stats for Arch-Mage buffs ---
        self.base_effect_potency_multiplier = 1.0
        self.effect_potency_multiplier = self.base_effect_potency_multiplier
        self.base_aura_size_multiplier = 1.0
        self.aura_size_multiplier = self.base_aura_size_multiplier

        self.on_hit_effects: List[Dict[str, Any]] = []
        self.on_blast_effects: List[Dict[str, Any]] = []
        self.bonus_damage_per_debuff = 0
        self.conditional_effects: List[Dict[str, Any]] = []
        self.on_hit_area_effects: List[Dict[str, Any]] = []

        self._attack_handlers: Dict[
            str, Callable[["Tower", "Enemy"], List["Entity"]]
        ] = {
            "standard_projectile": attack_handlers.create_standard_projectile,
            "persistent_ground_aura": attack_handlers.create_persistent_ground_aura,
            "persistent_attached_aura": attack_handlers.create_persistent_attached_aura,
        }

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
        self,
        dt: float,
        game_state: "GameState",
        all_enemies: List["Entity"],
        all_towers: List["Entity"],
    ) -> List["Entity"]:
        """
        Updates the tower's logic, finds targets, and fires.
        """
        super().update(dt, game_state, all_enemies, all_towers)

        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        self._find_new_targets(all_enemies)

        if self.current_targets and self.fire_cooldown <= 0:
            return self._fire()
        return []

    def _find_new_targets(self, enemies: List["Entity"]):
        """Finds all valid targets within the tower's range."""
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
        """Executes the tower's attack by delegating to a specialized handler."""
        if not self.current_targets:
            return []

        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")

        attack_type = self.attack_data.get("type")
        if not attack_type:
            logger.error(f"Tower '{self.name}' has no 'type' defined.")
            return []

        handler = self._attack_handlers.get(attack_type)
        if not handler:
            logger.error(f"No attack handler found for type: '{attack_type}'")
            return []

        primary_target = self.current_targets[0]
        attack_entities = handler(self, primary_target)

        logger.debug(
            f"Tower '{self.name}' fired using handler '{attack_type}', creating {len(attack_entities)} entities."
        )
        return attack_entities
