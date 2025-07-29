# game_logic/effects/effect_applicators.py
import logging
from typing import TYPE_CHECKING, Any, Dict

# Use TYPE_CHECKING to avoid circular imports at runtime, a best practice
# when dealing with complex type dependencies between modules.
if TYPE_CHECKING:
    from ..entities.tower import Tower

logger = logging.getLogger(__name__)

# --- Handler Functions for Tower Upgrades ---
# Each function in this module is a self-contained "handler" responsible for
# applying a single, specific type of effect to a tower. This approach
# decouples the upgrade logic from the UpgradeManager, making the system
# modular and easy to extend.


def modify_attack_data(tower: "Tower", value: Dict[str, Any]):
    """
    A generic handler to modify any value within the tower's attack_data['data'].
    This has been expanded to handle not just numeric operations but also complex
    data manipulations like adding effects to a dictionary or setting entirely
    new parameters.

    The 'value' dictionary should contain:
    - 'key' (str): The key of the attribute to modify.
    - 'operation' (str): 'add', 'multiply', 'set', 'add_effect', or 'modify_nested'.
    """
    key = value.get("key")
    operation = value.get("operation")

    if not all([key, operation]):
        logger.error(f"Invalid 'modify_attack_data' payload (missing key/op): {value}")
        return

    attack_specifics = tower.attack_data.get("data", {})

    if operation in ["add", "multiply"]:
        amount = value.get("amount")
        if amount is None or key not in attack_specifics:
            logger.warning(f"Invalid numeric operation for modify_attack_data: {value}")
            return
        original_value = attack_specifics[key]
        if operation == "add":
            attack_specifics[key] += amount
        elif operation == "multiply":
            attack_specifics[key] *= amount
        logger.debug(
            f"Applied '{key} {operation} {amount}'. Value: {original_value} -> {attack_specifics[key]}."
        )

    elif operation == "set":
        new_value = value.get("amount") or value.get("effect") or value.get("params")
        if new_value is None:
            logger.error(f"Invalid 'set' operation for modify_attack_data: {value}")
            return
        attack_specifics[key] = new_value
        logger.debug(f"Applied 'set {key}'. New value: {attack_specifics[key]}.")

    elif operation == "add_effect":
        effect_to_add = value.get("effect")
        if not effect_to_add or not isinstance(effect_to_add, dict):
            logger.error(
                f"Invalid 'add_effect' operation for modify_attack_data: {value}"
            )
            return
        if key not in attack_specifics or not isinstance(attack_specifics[key], dict):
            attack_specifics[key] = {}

        effect_id = effect_to_add.get("id")
        if effect_id:
            attack_specifics[key][effect_id] = effect_to_add
            logger.debug(f"Applied 'add_effect' to '{key}'. Added effect: {effect_id}.")
        else:
            logger.error(f"Effect for 'add_effect' is missing an 'id': {effect_to_add}")

    # --- NEW: Handler for modifying deeply nested values ---
    elif operation == "modify_nested":
        nested_key_str = value.get("nested_key")
        nested_op = value.get("nested_op")
        amount = value.get("amount")

        if not all([nested_key_str, nested_op, amount is not None]):
            logger.error(f"Invalid 'modify_nested' payload: {value}")
            return

        try:
            # e.g., nested_key_str = "elemental_vulnerability.duration"
            keys = nested_key_str.split(".")
            # current_level will point to attack_specifics['effects']
            current_level = attack_specifics.get(key, {})

            # Traverse down to the second-to-last key
            for k in keys[:-1]:
                current_level = current_level[k]

            final_key = keys[-1]
            original_value = current_level[final_key]

            if nested_op == "add":
                current_level[final_key] += amount
            elif nested_op == "multiply":
                current_level[final_key] *= amount
            else:
                logger.error(f"Unsupported nested_op '{nested_op}'")
                return

            logger.debug(
                f"Applied 'modify_nested': {nested_key_str} {nested_op} {amount}. "
                f"Value: {original_value} -> {current_level[final_key]}."
            )
        except (KeyError, TypeError) as e:
            logger.error(f"Could not resolve nested key '{nested_key_str}': {e}")

    else:
        logger.error(f"Unknown operation '{operation}' in 'modify_attack_data'")


def add_damage(tower: "Tower", value: int):
    """Increases the tower's base damage by a flat amount."""
    tower.damage += value
    logger.debug(f"Applied 'add_damage': {value}. New tower damage: {tower.damage}")


