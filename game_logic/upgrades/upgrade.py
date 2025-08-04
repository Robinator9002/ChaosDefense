# game_logic/upgrades/upgrade.py
from dataclasses import dataclass
from typing import Dict, Any, List

# It's good practice to create a new directory for a new system.
# This file would live in a path like: project/game_logic/upgrades/upgrade.py


@dataclass(frozen=True)
class Upgrade:
    """
    A data class representing a single, specific upgrade for a tower.

    This object is a direct Python representation of an upgrade entry from the
    upgrade definition JSON files. It is immutable (`frozen=True`) to prevent
    its state from being accidentally modified after creation.

    Attributes:
        id (str): A unique identifier for this specific upgrade, e.g., "turret_a1".
        name (str): The human-readable name of the upgrade.
        cost (int): The amount of gold required to purchase this upgrade.
        description (str): A short description of the upgrade's effect.
        path (str): The upgrade path this belongs to, either "a" or "b".
        effects (List[Dict[str, Any]]): A list of dictionaries, each defining a
                                        mechanical effect of the upgrade.
    """

    id: str
    name: str
    cost: int
    description: str
    path: str  # --- NEW: Explicitly define the upgrade path (Issue #3) ---
    effects: List[Dict[str, Any]]
