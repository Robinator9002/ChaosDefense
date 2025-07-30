# game_logic/effects/effect_handler.py
import logging
from typing import List, TYPE_CHECKING, Any, Dict

# Import the StatusEffect class which this handler will manage.
from .status_effect import StatusEffect

if TYPE_CHECKING:
    # Import Entity for type hinting the owner, preventing circular imports.
    from ..entities.entity import Entity

logger = logging.getLogger(__name__)


class EffectHandler:
    """
    A universal, component-based engine for managing status effects.

    This class encapsulates all logic for applying, updating, and calculating
    the stat modifications from a list of active status effects (both buffs
    and debuffs). An instance of this handler is owned by the base Entity
    class, granting this functionality to every tower and enemy in the game
    without code duplication.
    """

    def __init__(self, owner: "Entity"):
        """
        Initializes the EffectHandler.

        Args:
            owner (Entity): The entity instance that this handler belongs to.
                            This is crucial for accessing and modifying the
                            entity's stats.
        """
        self.owner = owner
        self.status_effects: List[StatusEffect] = []

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the owner entity, handling immunities
        and stacking logic.

        Args:
            new_effect (StatusEffect): The new effect instance to apply.
        """
        # Use getattr to safely check for immunities, as not all entities
        # (like projectiles) will have this attribute.
        immunities = getattr(self.owner, "immunities", [])
        if new_effect.effect_id in immunities:
            logger.debug(
                f"Entity {self.owner.entity_id} resisted effect '{new_effect.effect_id}' due to immunity."
            )
            return

        # Check for an existing effect of the same type to apply stacking logic.
        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                existing_effect.stack_with(new_effect)
                return

        # If no existing effect is found, add the new one to the list.
        self.status_effects.append(new_effect)

    def update(self, dt: float):
        """
        Updates all active status effects, ticking down their durations and
        applying any damage-over-time effects. This method should be called
        every frame from the owner entity's update loop.

        Args:
            dt (float): The time elapsed since the last frame.
        """
        if not self.status_effects:
            return

        # Iterate backwards to safely remove expired effects during the loop.
        for i in range(len(self.status_effects) - 1, -1, -1):
            effect = self.status_effects[i]
            dot_damage = effect.update(dt)

            if dot_damage > 0:
                # The owner is expected to have a take_damage method.
                self.owner.take_damage(dot_damage, ignores_armor=True)

            if not effect.is_active:
                self.status_effects.pop(i)

        # After updating durations, recalculate the owner's final stats.
        self.apply_stat_modifiers()

    def apply_stat_modifiers(self):
        """
        Calculates the owner's final stats for the current frame.

        This is the core of the buff/debuff system. It first resets the
        owner's dynamic stats to their permanent "base" values, then iterates
        through all active effects, reapplying their modifications. This
        ensures that buffs and debuffs are temporary and correctly calculated
        each frame.
        """
        # --- Reset all dynamic stats to their base values ---
        # We use getattr with a default to safely handle stats that might
        # not exist on every entity type.
        self.owner.damage = getattr(self.owner, "base_damage", self.owner.damage)
        self.owner.range = getattr(self.owner, "base_range", self.owner.range)
        self.owner.fire_rate = getattr(
            self.owner, "base_fire_rate", self.owner.fire_rate
        )
        self.owner.speed = getattr(self.owner, "base_speed", self.owner.speed)
        self.owner.armor = getattr(self.owner, "base_armor", self.owner.armor)
        self.owner.damage_taken_multiplier = 1.0

        # --- Re-apply all active modifiers from status effects ---
        for effect in self.status_effects:
            if effect.effect_type == "stat_modifier":
                stat = effect.stat_to_modify
                # Use hasattr to ensure we only modify stats that the owner actually possesses.
                if hasattr(self.owner, stat):
                    current_value = getattr(self.owner, stat)
                    setattr(self.owner, stat, current_value * effect.potency)

            elif effect.effect_type == "stat_debuff":
                stat = effect.stat_to_modify
                if hasattr(self.owner, stat):
                    current_value = getattr(self.owner, stat)
                    setattr(self.owner, stat, current_value - effect.potency)