def add_range(tower: "Tower", value: int):
    """Increases the tower's attack range by a flat amount."""
    tower.range += value
    logger.debug(f"Applied 'add_range': {value}. New tower range: {tower.range}")


def multiply_fire_rate(tower: "Tower", value: float):
    """Multiplies the tower's fire rate. A value of 1.4 is a 40% increase."""
    tower.fire_rate *= value
    logger.debug(
        f"Applied 'multiply_fire_rate': {value}. New fire rate: {tower.fire_rate:.2f}"
    )


def set_projectiles_per_shot(tower: "Tower", value: int):
    """Sets the number of projectiles the tower fires at once."""
    tower.projectiles_per_shot = value
    logger.debug(
        f"Applied 'set_projectiles_per_shot': {value}. New projectile count: {tower.projectiles_per_shot}"
    )


def set_pierce(tower: "Tower", value: int):
    """Sets the number of enemies a projectile can pierce."""
    tower.pierce_count = value
    logger.debug(
        f"Applied 'set_pierce': {value}. New pierce count: {tower.pierce_count}"
    )


def add_armor_shred(tower: "Tower", value: int):
    """Adds a flat amount to the armor shred applied by projectiles."""
    tower.armor_shred += value
    logger.debug(
        f"Applied 'add_armor_shred': {value}. New armor shred: {tower.armor_shred}"
    )


def add_effect(tower: "Tower", value: Dict[str, Any]):
    """Adds a new on-hit status effect to the tower's projectiles."""
    tower.on_hit_effects.append(value)
    logger.debug(f"Applied 'add_effect': {value['id']}")


def add_execute_threshold(tower: "Tower", value: Dict[str, float]):
    """Sets or overwrites the tower's ability to execute low-health targets."""
    tower.execute_threshold = value
    logger.debug(f"Applied 'add_execute_threshold': {value}")


def multiply_blast_radius(tower: "Tower", value: float):
    """Multiplies the tower's projectile blast radius."""
    tower.blast_radius *= value
    logger.debug(
        f"Applied 'multiply_blast_radius': {value}. New blast radius: {tower.blast_radius}"
    )


def add_blast_effect(tower: "Tower", value: Dict[str, Any]):
    """Adds a status effect that is applied by the projectile's explosion."""
    tower.on_blast_effects.append(value)
    logger.debug(f"Applied 'add_blast_effect': {value['id']}")


def multiply_effect_duration(tower: "Tower", value: float):
    """Multiplies the duration of all status effects applied by this tower."""
    tower.base_effect_duration_multiplier *= value
    logger.debug(
        f"Applied 'multiply_effect_duration': {value}. New duration multiplier: {tower.base_effect_duration_multiplier}"
    )


def multiply_effect_potency(tower: "Tower", value: float):
    """Multiplies the potency of all status effects applied by this tower."""
    tower.base_effect_potency_multiplier *= value
    logger.debug(
        f"Applied 'multiply_effect_potency': {value}. New potency multiplier: {tower.base_effect_potency_multiplier}"
    )


def add_on_apply_damage(tower: "Tower", value: int):
    """Adds a flat amount of bonus damage applied when a projectile hits."""
    tower.on_apply_damage += value
    logger.debug(
        f"Applied 'add_on_apply_damage': {value}. New bonus damage: {tower.on_apply_damage}"
    )


def add_on_death_explosion(tower: "Tower", value: Dict[str, Any]):
    """Grants the tower the ability to make enemies explode on death."""
    tower.on_death_explosion = value
    logger.debug(f"Applied 'add_on_death_explosion': {value}")


def add_bonus_damage_per_debuff(tower: "Tower", value: int):
    """Adds bonus damage based on the number of debuffs on the target."""
    tower.bonus_damage_per_debuff += value
    logger.debug(
        f"Applied 'add_bonus_damage_per_debuff': {value}. New bonus: {tower.bonus_damage_per_debuff}"
    )


def add_conditional_effect(tower: "Tower", value: Dict[str, Any]):
    """Adds an effect that only applies if a certain condition is met."""
    tower.conditional_effects.append(value)
    logger.debug(f"Applied 'add_conditional_effect': {value}")


def add_area_effect_on_hit(tower: "Tower", value: Dict[str, Any]):
    """Adds a chance to trigger a secondary area-of-effect on projectile impact."""
    tower.on_hit_area_effects.append(value)
    logger.debug(f"Applied 'add_area_effect_on_hit': {value}")
