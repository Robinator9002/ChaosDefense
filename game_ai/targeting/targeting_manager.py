# game_logic/targeting/targeting_manager.py
import logging
import math
from collections import defaultdict
from typing import List, Dict, Tuple, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from ...game_logic.entities.entity import Entity
    from ...game_logic.entities.tower import Tower
    from ...game_logic.entities.enemies.enemy import Enemy

logger = logging.getLogger(__name__)


class TargetingManager:
    """
    A centralized intelligence system for all entities on the battlefield.

    This manager uses a spatial hash grid to dramatically accelerate proximity
    queries (e.g., finding enemies in a tower's range). Instead of every tower
    checking every enemy (an O(N*M) operation), entities are registered into
    grid cells. Queries then only need to check entities in a small number of
    relevant cells, providing a massive performance boost, especially in
    late-game scenarios with many entities.
    """

    def __init__(self, cell_size: int = 100):
        """
        Initializes the TargetingManager.

        Args:
            cell_size (int): The width and height of each grid cell for the
                             spatial hash. A good starting value is roughly
                             the average tower attack range.
        """
        self.cell_size = cell_size
        # We maintain separate grids for different entity types to make
        # queries even faster (e.g., towers only query the enemy grid).
        self.enemy_grid: Dict[Tuple[int, int], List["Enemy"]] = defaultdict(list)
        self.tower_grid: Dict[Tuple[int, int], List["Tower"]] = defaultdict(list)

    def _get_cell_coords(self, position: pygame.Vector2) -> Tuple[int, int]:
        """Converts a world position (in pixels) to grid cell coordinates."""
        return (
            int(position.x // self.cell_size),
            int(position.y // self.cell_size),
        )

    def clear(self):
        """Clears all grids. This must be called at the start of each frame."""
        self.enemy_grid.clear()
        self.tower_grid.clear()

    def register_entity(self, entity: "Entity"):
        """
        Registers an entity into the appropriate spatial grid based on its type.
        This should be called for every active tower and enemy each frame.
        """
        cell_coords = self._get_cell_coords(entity.pos)

        # Use isinstance to determine which grid to place the entity in.
        # This is a robust way to handle class inheritance (e.g., BossEnemy is an Enemy).
        if isinstance(entity, pygame.sprite.Sprite) and "Enemy" in [
            cls.__name__ for cls in entity.__class__.__mro__
        ]:
            self.enemy_grid[cell_coords].append(entity)
        elif isinstance(entity, pygame.sprite.Sprite) and "Tower" in [
            cls.__name__ for cls in entity.__class__.__mro__
        ]:
            self.tower_grid[cell_coords].append(entity)

    def get_nearby_enemies(
        self, position: pygame.Vector2, radius: float
    ) -> List["Enemy"]:
        """
        Efficiently finds all enemies within a given radius of a position.
        """
        return self._get_nearby_entities(position, radius, self.enemy_grid)

    def get_nearby_towers(
        self, position: pygame.Vector2, radius: float
    ) -> List["Tower"]:
        """
        Efficiently finds all towers within a given radius of a position.
        """
        return self._get_nearby_entities(position, radius, self.tower_grid)

    def _get_nearby_entities(
        self,
        position: pygame.Vector2,
        radius: float,
        grid: Dict[Tuple[int, int], List["Entity"]],
    ) -> List["Entity"]:
        """
        The generic logic for querying a spatial grid.
        """
        entities_in_range: List["Entity"] = []
        radius_sq = radius * radius  # Use squared distances for performance

        # Determine the range of grid cells to check
        min_x = int((position.x - radius) // self.cell_size)
        max_x = int((position.x + radius) // self.cell_size)
        min_y = int((position.y - radius) // self.cell_size)
        max_y = int((position.y + radius) // self.cell_size)

        # Iterate through the relevant cells
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                cell_coords = (x, y)
                # For each entity in the cell, perform an exact distance check
                for entity in grid[cell_coords]:
                    if entity.is_alive:
                        distance_sq = position.distance_squared_to(entity.pos)
                        if distance_sq <= radius_sq:
                            entities_in_range.append(entity)

        return entities_in_range
