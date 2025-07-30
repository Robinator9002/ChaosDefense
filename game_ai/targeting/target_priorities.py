# game_ai/targeting/targeting_priorities.py
import logging
from typing import List, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    # --- MODIFIED: Updated import paths for new file location ---
    from ...game_logic.entities.tower import Tower
    from ...game_logic.entities.enemies.enemy import Enemy

logger = logging.getLogger(__name__)

# --- Targeting Priority Functions ---
# Each function takes a list of potential targets and context (the firing tower
# and all enemies on the map) and returns a sorted list based on a specific
# strategic priority. This allows tower AI behavior to be highly specialized.


def sort_by_first(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
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
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
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
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """Sorts enemies by their maximum HP (highest first)."""
    return sorted(targets, key=lambda e: e.max_hp, reverse=True)


def sort_by_weakest(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """Sorts enemies by their current HP (lowest first)."""
    return sorted(targets, key=lambda e: e.current_hp)


def sort_by_closest(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """Sorts enemies by their distance to the tower (closest first)."""
    return sorted(targets, key=lambda e: tower.pos.distance_squared_to(e.pos))


def sort_by_highest_armor(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """Sorts enemies by their current armor value (highest first)."""
    return sorted(targets, key=lambda e: e.armor, reverse=True)


def sort_by_lowest_armor(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """Sorts enemies by their current armor value (lowest first)."""
    return sorted(targets, key=lambda e: e.armor)


def sort_by_group_density(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """Sorts enemies by the number of other enemies near them (densest group first)."""
    density_radius_sq = 75 * 75  # Check for other enemies in a 75px radius

    def count_nearby(enemy: "Enemy"):
        count = 0
        for other in all_enemies:
            if (
                enemy is not other
                and enemy.pos.distance_squared_to(other.pos) <= density_radius_sq
            ):
                count += 1
        return count

    return sorted(targets, key=count_nearby, reverse=True)


def sort_by_unaffected(
    targets: List["Enemy"], tower: "Tower", all_enemies: List["Enemy"]
) -> List["Enemy"]:
    """
    Sorts enemies to prioritize those not currently affected by the tower's
    primary status effect (e.g., 'slow' for a Freezer).
    """
    primary_effect_id = None
    effects_data = tower.attack_data.get("data", {}).get("effects", {})
    if effects_data:
        primary_effect_id = next(iter(effects_data))

    if not primary_effect_id:
        return sort_by_closest(targets, tower, all_enemies)

    # Sort key is a boolean: False (0) for unaffected, True (1) for affected.
    # This puts all unaffected enemies at the front of the list.
    return sorted(
        targets,
        key=lambda e: any(
            eff.effect_id == primary_effect_id
            for eff in e.effect_handler.status_effects
        ),
    )
