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


def modify_nested_aura_property(tower: "Tower", value: Dict[str, Any]):
    """
    Modifies a nested property within a tower's aura definition.
    Example: change the potency of the 'damage_boost' effect in the first aura.
    """
    if not hasattr(tower, "auras") or not tower.auras:
        logger.warning(
            f"Attempted to modify aura on tower {tower.name} which has no auras."
        )
        return

    aura_index = value.get("aura_index", 0)
    path = value.get("path", "").split(".")
    operation = value.get("operation")
    amount = value.get("amount")

    if not all([path, operation, amount is not None]):
        logger.error(f"Invalid value for modify_nested_aura_property: {value}")
        return

    try:
        current_level = tower.auras[aura_index]
        for key in path[:-1]:
            current_level = current_level[key]

        final_key = path[-1]
        original_value = current_level[final_key]

        if operation == "add":
            current_level[final_key] += amount
        elif operation == "multiply":
            current_level[final_key] *= amount
        else:
            logger.warning(
                f"Unknown operation '{operation}' for modify_nested_aura_property"
            )

    except (KeyError, IndexError, TypeError) as e:
        logger.error(
            f"Could not modify nested aura property with path '{'.'.join(path)}': {e}"
        )
