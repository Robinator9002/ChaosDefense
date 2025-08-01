# game_logic/effects/status_effect.py
import logging
import uuid
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class StatusEffect:
    """
    Represents an active status effect applied to an entity.

    This class is a self-contained state machine for an effect. It manages its
    own duration, stacking behavior, and parameters. For Damage-over-Time (DoT)
    effects, it also manages the interval between damage ticks.
    """

    def __init__(
        self,
        effect_id: str,
        effect_data: Dict[str, Any],
        duration: float,
        potency: float,
        source_entity_id: Optional[uuid.UUID] = None,
    ):
        """
        Initializes a new instance of a status effect.

        Args:
            effect_id (str): The unique identifier for the effect (e.g., "slow").
            effect_data (Dict[str, Any]): The definition of the effect from the config.
            duration (float): The total duration of this effect instance in seconds.
            potency (float): The strength of this effect (e.g., 0.4 for a 40% slow,
                             or 5 for 5 armor reduction).
            source_entity_id (Optional[uuid.UUID]): The unique ID of the entity that
                                                   created this effect.
        """
        # --- Core Properties ---
        self.effect_id = effect_id
        self.effect_type = effect_data.get("type")
        self.stacking_logic = effect_data.get("stacking", "refresh")
        self.source_entity_id = source_entity_id
        self.params = effect_data.get("params", {})
        self.stat_to_modify = self.params.get("stat")

        # --- Instance-specific State ---
        self.duration_remaining = duration
        self.is_active = True
        self.potency = potency  # Generic potency for multipliers or flat amounts

        # --- Damage-over-Time (DoT) Specific State ---
        self.tick_interval = self.params.get("tick_interval", 0)
        self.tick_timer = self.tick_interval  # Start the timer ready for the first tick

        logger.debug(
            f"Applied status effect '{self.effect_id}' (potency: {self.potency}) "
            f"for {duration}s."
        )

    @property
    def modifiers(self) -> List[Dict[str, Any]]:
        """
        A property that translates the effect's data into a standardized list
        of stat modifiers for the EffectHandler to consume. This is the fix
        for the bug where the handler was looking for a non-existent attribute.

        Returns:
            A list of modification dictionaries, e.g.,
            [{"stat": "speed", "operation": "multiply", "value": 0.6}]
        """
        if self.effect_type not in ["stat_modifier", "stat_debuff"]:
            return []

        if not self.stat_to_modify:
            return []

        # For stat_modifier, potency is a multiplier (e.g., 1.2 for +20%, 0.6 for -40%)
        if self.effect_type == "stat_modifier":
            return [
                {
                    "stat": self.stat_to_modify,
                    "operation": "multiply",
                    "value": self.potency,
                }
            ]

        # For stat_debuff, potency is a flat reduction (e.g., -5 armor)
        if self.effect_type == "stat_debuff":
            return [
                {
                    "stat": self.stat_to_modify,
                    "operation": "add",
                    "value": -self.potency,  # Apply as a negative addition
                }
            ]

        return []

    def update(self, dt: float) -> bool:
        """
        Ticks down the effect's duration and handles DoT logic.

        Args:
            dt (float): The time elapsed since the last frame.

        Returns:
            bool: True if the effect is still active, False if it has expired.
        """
        if not self.is_active:
            return False

        self.duration_remaining -= dt
        if self.duration_remaining <= 0:
            self.expire()
            return False

        # --- Handle DoT Ticking ---
        if self.effect_type == "damage_over_time" and self.tick_interval > 0:
            self.tick_timer -= dt
            if self.tick_timer <= 0:
                self.tick_timer += self.tick_interval
                # The owner's EffectHandler will read this value
                damage_this_tick = int(self.potency)
                # We can directly apply damage here if we have the owner
                # but for now, we'll let the handler manage it.
                pass  # Placeholder for future direct application

        return True

    def get_dot_damage(self) -> int:
        """
        Calculates and returns any damage-over-time damage that should be
        applied this frame. Resets the internal flag after checking.

        Returns:
            int: The amount of DoT damage to apply.
        """
        if self.effect_type == "damage_over_time" and self.tick_timer <= 0:
            # This check happens after the update loop has already ticked the timer
            return int(self.potency)
        return 0

    def expire(self):
        """Marks the effect as no longer active."""
        self.is_active = False
        logger.debug(f"Status effect '{self.effect_id}' has expired.")

    def stack_with(self, new_effect: "StatusEffect"):
        """
        Applies stacking logic when an effect of the same type is reapplied.

        Args:
            new_effect (StatusEffect): The new effect instance being applied.
        """
        # Always reset the duration on any kind of stack.
        self.duration_remaining = max(
            self.duration_remaining, new_effect.duration_remaining
        )

        # --- Handle Potency Stacking ---
        if self.stacking_logic == "refresh":
            # Take the stronger of the two potencies.
            self.potency = max(self.potency, new_effect.potency)

        elif self.stacking_logic in ["stack_potency", "stack_intensity"]:
            # Add the potencies together.
            self.potency += new_effect.potency

        logger.debug(
            f"Stacked effect '{self.effect_id}'. New potency: {self.potency}, "
            f"New duration: {self.duration_remaining:.2f}s"
        )
