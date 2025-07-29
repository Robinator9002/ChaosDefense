# game_logic/entities/projectiles/projectile_data.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# To avoid circular imports, we only import StatusEffect for type hinting.
from ...effects.status_effect import StatusEffect


@dataclass(frozen=True)
class ProjectileData:
    """
    A Data Transfer Object (DTO) that encapsulates all the properties of a
    projectile at the moment it is fired from a tower.

    This class serves as an immutable "work order" from the Tower to the
    Projectile. Using this pattern decouples the Tower from the Projectile's
    internal implementation. The Tower's only job is to assemble this data
    packet; the Projectile's job is to interpret it. This makes both classes
    cleaner and easier to maintain. If a new projectile mechanic is added,
    only this dataclass and the relevant logic in the Tower and Projectile
    need to change, without altering any constructor signatures.
    """

    # --- Core Properties ---
    damage: int
    effects_to_apply: List[StatusEffect]
    status_effects_config: Dict[str, Any]

    # --- Behavioral Modifiers ---
    pierce_count: int = 0
    blast_radius: float = 0.0
    armor_shred: int = 0

    # --- Special Effect Payloads ---
    # These are lists of dictionaries, as they contain configuration data
    # that the projectile will use to create effects on the fly.
    on_blast_effects_data: List[Dict[str, Any]] = field(default_factory=list)
    conditional_effects: List[Dict[str, Any]] = field(default_factory=list)
    on_hit_area_effects: List[Dict[str, Any]] = field(default_factory=list)

    # --- Complex Damage Modifiers ---
    execute_threshold: Optional[Dict[str, float]] = None
    on_apply_damage: int = 0
    bonus_damage_per_debuff: int = 0
