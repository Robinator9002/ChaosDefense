# game_logic/effects/effect_handler.py
import logging
from typing import List, TYPE_CHECKING, Any, Dict

from .status_effect import StatusEffect

if TYPE_CHECKING:
    from ..entities.entity import Entity

logger = logging.getLogger(__name__)


class EffectHandler:
    """
    A universal, component-based engine for managing status effects.

    REFACTORED: This handler has been upgraded to manage new, esoteric stats
    required for advanced support towers like the Arch-Mage, such as effect
    potency and aura size multipliers.
    """

    def __init__(self, owner: "Entity"):
        """
        Initializes the EffectHandler.
        """
        self.owner = owner
        self.status_effects: List[StatusEffect] = []

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the owner entity.
        """
        immunities = getattr(self.owner, "immunities", [])
        if new_effect.effect_id in immunities:
            logger.debug(
                f"Entity {self.owner.entity_id} resisted effect '{new_effect.effect_id}' due to immunity."
            )
            return

        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                existing_effect.stack_with(new_effect)
                return

        self.status_effects.append(new_effect)

    def update(self, dt: float):
        """
        Updates all active status effects and recalculates owner stats.
        """
        if not self.status_effects:
            return

        for i in range(len(self.status_effects) - 1, -1, -1):
            effect = self.status_effects[i]
            dot_damage = effect.update(dt)

            if dot_damage > 0:
                self.owner.take_damage(dot_damage, ignores_armor=True)

            if not effect.is_active:
                self.status_effects.pop(i)

        self.apply_stat_modifiers()

    def apply_stat_modifiers(self):
        """
        Calculates the owner's final stats for the current frame by resetting
        to base values and reapplying all active effect modifiers.
        """
        # --- Reset all dynamic stats to their base values ---
        self.owner.damage = getattr(self.owner, "base_damage", self.owner.damage)
        self.owner.range = getattr(self.owner, "base_range", self.owner.range)
        self.owner.fire_rate = getattr(
            self.owner, "base_fire_rate", self.owner.fire_rate
        )
        self.owner.speed = getattr(self.owner, "base_speed", self.owner.speed)
        self.owner.armor = getattr(self.owner, "base_armor", self.owner.armor)
        self.owner.damage_taken_multiplier = 1.0
        # --- NEW: Reset esoteric stats for the Arch-Mage buffs ---
        self.owner.effect_potency_multiplier = getattr(
            self.owner, "base_effect_potency_multiplier", 1.0
        )
        self.owner.aura_size_multiplier = getattr(
            self.owner, "base_aura_size_multiplier", 1.0
        )

        # --- Re-apply all active modifiers from status effects ---
        for effect in self.status_effects:
            if effect.effect_type == "stat_modifier":
                stat = effect.stat_to_modify
                if hasattr(self.owner, stat):
                    current_value = getattr(self.owner, stat)
                    setattr(self.owner, stat, current_value * effect.potency)

            elif effect.effect_type == "stat_debuff":
                stat = effect.stat_to_modify
                if hasattr(self.owner, stat):
                    current_value = getattr(self.owner, stat)
                    setattr(self.owner, stat, current_value - effect.potency)
