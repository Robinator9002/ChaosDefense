# game_logic/attacks/attack_handlers.py
import logging
import random
import math
import copy
from typing import TYPE_CHECKING, List, Dict, Any

from ..entities.projectiles.projectile import Projectile
from ..entities.projectiles.projectile_data import ProjectileData
from ..entities.projectiles.persistent_ground_aura import PersistentGroundAura
from ..entities.projectiles.persistent_attached_aura import PersistentAttachedAura
from ..effects.status_effect import StatusEffect
from ..entities.entity import Entity


if TYPE_CHECKING:
    from ..entities.tower import Tower
    from ..entities.enemies.enemy import Enemy

logger = logging.getLogger(__name__)

# --- Attack Handler Functions ---
# Each function is a factory for a specific attack type, responsible for
# creating and returning the attack entities.


def create_standard_projectile(tower: "Tower", target: "Enemy") -> List[Entity]:
    """
    Handles the creation of standard projectiles, applying the tower's live
    effect_potency_multiplier and including effects from upgrades.
    """
    attack_specific_data = tower.attack.get("data", {})
    projectiles_to_fire = []
    num_shots = tower.projectiles_per_shot

    effect_instances = []

    # --- BUG FIX: Process both base effects and upgrade-added effects ---

    # 1. Process base effects from the tower's definition (e.g., a Freezer's slow)
    base_effects_data = attack_specific_data.get("effects", {})
    for effect_id, params in base_effects_data.items():
        if random.random() <= params.get("chance", 1.0):
            if effect_id in tower.status_effects_config:
                effect_def = tower.status_effects_config[effect_id]
                final_potency = (
                    params.get("potency", 1.0) * tower.effect_potency_multiplier
                )
                effect_instances.append(
                    StatusEffect(
                        effect_id=effect_id,
                        effect_data=effect_def,
                        duration=params.get("duration", 1.0),
                        potency=final_potency,
                        source_entity_id=tower.entity_id,
                    )
                )

    # 2. Process dynamic effects added by upgrades (e.g., a Turret's stun rounds)
    for effect_data in tower.on_hit_effects:
        effect_id = effect_data.get("id")
        if random.random() <= effect_data.get("chance", 1.0):
            if effect_id and effect_id in tower.status_effects_config:
                effect_def = tower.status_effects_config[effect_id]
                final_potency = (
                    effect_data.get("potency", 1.0) * tower.effect_potency_multiplier
                )
                effect_instances.append(
                    StatusEffect(
                        effect_id=effect_id,
                        effect_data=effect_def,
                        duration=effect_data.get("duration", 1.0),
                        potency=final_potency,
                        source_entity_id=tower.entity_id,
                    )
                )

    projectile_payload = ProjectileData(
        damage=tower.damage,
        effects_to_apply=effect_instances,
        status_effects_config=tower.status_effects_config,
        pierce_count=tower.pierce_count,
        blast_radius=tower.blast_radius,
        armor_shred=tower.armor_shred,
        on_blast_effects_data=tower.on_blast_effects,
        conditional_effects=tower.conditional_effects,
        on_hit_area_effects=tower.on_hit_area_effects,
        execute_threshold=tower.execute_threshold,
        on_apply_damage=tower.on_apply_damage,
        bonus_damage_per_debuff=tower.bonus_damage_per_debuff,
    )

    for i in range(num_shots):
        current_target = tower.current_targets[i % len(tower.current_targets)]
        origin_pos = tower.pos.copy()
        if num_shots > 1:
            spread_angle_deg = 15
            angle_offset = ((i / (num_shots - 1)) - 0.5) * spread_angle_deg * 2
            direction = current_target.pos - tower.pos
            base_angle_rad = math.atan2(direction.y, direction.x)
            offset_angle_rad = base_angle_rad + math.radians(angle_offset)
            origin_pos.x += 8 * math.cos(offset_angle_rad)
            origin_pos.y += 8 * math.sin(offset_angle_rad)

        new_projectile = Projectile(
            x=origin_pos.x,
            y=origin_pos.y,
            target=current_target,
            data=projectile_payload,
        )
        projectiles_to_fire.append(new_projectile)

    return projectiles_to_fire


def create_persistent_ground_aura(tower: "Tower", target: "Enemy") -> List[Entity]:
    original_aura_data = tower.attack.get("data", {})
    processed_aura_data = copy.deepcopy(original_aura_data)

    base_radius = processed_aura_data.get("radius", 50)
    processed_aura_data["radius"] = base_radius * tower.aura_size_multiplier

    if "effects" in processed_aura_data:
        for effect_id, params in processed_aura_data["effects"].items():
            base_potency = params.get("potency", 1.0)
            params["potency"] = base_potency * tower.effect_potency_multiplier

    aura = PersistentGroundAura(
        x=target.pos.x,
        y=target.pos.y,
        aura_data=processed_aura_data,
        status_effects_config=tower.status_effects_config,
    )
    return [aura]


def create_persistent_attached_aura(tower: "Tower", target: "Enemy") -> List[Entity]:
    original_aura_data = tower.attack.get("data", {})
    processed_aura_data = copy.deepcopy(original_aura_data)

    base_radius = processed_aura_data.get("radius", 50)
    processed_aura_data["radius"] = base_radius * tower.aura_size_multiplier

    if "effects" in processed_aura_data:
        for effect_id, params in processed_aura_data["effects"].items():
            base_potency = params.get("potency", 1.0)
            params["potency"] = base_potency * tower.effect_potency_multiplier

    aura = PersistentAttachedAura(
        target=target,
        aura_data=processed_aura_data,
        status_effects_config=tower.status_effects_config,
    )
    return [aura]
