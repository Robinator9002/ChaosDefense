# game_logic/entities/tower.py
import pygame
import logging
import uuid
import random
import math
import copy
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Callable

from .entity import Entity
from ..attacks import attack_handlers

if TYPE_CHECKING:
    from .enemies.enemy import Enemy
    from ..game_state import GameState
    from ..game_ai.targeting.targeting_manager import TargetingManager


logger = logging.getLogger(__name__)


class Tower(Entity):
    """
    Represents a universal, data-driven defensive tower. Its stats and behaviors
    are defined by configuration data, and this class brings them to life.

    REFACTORED: No longer uses a static list of available personas. Instead,
    it can dynamically determine which personas are eligible based on its
    current abilities (e.g., having a blast radius makes 'ARTILLERY' eligible).
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

        # --- Core Identifiers & Data ---
        self.tower_type_id = tower_type_id
        self.name = tower_type_data.get("name", "Unknown Tower")
        self.cost = tower_type_data.get("cost", 0)
        self.status_effects_config = status_effects_config

        self.attack = copy.deepcopy(tower_type_data.get("attack", {}))
        self.auras = copy.deepcopy(tower_type_data.get("auras", []))

        self.attack.setdefault("data", {})

        # --- Targeting & AI ---
        # --- REFACTORED: Removed static persona list. ---
        # The default persona is now hard-coded as a fallback. The UI and
        # dynamic eligibility system will handle the actual logic.
        self.current_persona = "EXECUTIONER"
        self.current_targets: List["Enemy"] = []

        # --- State & Cooldowns ---
        self.fire_cooldown = 0.0
        self.total_investment: int = self.cost

        # --- Upgrade Progression ---
        self.path_a_tier = 0
        self.path_b_tier = 0

        # --- Base Stats Initialization ---
        self.base_damage = self.damage
        self.base_range = self.range
        self.base_fire_rate = self.fire_rate
        self.base_blast_radius = self.blast_radius
        self.base_effect_potency_multiplier = 1.0
        self.base_aura_size_multiplier = 1.0

        # --- Live Stats (Managed by EffectHandler) ---
        self.effect_potency_multiplier = self.base_effect_potency_multiplier
        self.aura_size_multiplier = self.base_aura_size_multiplier

        # --- Special Properties (Modified by Upgrades) ---
        self.projectiles_per_shot = 1
        self.pierce_count = 0
        self.armor_shred = 0
        self.execute_threshold: Optional[Dict[str, float]] = None
        self.on_apply_damage = 0
        self.on_death_explosion: Optional[Dict[str, Any]] = None
        self.bonus_damage_per_debuff = 0
        self.conditional_effects: List[Dict[str, Any]] = []
        self.on_hit_area_effects: List[Dict[str, Any]] = []
        self.on_hit_effects: List[Dict[str, Any]] = []
        self.on_blast_effects: List[Dict[str, Any]] = []

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

    @property
    def damage(self) -> float:
        return self.attack["data"].get("damage", 0)

    @damage.setter
    def damage(self, value: float):
        self.attack["data"]["damage"] = value

    @property
    def range(self) -> float:
        return self.attack["data"].get("range", 0)

    @range.setter
    def range(self, value: float):
        self.attack["data"]["range"] = value

    @property
    def fire_rate(self) -> float:
        return self.attack["data"].get("fire_rate", 0)

    @fire_rate.setter
    def fire_rate(self, value: float):
        self.attack["data"]["fire_rate"] = value

    @property
    def blast_radius(self) -> float:
        return self.attack["data"].get("blast_radius", 0)

    @blast_radius.setter
    def blast_radius(self, value: float):
        self.attack["data"]["blast_radius"] = value

    @property
    def effects(self) -> Dict[str, Any]:
        """Provides clean access to the on-hit effects dictionary."""
        return self.attack["data"].get("effects", {})

    def _create_sprite(
        self, tile_size: int, tower_data: Dict[str, Any]
    ) -> pygame.Surface:
        sprite = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        color = tower_data.get("placeholder_color", (128, 128, 128))
        pygame.draw.rect(
            sprite, color, (2, 2, tile_size - 4, tile_size - 4), border_radius=4
        )
        pygame.draw.circle(sprite, (200, 200, 220), (tile_size // 2, tile_size // 2), 6)
        return sprite

    def update(
        self, dt: float, game_state: "GameState", targeting_manager: "TargetingManager"
    ) -> List["Entity"]:
        super().update(dt, game_state, targeting_manager)

        if not self.attack.get("type"):
            return []

        if self.fire_cooldown > 0:
            self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        self._find_new_targets(targeting_manager)

        if self.current_targets and self.fire_cooldown <= 0:
            return self._fire()
        return []

    def get_eligible_personas(self, all_personas_config: Dict[str, Any]) -> List[str]:
        """
        Dynamically determines which AI personas are valid for this tower
        based on its current, fully-upgraded state.
        """
        eligible = []
        for persona_id in all_personas_config.keys():
            if persona_id == "ARTILLERY":
                # Eligible if the tower has any area-of-effect capability.
                if self.blast_radius > 0:
                    eligible.append(persona_id)
            elif persona_id == "CONTAGION":
                # Eligible if the tower can apply any status effect. This checks
                # base effects and effects added by upgrades.
                has_debuffs = (
                    len(self.attack.get("data", {}).get("effects", {})) > 0
                    or len(self.on_hit_effects) > 0
                    or len(self.on_blast_effects) > 0
                )
                if has_debuffs:
                    eligible.append(persona_id)
            else:
                # All other personas are considered universally applicable.
                eligible.append(persona_id)
        return eligible

    def set_persona(self, new_persona_id: str):
        """
        Sets the tower's current targeting persona. The UI is responsible for
        ensuring the requested persona is eligible before calling this.
        """
        self.current_persona = new_persona_id
        logger.info(f"Tower {self.entity_id} changed persona to '{new_persona_id}'.")

    def _find_new_targets(self, targeting_manager: "TargetingManager"):
        potential_targets = targeting_manager.get_nearby_enemies(self.pos, self.range)

        if not potential_targets:
            self.current_targets = []
            return

        self.current_targets = targeting_manager.sort_targets(
            potential_targets, self, self.current_persona
        )

    def _fire(self) -> List["Entity"]:
        if not self.current_targets:
            return []

        if self.fire_rate > 0:
            self.fire_cooldown = 1.0 / self.fire_rate
        else:
            self.fire_cooldown = float("inf")

        attack_type = self.attack.get("type")
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
