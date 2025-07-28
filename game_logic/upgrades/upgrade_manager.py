# game_logic/upgrades/upgrade_manager.py
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from .upgrade import Upgrade

# Use TYPE_CHECKING to avoid a circular import dependency at runtime.
if TYPE_CHECKING:
    from ..entities.tower import Tower

logger = logging.getLogger(__name__)


class UpgradeManager:
    """
    Manages the loading, retrieval, and application of tower upgrades.

    This class acts as a central service for all upgrade-related logic. It
    is initialized once with the game's configuration and then used by the
    GameManager to handle upgrade purchases and by the UI to display
    upgrade information.
    """

    def __init__(self, upgrade_definitions: Dict[str, Any]):
        """
        Initializes the UpgradeManager.

        It parses the raw dictionary from the JSON configuration file into a more
        structured and efficient format, converting each upgrade entry into an
        instance of the Upgrade data class.

        Args:
            upgrade_definitions (Dict[str, Any]): The raw, loaded content from
                                                 upgrade_definitions.json.
        """
        # The definitions are stored in a nested dictionary for fast lookups:
        # { "tower_id": { "path_id": [Upgrade, Upgrade, ...], ... }, ... }
        self.definitions: Dict[str, Dict[str, list[Upgrade]]] = {}
        self._parse_definitions(upgrade_definitions)
        logger.info("UpgradeManager initialized and all upgrade definitions parsed.")

    def _parse_definitions(self, raw_definitions: Dict[str, Any]):
        """
        Parses the raw upgrade definition dictionary into Upgrade objects.
        This internal method populates the self.definitions dictionary.
        """
        for tower_type_id, paths_data in raw_definitions.items():
            # First-level validation: Skip top-level comments.
            if not isinstance(paths_data, dict):
                logger.debug(
                    f"Skipping non-dictionary key '{tower_type_id}' in upgrade definitions."
                )
                continue

            self.definitions[tower_type_id] = {}
            for path_id, path_data in paths_data.items():
                # --- BUG FIX: SECOND-LEVEL VALIDATION ---
                # Before processing a path, check if its data is a dictionary.
                # This prevents crashes on comments inside a tower's definition.
                if not isinstance(path_data, dict):
                    logger.debug(
                        f"Skipping non-dictionary path key '{path_id}' for tower '{tower_type_id}'."
                    )
                    continue

                self.definitions[tower_type_id][path_id] = [
                    Upgrade(**upgrade_data)
                    for upgrade_data in path_data.get("upgrades", [])
                ]

    def get_next_upgrade(self, tower: "Tower", path_id: str) -> Optional[Upgrade]:
        """
        Gets the next available upgrade for a specific tower on a given path.

        It checks the tower's current tier on the specified path and returns the
        next Upgrade object in the sequence.

        Args:
            tower ("Tower"): The specific tower instance requesting the upgrade.
            path_id (str): The identifier for the upgrade path ("path_a" or "path_b").

        Returns:
            Optional[Upgrade]: The next Upgrade object if one is available,
                               otherwise None if the path is maxed out or invalid.
        """
        # Determine which tier to look for based on the requested path.
        current_tier = tower.path_a_tier if path_id == "path_a" else tower.path_b_tier

        try:
            # Look up the list of all upgrades for the tower's type and path.
            path_upgrades = self.definitions[tower.tower_type_id][path_id]

            # Check if the current tier is a valid index in the list.
            if 0 <= current_tier < len(path_upgrades):
                return path_upgrades[current_tier]
        except KeyError:
            logger.error(
                f"Invalid tower_type_id '{tower.tower_type_id}' or path_id '{path_id}' for upgrade lookup."
            )
            return None

        # If the index is out of bounds, the path is fully upgraded.
        return None

    def apply_upgrade(self, tower: "Tower", upgrade: Upgrade):
        """
        Applies the effects of a given upgrade to a target tower.

        This method is the core of the upgrade system's logic. It iterates
        through the 'effects' dictionary of an Upgrade object and modifies the
        tower's attributes accordingly. This decouples the upgrade data from
        the tower's own code.

        Args:
            tower ("Tower"): The tower instance to be modified.
            upgrade (Upgrade): The Upgrade object whose effects should be applied.
        """
        logger.info(f"Applying upgrade '{upgrade.id}' to tower {tower.entity_id}.")

        for effect_key, value in upgrade.effects.items():
            # This block checks each key in the 'effects' dictionary and performs
            # the corresponding action on the tower object.
            if effect_key == "add_damage":
                tower.damage += value
            elif effect_key == "add_range":
                tower.range += value
            elif effect_key == "multiply_fire_rate":
                tower.fire_rate *= value
            elif effect_key == "set_projectiles_per_shot":
                tower.projectiles_per_shot = value
            elif effect_key == "set_pierce":
                tower.pierce_count = value
            elif effect_key == "add_armor_shred":
                tower.armor_shred += value
            elif effect_key == "add_effect":
                tower.on_hit_effects.append(value)
            elif effect_key == "add_execute_threshold":
                tower.execute_threshold = value
            elif effect_key == "multiply_blast_radius":
                tower.blast_radius *= value
            elif effect_key == "add_blast_effect":
                tower.on_blast_effects.append(value)
            elif effect_key == "multiply_effect_duration":
                tower.base_effect_duration_multiplier *= value
            elif effect_key == "multiply_effect_potency":
                tower.base_effect_potency_multiplier *= value
            elif effect_key == "add_on_apply_damage":
                tower.on_apply_damage += value
            elif effect_key == "add_on_death_explosion":
                tower.on_death_explosion = value
            # --- Start of new effect handlers for Energy Beacon ---
            elif effect_key == "add_bonus_damage_per_debuff":
                tower.bonus_damage_per_debuff += value
            elif effect_key == "add_conditional_effect":
                tower.conditional_effects.append(value)
            elif effect_key == "add_area_effect_on_hit":
                tower.on_hit_area_effects.append(value)
            else:
                # Log a warning for any effect keys that are not recognized.
                # This helps in debugging new or mistyped upgrade effects.
                logger.warning(f"Unknown upgrade effect key found: '{effect_key}'")
