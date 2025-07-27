# game_logic/effects/status_effect.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StatusEffect:
    """
    Represents an active status effect applied to an entity.

    This class manages its own duration and holds the parameters of the
    effect, such as a damage-over-time value or a stat multiplier.
    """

    def __init__(
        self,
        effect_id: str,
        effect_data: Dict[str, Any],
        duration: float,
        potency: float,
    ):
        """
        Initializes a new instance of a status effect.

        Args:
            effect_id (str): The unique identifier for the effect (e.g., "slow").
            effect_data (Dict[str, Any]): The definition of the effect from the config file.
            duration (float): The total duration of this effect instance in seconds.
            potency (float): The strength of this effect (e.g., 0.4 for a 40% slow).
        """
        self.effect_id = effect_id
        self.effect_type = effect_data.get("type")
        self.stacking_logic = effect_data.get("stacking", "refresh")

        # Store effect-specific parameters
        self.params = effect_data.get("params", {})
        self.stat_to_modify = self.params.get("stat")

        # Overwrite the base multiplier with the specific instance's potency
        if "multiplier" in self.params:
            self.params["multiplier"] = potency

        self.duration_remaining = duration
        self.is_active = True

        logger.debug(f"Applied status effect '{self.effect_id}' for {duration}s.")

    def update(self, dt: float):
        """
        Ticks down the effect's duration.

        Args:
            dt (float): The time elapsed since the last frame.
        """
        if not self.is_active:
            return

        self.duration_remaining -= dt
        if self.duration_remaining <= 0:
            self.expire()

    def expire(self):
        """Marks the effect as no longer active."""
        self.is_active = False
        logger.debug(f"Status effect '{self.effect_id}' has expired.")

    def refresh(self, new_duration: float, new_potency: float):
        """
        Refreshes the effect's duration and potentially its potency.

        Used for effects with 'refresh' stacking logic.
        """
        self.duration_remaining = new_duration

        # Update potency only if the new one is stronger
        if "multiplier" in self.params and new_potency > self.params.get(
            "multiplier", 0
        ):
            self.params["multiplier"] = new_potency

        logger.debug(f"Refreshed status effect '{self.effect_id}'.")
