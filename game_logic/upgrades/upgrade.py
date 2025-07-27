# game_logic/upgrades/upgrade.py
from dataclasses import dataclass
from typing import Dict, Any

# It's good practice to create a new directory for a new system.
# This file would live in a path like: project/game_logic/upgrades/upgrade.py


@dataclass(frozen=True)
class Upgrade:
    """
    A data class representing a single, specific upgrade for a tower.

    This object is a direct Python representation of an upgrade entry from the
    upgrade_definitions.json configuration file. It is immutable (`frozen=True`)
    to prevent its state from being accidentally modified after creation. It serves
    as a clean data container that is passed from the data layer to the logic
    and UI layers.

    Attributes:
        id (str): A unique identifier for this specific upgrade,
                  e.g., "turret_a1".
        name (str): The human-readable name of the upgrade,
                    e.g., "Increased Damage".
        cost (int): The amount of gold required to purchase this upgrade.
        description (str): A short description of the upgrade's effect,
                           used for UI tooltips.
        effects (Dict[str, Any]): A dictionary containing the mechanical
                                 effects of the upgrade. The keys are action
                                 names (e.g., "add_damage") and the values are
                                 the parameters for that action.
    """

    id: str
    name: str
    cost: int
    description: str
    effects: Dict[str, Any]
