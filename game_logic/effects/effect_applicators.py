# game_logic/effects/effect_applicators.py
import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ..entities.tower import Tower

logger = logging.getLogger(__name__)

# This file contains a library of functions, each designed to apply a specific
# type of upgrade effect to a tower. This approach keeps the upgrade logic
# modular and data-driven.


def add_damage(tower: "Tower", value: Any):
    if isinstance(value, (int, float)) and hasattr(tower, "base_damage"):
        tower.damage += value
        tower.base_damage += value


def add_range(tower: "Tower", value: Any):
    if isinstance(value, (int, float)) and hasattr(tower, "base_range"):
        tower.range += value
        tower.base_range += value


def multiply_fire_rate(tower: "Tower", value: Any):
    if isinstance(value, (int, float)) and hasattr(tower, "base_fire_rate"):
        tower.fire_rate *= value
        tower.base_fire_rate *= value


def set_projectiles_per_shot(tower: "Tower", value: Any):
    if isinstance(value, int):
        tower.projectiles_per_shot = value


def set_pierce(tower: "Tower", value: Any):
    if isinstance(value, int):
        tower.pierce_count = value


def add_armor_shred(tower: "Tower", value: Any):
    if isinstance(value, int):
        tower.armor_shred += value


def add_effect(tower: "Tower", value: Any):
    if isinstance(value, dict):
        tower.on_hit_effects.append(value)


def add_execute_threshold(tower: "Tower", value: Any):
    if isinstance(value, dict):
        tower.execute_threshold = value


def multiply_blast_radius(tower: "Tower", value: Any):
    if isinstance(value, (int, float)):
        tower.blast_radius *= value


def add_blast_effect(tower: "Tower", value: Any):
    if isinstance(value, dict):
        tower.on_blast_effects.append(value)


def multiply_effect_potency(tower: "Tower", value: Any):
    if isinstance(value, (int, float)):
        tower.effect_potency_multiplier *= value
        tower.base_effect_potency_multiplier *= value


def add_on_apply_damage(tower: "Tower", value: Any):
    if isinstance(value, int):
        tower.on_apply_damage += value


def add_on_death_explosion(tower: "Tower", value: Any):
    if isinstance(value, dict):
        tower.on_death_explosion = value


def add_bonus_damage_per_debuff(tower: "Tower", value: Any):
    if isinstance(value, int):
        tower.bonus_damage_per_debuff += value


def add_conditional_effect(tower: "Tower", value: Any):
    if isinstance(value, dict):
        tower.conditional_effects.append(value)


def add_area_effect_on_hit(tower: "Tower", value: Any):
    if isinstance(value, dict):
        tower.on_hit_area_effects.append(value)


def modify_attack_data(tower: "Tower", value: Dict[str, Any]):
    """Modifies a key within the tower's attack.data dictionary."""
    if not isinstance(value, dict):
        return

    # --- FIX: Use tower.attack, not tower.attack_data ---
    if not hasattr(tower, "attack") or "data" not in tower.attack:
        logger.warning(f"Tower {tower.name} has no attack data to modify.")
        return

    attack_specifics = tower.attack["data"]
    key = value.get("key")
    op = value.get("operation")
    amount = value.get("amount")

    if not all([key, op, amount is not None]):
        return

    if key in attack_specifics:
        if op == "add":
            attack_specifics[key] += amount
        elif op == "multiply":
            attack_specifics[key] *= amount
        elif op == "set":
            attack_specifics[key] = amount


def modify_nested_property(tower: "Tower", value: Dict[str, Any]):
    """
    Modifies a nested property within a tower's data structure using a
    dot- and bracket-separated path string. This is the key handler for
    support tower upgrades that modify complex, nested data like auras.

    Args:
        tower (Tower): The tower entity to be modified.
        value (Dict[str, Any]): A dictionary defining the modification.
            Expected format:
            {
                "path": "auras[0].effects.damage_boost.potency",
                "operation": "add" | "multiply",
                "amount": <float_or_int>
            }
    """
    path_str = value.get("path")
    operation = value.get("operation")
    amount = value.get("amount")

    # --- 1. Validate the input data from the JSON config ---
    if not all([path_str, operation, amount is not None]):
        logger.error(f"Invalid value for modify_nested_property: {value}")
        return

    # --- 2. Parse the path string into a list of keys ---
    # This standardizes access for attributes, dict keys, and list indices.
    # e.g., "auras[0].effects" becomes ["auras", "0", "effects"]
    keys = path_str.replace("[", ".").replace("]", "").split(".")

    try:
        # --- 3. Traverse the structure to find the parent of the target property ---
        current_level = tower
        for key in keys[:-1]:  # Go up to the second-to-last key
            if key.isdigit() and isinstance(current_level, list):
                current_level = current_level[int(key)]
            elif isinstance(current_level, dict):
                current_level = current_level[key]
            else:
                current_level = getattr(current_level, key)

        final_key = keys[-1]

        # --- 4. Get the original value and apply the operation ---
        if final_key.isdigit() and isinstance(current_level, list):
            original_value = current_level[int(final_key)]
            final_key = int(final_key)  # Cast to int for list indexing
        elif isinstance(current_level, dict):
            original_value = current_level[final_key]
        else:
            original_value = getattr(current_level, final_key)

        if operation == "add":
            new_value = original_value + amount
        elif operation == "multiply":
            new_value = original_value * amount
        else:
            logger.warning(
                f"Unknown operation '{operation}' for modify_nested_property"
            )
            return

        # --- 5. Set the new value back on the parent object/dict/list ---
        if isinstance(current_level, dict) or isinstance(current_level, list):
            current_level[final_key] = new_value
        else:
            setattr(current_level, final_key, new_value)

        logger.debug(f"Modified '{path_str}': {original_value} -> {new_value}")

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        logger.error(f"Could not modify nested property with path '{path_str}': {e}")
