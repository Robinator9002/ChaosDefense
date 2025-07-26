# level_generation/grid.py
from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Tile:
    """
    Represents a single tile on the game grid.

    This is a pure data class. It holds its position and a 'key' that
    references its type and properties defined in the level style configuration.
    For example, a tile_key of "MOUNTAIN" would be linked to the MOUNTAIN
    definition in level_styles.json.
    """

    x: int
    y: int
    tile_key: str  # e.g., "PATH", "BUILDABLE", "MOUNTAIN"


class Grid:
    """
    Represents the entire game map as a 2D grid of Tile objects.

    This class manages the logical structure of the level, providing methods
    to access and modify tiles. It knows nothing about rendering, pathfinding,
    or game rules; it is simply a container for the level's layout.
    """

    def __init__(self, width: int, height: int):
        """
        Initializes the grid with given dimensions.

        Args:
            width (int): The number of tiles in the x-direction.
            height (int): The number of tiles in the y-direction.
        """
        if (
            not isinstance(width, int)
            or not isinstance(height, int)
            or width <= 0
            or height <= 0
        ):
            raise ValueError("Grid dimensions must be positive integers.")

        self.width = width
        self.height = height

        # The grid is stored as a list of lists (rows), where grid[y][x] is the standard access pattern.
        self._grid: list[list[Tile]] = []
        self._initialize_grid()
        logger.info(f"Initialized a {width}x{height} grid.")

    def _initialize_grid(self, default_tile_key: str = "BUILDABLE"):
        """
        Fills the grid with default Tile objects.

        Args:
            default_tile_key (str): The key for the default tile type,
                                    typically "BUILDABLE".
        """
        self._grid = [
            [Tile(x, y, default_tile_key) for x in range(self.width)]
            for y in range(self.height)
        ]

    def is_valid_coord(self, x: int, y: int) -> bool:
        """
        Checks if a given coordinate is within the bounds of the grid.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.

        Returns:
            bool: True if the coordinate is valid, False otherwise.
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> Tile | None:
        """
        Retrieves the Tile object at a specific coordinate.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.

        Returns:
            Tile | None: The Tile object if the coordinate is valid,
                         otherwise None.
        """
        if not self.is_valid_coord(x, y):
            return None
        return self._grid[y][x]

    def set_tile_type(self, x: int, y: int, tile_key: str):
        """
        Changes the type of a tile at a specific coordinate.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            tile_key (str): The new key for the tile's type (e.g., "PATH").

        Raises:
            IndexError: If the coordinates are out of bounds.
        """
        if not self.is_valid_coord(x, y):
            raise IndexError(
                f"Coordinate ({x}, {y}) is out of grid bounds ({self.width}x{self.height})."
            )

        self._grid[y][x].tile_key = tile_key
