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


# --- NEW: Handler for missing effect type from Issue #13 ---
def multiply_effect_duration(tower: "Tower", value: Any):
    """
    Multiplies the duration of a tower's primary on-hit status effect.
    This is a more complex handler as it needs to find the effect first.
    """
    if not isinstance(value, (int, float)):
        return

    # This logic assumes we want to modify the *first* defined effect in the attack data.
    # This is a reasonable assumption for towers like the Freezer or Energy Beacon.
    if tower.attack and "data" in tower.attack and "effects" in tower.attack["data"]:
        effects_dict = tower.attack["data"]["effects"]
        if effects_dict:
            # Get the key of the first effect (e.g., "slow")
            primary_effect_key = next(iter(effects_dict))
            if "duration" in effects_dict[primary_effect_key]:
                original_duration = effects_dict[primary_effect_key]["duration"]
                effects_dict[primary_effect_key]["duration"] *= value
                logger.debug(
                    f"Multiplied duration of '{primary_effect_key}' for tower {tower.name}: {original_duration} -> {effects_dict[primary_effect_key]['duration']}"
                )
            else:
                logger.warning(
                    f"Upgrade tried to modify duration, but no 'duration' key found for effect '{primary_effect_key}' on tower {tower.name}"
                )


def modify_attack_data(tower: "Tower", value: Dict[str, Any]):
    """Modifies a key within the tower's attack.data dictionary."""
    if not isinstance(value, dict):
        return

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
                "operation": "add" | "multiply" | "set" | "add_aura" | "add_effect",
                "amount": <any>
            }
    """
    path_str = value.get("path")
    operation = value.get("operation")
    amount = value.get("amount")

    if not all([path_str, operation, amount is not None]):
        logger.error(f"Invalid value for modify_nested_property: {value}")
        return

    keys = path_str.replace("[", ".").replace("]", "").split(".")

    try:
        current_level = tower
        for key in keys[:-1]:
            if key.isdigit() and isinstance(current_level, list):
                current_level = current_level[int(key)]
            elif isinstance(current_level, dict):
                current_level = current_level[key]
            else:
                current_level = getattr(current_level, key)

        final_key = keys[-1]

        # --- MODIFIED: Expanded logic to handle new operations (Issue #14) ---
        if operation in ["add", "multiply", "set"]:
            # Logic for modifying existing values
            if final_key.isdigit() and isinstance(current_level, list):
                original_value = current_level[int(final_key)]
                final_key = int(final_key)
            elif isinstance(current_level, dict):
                original_value = current_level[final_key]
            else:
                original_value = getattr(current_level, final_key)

            if operation == "add":
                new_value = original_value + amount
            elif operation == "multiply":
                new_value = original_value * amount
            else:  # operation == "set"
                new_value = amount

            if isinstance(current_level, (dict, list)):
                current_level[final_key] = new_value
            else:
                setattr(current_level, final_key, new_value)

            logger.debug(f"Modified '{path_str}': {original_value} -> {new_value}")

        elif operation == "add_aura":
            # Logic for appending a new aura object to the 'auras' list
            target_list = getattr(tower, final_key)
            if isinstance(target_list, list) and isinstance(amount, dict):
                target_list.append(amount)
                logger.debug(f"Added new aura to '{final_key}' on tower {tower.name}")
            else:
                logger.error(
                    f"Cannot 'add_aura' to non-list or with non-dict amount for path '{path_str}'"
                )

        elif operation == "add_effect":
            # Logic for adding a new effect to an 'effects' dictionary
            target_dict = getattr(current_level, final_key)
            if isinstance(target_dict, dict) and isinstance(amount, dict):
                target_dict.update(amount)
                logger.debug(
                    f"Added new effect to '{final_key}' on tower {tower.name}: {amount}"
                )
            else:
                logger.error(
                    f"Cannot 'add_effect' to non-dict or with non-dict amount for path '{path_str}'"
                )

        else:
            logger.warning(
                f"Unknown operation '{operation}' for modify_nested_property"
            )
            return

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        logger.error(f"Could not modify nested property with path '{path_str}': {e}")
