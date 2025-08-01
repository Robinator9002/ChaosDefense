# game_logic/game_ai/targeting/targeting_priorities.py
import logging
from typing import List, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from ...entities.tower import Tower
    from ...entities.enemies.enemy import Enemy

    # --- NEW: Import TargetingManager for type hinting and its methods ---
    from .targeting_manager import TargetingManager

logger = logging.getLogger(__name__)

# --- Targeting Priority Functions ---
# REFACTORED: All sorter functions now accept the TargetingManager instance
# to allow for advanced, performant queries.


def sort_by_first(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies based on their progress along the path (furthest first)."""

    def sort_key(enemy: "Enemy"):
        if enemy.current_waypoint_index < len(enemy.pixel_path):
            next_waypoint = enemy.pixel_path[enemy.current_waypoint_index]
            dist_to_next = enemy.pos.distance_squared_to(next_waypoint)
            return (-enemy.current_waypoint_index, dist_to_next)
        return (-enemy.current_waypoint_index, 0)

    return sorted(targets, key=sort_key)


def sort_by_last(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies based on their progress along the path (least progress first)."""

    def sort_key(enemy: "Enemy"):
        if enemy.current_waypoint_index < len(enemy.pixel_path):
            next_waypoint = enemy.pixel_path[enemy.current_waypoint_index]
            dist_to_next = enemy.pos.distance_squared_to(next_waypoint)
            return (enemy.current_waypoint_index, -dist_to_next)
        return (enemy.current_waypoint_index, 0)

    return sorted(targets, key=sort_key)


def sort_by_strongest(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies by their maximum HP (highest first)."""
    return sorted(targets, key=lambda e: e.max_hp, reverse=True)


def sort_by_weakest(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies by their current HP (lowest first)."""
    return sorted(targets, key=lambda e: e.current_hp)


def sort_by_closest(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies by their distance to the tower (closest first)."""
    return sorted(targets, key=lambda e: tower.pos.distance_squared_to(e.pos))


def sort_by_highest_armor(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies by their current armor value (highest first)."""
    return sorted(targets, key=lambda e: e.armor, reverse=True)


def sort_by_lowest_armor(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """Sorts enemies by their current armor value (lowest first)."""
    return sorted(targets, key=lambda e: e.armor)


def sort_by_group_density(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """
    Sorts enemies by the number of other enemies near them.

    OPTIMIZED: This function no longer iterates through all enemies on the map.
    Instead, it uses a single, highly efficient query to the TargetingManager
    for each enemy, dramatically improving performance in dense waves.
    """
    # --- DYNAMIC RADIUS: Use the tower's blast radius for the check ---
    # This makes the targeting behavior intelligently adapt to the tower's upgrades.
    # We use a fallback radius for towers that have no blast radius.
    density_radius = tower.blast_radius if tower.blast_radius > 0 else 75.0

    def count_nearby(enemy: "Enemy"):
        # The query to the targeting manager is extremely fast.
        nearby_enemies = targeting_manager.get_nearby_enemies(enemy.pos, density_radius)
        # We subtract 1 to not count the enemy itself.
        return len(nearby_enemies) - 1

    return sorted(targets, key=count_nearby, reverse=True)


def sort_by_unaffected(
    targets: List["Enemy"], tower: "Tower", targeting_manager: "TargetingManager"
) -> List["Enemy"]:
    """
    Sorts enemies to prioritize those not currently affected by the tower's
    primary status effect (e.g., 'slow' for a Freezer).
    """
    primary_effect_id = None
    effects_data = tower.attack.get("data", {}).get("effects", {})
    if effects_data:
        primary_effect_id = next(iter(effects_data))

    if not primary_effect_id:
        return sort_by_closest(targets, tower, targeting_manager)

    return sorted(
        targets,
        key=lambda e: any(
            eff.effect_id == primary_effect_id
            for eff in e.effect_handler.status_effects
        ),
    )
