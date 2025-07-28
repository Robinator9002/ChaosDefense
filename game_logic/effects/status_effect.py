# game_logic/effects/status_effect.py
import logging
import uuid
from typing import Dict, Any, Optional

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

    def update(self, dt: float) -> int:
        """
        Ticks down the effect's duration and handles DoT logic.

        Args:
            dt (float): The time elapsed since the last frame.

        Returns:
            int: The amount of DoT damage to be applied this frame, or 0.
        """
        if not self.is_active:
            return 0

        self.duration_remaining -= dt
        if self.duration_remaining <= 0:
            self.expire()
            return 0

        # --- Handle DoT Ticking ---
        if self.effect_type == "damage_over_time" and self.tick_interval > 0:
            self.tick_timer -= dt
            if self.tick_timer <= 0:
                self.tick_timer += self.tick_interval  # Reset timer for the next tick
                # The potency for a DoT is its damage per tick.
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
