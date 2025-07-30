# game_logic/targeting/targeting_priorities.py
import logging
from typing import List, TYPE_CHECKING, Tuple
import pygame

if TYPE_CHECKING:
    from ...game_logic.entities.enemies import Enemy

logger = logging.getLogger(__name__)

# --- Targeting Priority Functions ---
# Each function in this module takes a list of potential enemy targets and
# returns a sorted list based on a specific strategic priority. This allows
# tower targeting behavior to be defined in data and easily extended.


def sort_by_first(targets: List["Enemy"], tower_pos: "pygame.Vector2") -> List["Enemy"]:
    """Sorts enemies based on their progress along the path (furthest first)."""

    def sort_key(enemy: "Enemy") -> Tuple[int, float]:
        # Primary key: waypoint index (higher is further along the path).
        # Secondary key: inverse distance to the *next* waypoint (smaller is further).
        # A smaller distance means they are closer to completing that waypoint segment.
        if enemy.current_waypoint_index < len(enemy.pixel_path):
            next_waypoint = enemy.pixel_path[enemy.current_waypoint_index]
            dist_to_next = enemy.pos.distance_squared_to(next_waypoint)
            return (-enemy.current_waypoint_index, dist_to_next)
        return (-enemy.current_waypoint_index, 0)

    return sorted(targets, key=sort_key)


def sort_by_last(targets: List["Enemy"], tower_pos: "pygame.Vector2") -> List["Enemy"]:
    """Sorts enemies based on their progress along the path (least progress first)."""

    def sort_key(enemy: "Enemy") -> Tuple[int, float]:
        # Primary key: waypoint index (lower is less progress).
        # Secondary key: distance to the *next* waypoint (larger is less progress).
        if enemy.current_waypoint_index < len(enemy.pixel_path):
            next_waypoint = enemy.pixel_path[enemy.current_waypoint_index]
            dist_to_next = enemy.pos.distance_squared_to(next_waypoint)
            return (enemy.current_waypoint_index, -dist_to_next)
        return (enemy.current_waypoint_index, 0)

    return sorted(targets, key=sort_key)


def sort_by_strongest(
    targets: List["Enemy"], tower_pos: "pygame.Vector2"
) -> List["Enemy"]:
    """Sorts enemies by their maximum HP (highest first)."""
    return sorted(targets, key=lambda e: e.max_hp, reverse=True)


def sort_by_weakest(
    targets: List["Enemy"], tower_pos: "pygame.Vector2"
) -> List["Enemy"]:
    """Sorts enemies by their current HP (lowest first)."""
    return sorted(targets, key=lambda e: e.current_hp)


def sort_by_closest(
    targets: List["Enemy"], tower_pos: "pygame.Vector2"
) -> List["Enemy"]:
    """Sorts enemies by their distance to the tower (closest first)."""
    return sorted(targets, key=lambda e: tower_pos.distance_squared_to(e.pos))
