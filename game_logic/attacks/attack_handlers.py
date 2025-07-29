# game_logic/attacks/attack_handlers.py
import logging
import random
import math
from typing import TYPE_CHECKING, List, Dict, Any

# --- Import Attack Entity Classes ---
# We import all the concrete "attack entity" classes that these handlers will create.
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
# Each function in this module is a "factory" for a specific attack type.
# It takes the firing tower and a target, reads the tower's live stats and
# attack data, and is responsible for creating and returning one or more
# Entity objects that represent the attack.


def create_standard_projectile(tower: "Tower", target: "Enemy") -> List[Entity]:
    """
    Handles the creation of one or more standard, traveling projectiles.

    BUGFIX: This function has been refactored to read its core stats (damage,
    pierce, etc.) directly from the live Tower object's attributes, rather
    than re-reading the base config data. This ensures that all upgrades
    applied by the UpgradeManager are correctly reflected in the projectile.
    """
    attack_specific_data = tower.attack_data.get("data", {})
    projectiles_to_fire = []
    num_shots = tower.projectiles_per_shot

    # Assemble the status effect instances first, using the tower's live multipliers.
    effect_instances = []
    effects_to_apply_data = attack_specific_data.get("effects", {})
    for effect_id, params in effects_to_apply_data.items():
        if random.random() <= params.get("chance", 1.0):
            if effect_id in tower.status_effects_config:
                effect_def = tower.status_effects_config[effect_id]
                effect_instances.append(
                    StatusEffect(
                        effect_id=effect_id,
                        effect_data=effect_def,
                        duration=params.get("duration", 1.0)
                        * tower.base_effect_duration_multiplier,
                        potency=params.get("potency", 1.0)
                        * tower.base_effect_potency_multiplier,
                        source_entity_id=tower.entity_id,
                    )
                )

    # Assemble the ProjectileData payload using the tower's current, live stats.
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
        # Use modulo to cycle through targets if there are more shots than targets
        current_target = tower.current_targets[i % len(tower.current_targets)]
        origin_pos = tower.pos.copy()

        # Handle spread for multi-shot attacks
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
    """
    Handles the creation of a stationary, persistent ground effect at the
    target's location.

    BUGFIX: This function now correctly passes the 'data' sub-object from the
    tower's attack configuration to the aura's constructor, ensuring the
    aura is created with the correct stats (dps, radius, etc.).
    """
    aura = PersistentGroundAura(
        x=target.pos.x,
        y=target.pos.y,
        aura_data=tower.attack_data.get("data", {}),
        status_effects_config=tower.status_effects_config,
    )
    return [aura]


def create_persistent_attached_aura(tower: "Tower", target: "Enemy") -> List[Entity]:
    """
    Handles the creation of a persistent effect that attaches to and follows
    the primary target.

    BUGFIX: This function now correctly passes the 'data' sub-object from the
    tower's attack configuration to the aura's constructor, ensuring the
    aura is created with the correct stats (dps, radius, etc.).
    """
    aura = PersistentAttachedAura(
        target=target,
        aura_data=tower.attack_data.get("data", {}),
        status_effects_config=tower.status_effects_config,
    )
    return [aura]
