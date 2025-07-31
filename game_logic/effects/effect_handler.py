# game_logic/effects/effect_handler.py
import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.entity import Entity
    from .status_effect import StatusEffect

logger = logging.getLogger(__name__)


class EffectHandler:
    """
    Manages all status effects on a single entity. It is responsible for
    applying effects, updating their durations, and calculating the final
    modified stats for the entity each frame.
    """

    def __init__(self, owner: "Entity"):
        """
        Initializes the EffectHandler.
        Args:
            owner (Entity): The entity instance that this handler belongs to.
        """
        self.owner = owner
        self.status_effects: List["StatusEffect"] = []

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the owner. If an effect of the same type
        already exists, it will either stack or refresh based on the effect's data.
        """
        # Simple implementation: for now, we just add the effect.
        # A more complex system would handle stacking/refreshing here.
        self.status_effects.append(new_effect)

    def update(self, dt: float):
        """
        Updates all active status effects, removing any that have expired.
        Then, recalculates all of the owner's stats based on the remaining effects.
        """
        # Tick down duration and remove expired effects
        self.status_effects = [
            effect for effect in self.status_effects if effect.update(dt)
        ]
        # Recalculate all stats from scratch
        self.apply_stat_modifiers()

    def apply_stat_modifiers(self):
        """
        Resets the owner's stats to their base values and then applies all
        modifiers from currently active status effects.

        --- FIX ---
        This function now uses `hasattr` to check if the owner (e.g., Enemy)
        actually has a stat (e.g., 'damage') before trying to modify it. This
        prevents crashes when effects are applied to entities that don't have
        the full set of tower-like attributes.
        """
        # --- Step 1: Reset all modifiable stats to their base values ---
        # This prevents modifiers from stacking frame-over-frame.

        # Tower-specific stats
        if hasattr(self.owner, "base_damage"):
            self.owner.damage = self.owner.base_damage
        if hasattr(self.owner, "base_range"):
            self.owner.range = self.owner.base_range
        if hasattr(self.owner, "base_fire_rate"):
            self.owner.fire_rate = self.owner.base_fire_rate
        if hasattr(self.owner, "base_effect_potency_multiplier"):
            self.owner.effect_potency_multiplier = (
                self.owner.base_effect_potency_multiplier
            )
        if hasattr(self.owner, "base_aura_size_multiplier"):
            self.owner.aura_size_multiplier = self.owner.base_aura_size_multiplier

        # Enemy-specific stats
        if hasattr(self.owner, "base_speed"):
            self.owner.speed = self.owner.base_speed
        if hasattr(self.owner, "base_armor"):
            self.owner.armor = self.owner.base_armor

        # --- Step 2: Apply all active modifiers ---
        for effect in self.status_effects:
            for modifier in effect.modifiers:
                stat = modifier["stat"]
                op = modifier["operation"]
                value = modifier["value"]

                # Again, check if the owner has the stat before modifying
                if hasattr(self.owner, stat):
                    current_value = getattr(self.owner, stat)
                    if op == "add":
                        setattr(self.owner, stat, current_value + value)
                    elif op == "multiply":
                        setattr(self.owner, stat, current_value * value)

        # Ensure stats don't fall below reasonable minimums
        if hasattr(self.owner, "speed"):
            self.owner.speed = max(
                5, self.owner.speed
            )  # Prevent enemies from stopping completely unless stunned
