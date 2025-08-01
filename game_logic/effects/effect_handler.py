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
    applying effects, updating their durations, applying damage-over-time,
    and calculating the final modified stats for the entity each frame.
    """

    # --- REFACTOR: Centralized list of modifiable stats ---
    # This list is the single source of truth for all stats that can be
    # temporarily modified by status effects. This decouples the handler from
    # specific entity implementations (Tower, Enemy). To add a new modifiable
    # stat to the game, a developer only needs to add it here.
    MODIFIABLE_STATS = [
        "damage",
        "range",
        "fire_rate",
        "effect_potency_multiplier",
        "aura_size_multiplier",
        "speed",
        "armor",
    ]

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
        for existing_effect in self.status_effects:
            if existing_effect.effect_id == new_effect.effect_id:
                existing_effect.stack_with(new_effect)
                return

        self.status_effects.append(new_effect)

    def update(self, dt: float):
        """
        Updates all active status effects, applying DoT damage, removing any
        that have expired, and then recalculating all of the owner's stats.
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
        Resets the owner's stats to their base values and then applies all
        modifiers from currently active status effects.
        """
        # --- Step 1: Reset all modifiable stats to their base values ---
        # This generic loop iterates through our centralized list.
        for stat_name in self.MODIFIABLE_STATS:
            base_stat_name = f"base_{stat_name}"
            # Check if the owner has both the stat and its 'base_' counterpart.
            if hasattr(self.owner, stat_name) and hasattr(self.owner, base_stat_name):
                base_value = getattr(self.owner, base_stat_name)
                setattr(self.owner, stat_name, base_value)

        # Handle special cases that don't follow the base_stat pattern.
        if hasattr(self.owner, "damage_taken_multiplier"):
            self.owner.damage_taken_multiplier = 1.0

        # --- Step 2: Apply all active modifiers ---
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
