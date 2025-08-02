# game_logic/game_ai/targeting/targeting_manager.py
import logging
import math
from collections import defaultdict
from typing import List, Dict, Tuple, TYPE_CHECKING, Any, Callable
import pygame
import uuid

from . import targeting_priorities

if TYPE_CHECKING:
    from ...entities.entity import Entity
    from ...entities.tower import Tower
    from ...entities.enemies.enemy import Enemy

logger = logging.getLogger(__name__)


class TargetingManager:
    """
    A centralized, stateful intelligence system for all entities.

    This manager uses a persistent spatial hash grid to dramatically accelerate
    proximity queries. Instead of being rebuilt every frame, it is now updated
    incrementally as entities are added, removed, or moved. This is a critical
    performance optimization.
    """

    def __init__(self, cell_size: int, targeting_ai_config: Dict[str, Any]):
        """
        Initializes the TargetingManager.
        """
        self.cell_size = cell_size
        self.targeting_ai_config = targeting_ai_config

        # --- The spatial hash grids ---
        self.enemy_grid: Dict[Tuple[int, int], List["Enemy"]] = defaultdict(list)
        self.tower_grid: Dict[Tuple[int, int], List["Tower"]] = defaultdict(list)

        self._entity_cell_map: Dict[uuid.UUID, Tuple[int, int]] = {}

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

    def add_entity(self, entity: "Entity"):
        """
        Adds a new entity to the appropriate spatial grid and tracks its cell.
        """
        cell_coords = self._get_cell_coords(entity.pos)

        if "Enemy" in [cls.__name__ for cls in entity.__class__.__mro__]:
            self.enemy_grid[cell_coords].append(entity)
        elif "Tower" in [cls.__name__ for cls in entity.__class__.__mro__]:
            self.tower_grid[cell_coords].append(entity)

        self._entity_cell_map[entity.entity_id] = cell_coords

    def remove_entity(self, entity: "Entity"):
        """
        Removes an entity from the spatial grid and stops tracking it.
        """
        if entity.entity_id not in self._entity_cell_map:
            return

        last_known_cell = self._entity_cell_map[entity.entity_id]

        try:
            if "Enemy" in [cls.__name__ for cls in entity.__class__.__mro__]:
                if entity in self.enemy_grid[last_known_cell]:
                    self.enemy_grid[last_known_cell].remove(entity)
            elif "Tower" in [cls.__name__ for cls in entity.__class__.__mro__]:
                if entity in self.tower_grid[last_known_cell]:
                    self.tower_grid[last_known_cell].remove(entity)
        except ValueError:
            logger.warning(
                f"Attempted to remove entity {entity.entity_id} which was not in its tracked cell."
            )

        del self._entity_cell_map[entity.entity_id]

    def update_entity_position(self, entity: "Entity"):
        """
        Checks if a moving entity has crossed into a new cell and updates the
        grid accordingly.
        """
        if entity.entity_id not in self._entity_cell_map:
            return

        last_known_cell = self._entity_cell_map[entity.entity_id]
        current_cell = self._get_cell_coords(entity.pos)

        if last_known_cell != current_cell:
            try:
                if "Enemy" in [cls.__name__ for cls in entity.__class__.__mro__]:
                    if entity in self.enemy_grid[last_known_cell]:
                        self.enemy_grid[last_known_cell].remove(entity)
                    self.enemy_grid[current_cell].append(entity)
            except ValueError:
                logger.warning(
                    f"Attempted to update entity {entity.entity_id} which was not in its tracked cell."
                )

            self._entity_cell_map[entity.entity_id] = current_cell

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
            # --- REFACTORED: Pass self instead of empty list ---
            return targeting_priorities.sort_by_closest(targets, tower, self)

        function_name = persona_data.get("priority_function")
        sorter = self.sorters.get(function_name)

        if not sorter:
            logger.error(f"No sorter function found for '{function_name}'.")
            return targets

        # --- REFACTORED: Pass the TargetingManager instance itself ---
        # Instead of passing a slow, pre-compiled list of all enemies, we now
        # pass the manager itself. This gives sorter functions access to its
        # highly efficient query methods, like get_nearby_enemies.
        return sorter(targets, tower, self)
