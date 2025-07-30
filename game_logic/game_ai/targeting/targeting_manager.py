# game_ai/targeting/targeting_manager.py
import logging
import math
from collections import defaultdict
from typing import List, Dict, Tuple, TYPE_CHECKING, Any, Callable
import pygame

# --- NEW: Import the priority sorting functions ---
# We will create this file in the next step.
from . import targeting_priorities

if TYPE_CHECKING:
    # --- MODIFIED: Updated import paths for new file location ---
    from ...entities.entity import Entity
    from ...entities.tower import Tower
    from game_logic.entities.enemies.enemy import Enemy

logger = logging.getLogger(__name__)


class TargetingManager:
    """
    A centralized intelligence system for all entities on the battlefield.

    This manager uses a spatial hash grid to dramatically accelerate proximity
    queries. It also contains the logic for sorting potential targets based on
    a tower's currently selected AI persona, which is defined in data.
    """

    def __init__(self, cell_size: int, targeting_ai_config: Dict[str, Any]):
        """
        Initializes the TargetingManager.

        Args:
            cell_size (int): The width and height of each grid cell for the
                             spatial hash.
            targeting_ai_config (Dict[str, Any]): The loaded contents of
                                                 targeting_ai.json.
        """
        self.cell_size = cell_size
        self.targeting_ai_config = targeting_ai_config
        self.enemy_grid: Dict[Tuple[int, int], List["Enemy"]] = defaultdict(list)
        self.tower_grid: Dict[Tuple[int, int], List["Tower"]] = defaultdict(list)

        # This dispatch table maps the function name string from the config
        # to the actual sorting function in the targeting_priorities module.
        self.sorters: Dict[str, Callable] = {
            "sort_by_first": targeting_priorities.sort_by_first,
            "sort_by_last": targeting_priorities.sort_by_last,
            "sort_by_strongest": targeting_priorities.sort_by_strongest,
            "sort_by_weakest": targeting_priorities.sort_by_weakest,
            "sort_by_closest": targeting_priorities.sort_by_closest,
            "sort_by_highest_armor": targeting_priorities.sort_by_highest_armor,
            "sort_by_lowest_armor": targeting_priorities.sort_by_lowest_armor,
            "sort_by_group_density": targeting_priorities.sort_by_group_density,
            "sort_by_unaffected": targeting_priorities.sort_by_unaffected,
        }

    def _get_cell_coords(self, position: pygame.Vector2) -> Tuple[int, int]:
        """Converts a world position to grid cell coordinates."""
        return (
            int(position.x // self.cell_size),
            int(position.y // self.cell_size),
        )

    def clear(self):
        """Clears all grids. Must be called at the start of each frame."""
        self.enemy_grid.clear()
        self.tower_grid.clear()

    def register_entity(self, entity: "Entity"):
        """Registers an entity into the appropriate spatial grid."""
        cell_coords = self._get_cell_coords(entity.pos)
        # Use Method Resolution Order to robustly check for inherited types.
        if "Enemy" in [cls.__name__ for cls in entity.__class__.__mro__]:
            self.enemy_grid[cell_coords].append(entity)
        elif "Tower" in [cls.__name__ for cls in entity.__class__.__mro__]:
            self.tower_grid[cell_coords].append(entity)

    def get_nearby_enemies(
        self, position: pygame.Vector2, radius: float
    ) -> List["Enemy"]:
        """Efficiently finds all enemies within a given radius."""
        return self._get_nearby_entities(position, radius, self.enemy_grid)

    def get_nearby_towers(
        self, position: pygame.Vector2, radius: float
    ) -> List["Tower"]:
        """Efficiently finds all towers within a given radius."""
        return self._get_nearby_entities(position, radius, self.tower_grid)

    def _get_nearby_entities(
        self, position: pygame.Vector2, radius: float, grid: Dict
    ) -> List["Entity"]:
        """The generic logic for querying a spatial grid."""
        entities_in_range: List["Entity"] = []
        radius_sq = radius * radius

        min_x = int((position.x - radius) // self.cell_size)
        max_x = int((position.x + radius) // self.cell_size)
        min_y = int((position.y - radius) // self.cell_size)
        max_y = int((position.y + radius) // self.cell_size)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                for entity in grid.get((x, y), []):
                    if (
                        entity.is_alive
                        and position.distance_squared_to(entity.pos) <= radius_sq
                    ):
                        entities_in_range.append(entity)

        return entities_in_range

    def sort_targets(
        self, targets: List["Enemy"], tower: "Tower", persona_id: str
    ) -> List["Enemy"]:
        """
        Sorts a list of targets based on a tower's AI persona.
        """
        persona_data = self.targeting_ai_config.get(persona_id)
        if not persona_data:
            logger.warning(f"Unknown AI persona '{persona_id}'. Defaulting to closest.")
            return targeting_priorities.sort_by_closest(targets, tower, [])

        function_name = persona_data.get("priority_function")
        sorter = self.sorters.get(function_name)

        if not sorter:
            logger.error(f"No sorter function found for '{function_name}'.")
            return targets

        # For sorters that need global context, provide all enemies.
        all_enemies = [enemy for cell in self.enemy_grid.values() for enemy in cell]

        return sorter(targets, tower, all_enemies)
