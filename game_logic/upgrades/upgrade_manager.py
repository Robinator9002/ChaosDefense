# game_logic/upgrades/upgrade_manager.py
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING, Callable

from .upgrade import Upgrade

# --- MODIFIED: Import the new, separated effect applicator functions ---
# We now import the module containing our library of handler functions.
# The relative path '..' correctly navigates from 'upgrades' up to 'game_logic'
# and then down into the 'effects' directory, as per your structural change.
from ..effects import effect_applicators

# Use TYPE_CHECKING to avoid a circular import dependency at runtime.
if TYPE_CHECKING:
    from ..entities.tower import Tower

logger = logging.getLogger(__name__)


class UpgradeManager:
    """
    Manages the loading, retrieval, and application of tower upgrades using a
    data-driven, handler-based system for maximum flexibility and extensibility.
    """

    def __init__(self, upgrade_definitions: Dict[str, Any]):
        """
        Initializes the UpgradeManager.

        It parses the raw upgrade definitions and, most importantly, creates a
        dispatch table (_effect_handlers) that maps effect type strings from
        the JSON config to the actual Python functions that apply those effects.
        """
        self.definitions: Dict[str, Dict[str, list[Upgrade]]] = {}
        # --- NEW: The dispatch table for all upgrade effects ---
        # This dictionary is the core of the new system. It maps the 'type'
        # string from the JSON to the corresponding function in the
        # effect_applicators module. To add a new effect to the game, you
        # only need to add an entry here and in the applicators file.
        self._effect_handlers: Dict[str, Callable[["Tower", Any], None]] = {
            "add_damage": effect_applicators.add_damage,
            "add_range": effect_applicators.add_range,
            "multiply_fire_rate": effect_applicators.multiply_fire_rate,
            "set_projectiles_per_shot": effect_applicators.set_projectiles_per_shot,
            "set_pierce": effect_applicators.set_pierce,
            "add_armor_shred": effect_applicators.add_armor_shred,
            "add_effect": effect_applicators.add_effect,
            "add_execute_threshold": effect_applicators.add_execute_threshold,
            "multiply_blast_radius": effect_applicators.multiply_blast_radius,
            "add_blast_effect": effect_applicators.add_blast_effect,
            "multiply_effect_duration": effect_applicators.multiply_effect_duration,
            "multiply_effect_potency": effect_applicators.multiply_effect_potency,
            "add_on_apply_damage": effect_applicators.add_on_apply_damage,
            "add_on_death_explosion": effect_applicators.add_on_death_explosion,
            "add_bonus_damage_per_debuff": effect_applicators.add_bonus_damage_per_debuff,
            "add_conditional_effect": effect_applicators.add_conditional_effect,
            "add_area_effect_on_hit": effect_applicators.add_area_effect_on_hit,
        }

        self._parse_definitions(upgrade_definitions)
        logger.info("UpgradeManager initialized with new handler-based system.")

    def _parse_definitions(self, raw_definitions: Dict[str, Any]):
        """
        Parses the raw upgrade definition dictionary into Upgrade objects.
        This method is now compatible with the new JSON structure where 'effects'
        is a list of objects.
        """
        for tower_type_id, paths_data in raw_definitions.items():
            if not isinstance(paths_data, dict):
                continue

            self.definitions[tower_type_id] = {}
            for path_id, path_data in paths_data.items():
                if not isinstance(path_data, dict):
                    continue

                # NOTE: This assumes the 'Upgrade' dataclass has been updated to expect
                # 'effects: List[Dict[str, Any]]' to match the new JSON format.
                self.definitions[tower_type_id][path_id] = [
                    Upgrade(**upgrade_data)
                    for upgrade_data in path_data.get("upgrades", [])
                ]

    def get_next_upgrade(self, tower: "Tower", path_id: str) -> Optional[Upgrade]:
        """
        Gets the next available upgrade for a specific tower on a given path.
        """
        current_tier = tower.path_a_tier if path_id == "path_a" else tower.path_b_tier

        try:
            path_upgrades = self.definitions[tower.tower_type_id][path_id]
            if 0 <= current_tier < len(path_upgrades):
                return path_upgrades[current_tier]
        except KeyError:
            logger.error(
                f"Invalid tower_type_id '{tower.tower_type_id}' or path_id '{path_id}' for upgrade lookup."
            )
            return None
        return None

    def apply_upgrade(self, tower: "Tower", upgrade: Upgrade):
        """
        Applies the effects of a given upgrade to a target tower using the
        new data-driven handler system.
        """
        logger.info(f"Applying upgrade '{upgrade.id}' to tower {tower.entity_id}.")

        # --- REFACTORED: The core logic is now a simple loop ---
        # The rigid if/elif block is gone. We now iterate through the list of
        # effects defined in the JSON for this upgrade.
        for effect_data in upgrade.effects:
            effect_type = effect_data.get("type")
            effect_value = effect_data.get("value")

            # Look up the correct handler function from our dispatch table.
            handler = self._effect_handlers.get(effect_type)

            if handler:
                # If a handler is found, execute it, passing the tower and
                # the effect's value.
                handler(tower, effect_value)
            else:
                # If no handler is registered for this effect type, log a
                # warning. This makes debugging new or mistyped effects easy.
                logger.warning(
                    f"Unknown upgrade effect type found in config: '{effect_type}'"
                )
