# game_logic/effects/effect_handler.py
import logging
from typing import List, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..entities.entity import Entity
    from .status_effect import StatusEffect

logger = logging.getLogger(__name__)


class EffectHandler:
    """
    Manages all status effects on a single entity. It is responsible for
    applying effects, updating their durations, applying damage-over-time,
    and calculating the final modified stats for the entity each frame.

    REFACTORED: Now uses a hybrid stat reset system. It prefers to use 'base_'
    attributes for resetting stats (ideal for towers with permanent upgrades),
    but will fall back to a snapshot of the entity's initial stats if a 'base_'
    attribute is not found. This makes the handler universally compatible
    without requiring dummy attributes on entities like enemies.
    """

    MODIFIABLE_STATS = [
        "damage",
        "range",
        "fire_rate",
        "effect_potency_multiplier",
        "aura_size_multiplier",
        "speed",
        "armor",
        "damage_taken_multiplier",
    ]

    def __init__(self, owner: "Entity"):
        """
        Initializes the EffectHandler.
        Args:
            owner (Entity): The entity instance that this handler belongs to.
        """
        self.owner = owner
        self.status_effects: List["StatusEffect"] = []

        # --- NEW: Take a snapshot of the owner's initial stats ---
        # This serves as a fallback for entities that don't have 'base_' attributes.
        self._initial_stats: Dict[str, Any] = {
            stat: getattr(owner, stat)
            for stat in self.MODIFIABLE_STATS
            if hasattr(owner, stat)
        }

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to the owner. If an effect of the same type
        already exists, it will either stack or refresh based on the effect's data.
        """
        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                existing_effect.stack_with(new_effect)
                return

        self.status_effects.append(new_effect)

    def update(self, dt: float):
        """
        Updates all active status effects, applying DoT, removing expired ones,
        and then recalculating all of the owner's stats.
        """
        total_dot_damage = 0

        for effect in self.status_effects:
            effect.update(dt)
            total_dot_damage += effect.get_dot_damage()

        if total_dot_damage > 0:
            self.owner.take_damage(total_dot_damage, ignores_armor=True)

        self.status_effects = [
            effect for effect in self.status_effects if effect.is_active
        ]

        self.apply_stat_modifiers()

    def apply_stat_modifiers(self):
        """
        Resets the owner's stats and then applies all active modifiers.
        """
        # --- REFACTORED: Hybrid Stat Reset Logic ---
        for stat_name in self.MODIFIABLE_STATS:
            if not hasattr(self.owner, stat_name):
                continue

            base_stat_name = f"base_{stat_name}"
            # Prefer the 'base_' attribute if it exists (for towers)
            if hasattr(self.owner, base_stat_name):
                base_value = getattr(self.owner, base_stat_name)
                setattr(self.owner, stat_name, base_value)
            # Fall back to the initial snapshot (for enemies)
            elif stat_name in self._initial_stats:
                initial_value = self._initial_stats[stat_name]
                setattr(self.owner, stat_name, initial_value)

        # --- Apply all active modifiers ---
        for effect in self.status_effects:
            for modifier in effect.modifiers:
                stat = modifier["stat"]
                op = modifier["operation"]
                value = modifier["value"]

                if hasattr(self.owner, stat):
                    current_value = getattr(self.owner, stat)
                    if op == "add":
                        setattr(self.owner, stat, current_value + value)
                    elif op == "multiply":
                        setattr(self.owner, stat, current_value * value)

        # Ensure stats don't fall below reasonable minimums
        if hasattr(self.owner, "speed"):
            if not any(e.effect_id == "stun" for e in self.status_effects):
                self.owner.speed = max(5, self.owner.speed)
