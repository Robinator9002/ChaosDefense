# level_generation/generator.py
import random
import logging
from .grid import Grid

logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    A static class responsible for procedural level generation.

    It takes a Grid object and populates it with terrain features like paths,
    obstacles, and buildable areas based on a given style configuration.
    """

    @staticmethod
    def generate(grid: Grid) -> Grid:
        """
        Orchestrates the entire level generation process.

        This method follows a specific sequence to ensure a valid and
        interesting level layout. The path is generated first to guarantee
        it is not blocked, followed by major and minor terrain features.

        Args:
            grid (Grid): The Grid instance to be populated.

        Returns:
            Grid: The same Grid instance, now populated with a level.
        """
        logger.info("Starting procedural level generation...")

        # The order of these operations is important.
        LevelGenerator._create_border(grid)
        LevelGenerator._create_path(grid)

        # Place major features (mountains, lakes)
        LevelGenerator._place_terrain_feature(
            grid, "MOUNTAIN", 3, 5, LevelGenerator._place_cluster
        )
        LevelGenerator._place_terrain_feature(
            grid, "LAKE", 2, 4, LevelGenerator._place_blob
        )

        # Place minor features (trees) that can fill remaining space
        LevelGenerator._place_terrain_feature(
            grid, "TREE", 40, 80, LevelGenerator._place_scatter
        )

        logger.info("Level generation complete.")
        return grid

    @staticmethod
    def _create_border(grid: Grid):
        """Fills the outermost edge of the grid with 'BORDER' tiles."""
        for x in range(grid.width):
            grid.set_tile_type(x, 0, "BORDER")
            grid.set_tile_type(x, grid.height - 1, "BORDER")
        for y in range(grid.height):
            grid.set_tile_type(0, y, "BORDER")
            grid.set_tile_type(grid.width - 1, y, "BORDER")

    @staticmethod
    def _create_path(grid: Grid):
        """
        Generates a guaranteed path from the left to the right side of the grid.

        Uses a "drunken walk" algorithm with a strong bias to move rightward,
        ensuring a continuous but varied path for enemies.
        """
        # Start the path on the left edge (inside the border)
        start_y = grid.height // 2 + random.randint(-grid.height // 6, grid.height // 6)
        pos = (1, start_y)
        path_coords = []

        while pos[0] < grid.width - 1:
            path_coords.append(pos)
            grid.set_tile_type(pos[0], pos[1], "PATH")

            # Define potential next moves and their weights
            potential_moves = {
                "right": ((pos[0] + 1, pos[1]), 10),  # Strong bias to move right
                "up": ((pos[0], pos[1] - 1), 1),
                "down": ((pos[0], pos[1] + 1), 1),
            }

            valid_moves = []
            weights = []
            for move, (coord, weight) in potential_moves.items():
                # A move is valid if it's within the border and not already part of the path
                if (
                    grid.is_valid_coord(coord[0], coord[1])
                    and grid.get_tile(coord[0], coord[1]).tile_key != "BORDER"
                    and coord not in path_coords
                ):
                    valid_moves.append(coord)
                    weights.append(weight)

            if not valid_moves:
                # If stuck (highly unlikely with this setup), break the loop
                logger.warning("Path generation got stuck. Path may be incomplete.")
                break

            # Choose the next position based on the weighted probabilities
            pos = random.choices(valid_moves, weights=weights, k=1)[0]

    @staticmethod
    def _place_terrain_feature(
        grid: Grid, tile_key: str, min_count: int, max_count: int, placement_func
    ):
        """
        A generic method to place a number of features on the grid.

        Args:
            grid (Grid): The grid to modify.
            tile_key (str): The key of the tile to place (e.g., "MOUNTAIN").
            min_count (int): The minimum number of features/clusters to place.
            max_count (int): The maximum number of features/clusters to place.
            placement_func (function): The specific function to use for placing one feature.
        """
        count = random.randint(min_count, max_count)
        for _ in range(count):
            # The placement function is responsible for finding a valid spot
            placement_func(grid, tile_key)

    @staticmethod
    def _place_cluster(grid: Grid, tile_key: str):
        """Places a rectangular cluster of tiles (e.g., for mountains)."""
        cluster_width = random.randint(2, 4)
        cluster_height = random.randint(2, 4)

        # Try a few times to find a valid spot
        for _ in range(10):  # 10 placement attempts
            start_x = random.randint(1, grid.width - cluster_width - 1)
            start_y = random.randint(1, grid.height - cluster_height - 1)

            # Check if the entire area is clear for placement
            is_valid_spot = True
            for y in range(start_y, start_y + cluster_height):
                for x in range(start_x, start_x + cluster_width):
                    if grid.get_tile(x, y).tile_key != "BUILDABLE":
                        is_valid_spot = False
                        break
                if not is_valid_spot:
                    break

            if is_valid_spot:
                # Place the cluster
                for y in range(start_y, start_y + cluster_height):
                    for x in range(start_x, start_x + cluster_width):
                        grid.set_tile_type(x, y, tile_key)
                return  # Successfully placed, exit the function

    @staticmethod
    def _place_blob(grid: Grid, tile_key: str):
        """Places a randomly shaped blob of tiles (e.g., for lakes)."""
        blob_size = random.randint(5, 12)

        for _ in range(10):  # 10 placement attempts
            start_x = random.randint(1, grid.width - 2)
            start_y = random.randint(1, grid.height - 2)

            if grid.get_tile(start_x, start_y).tile_key == "BUILDABLE":
                # Start the blob formation
                blob_coords = set()
                q = [(start_x, start_y)]

                while q and len(blob_coords) < blob_size:
                    x, y = q.pop(0)
                    if (x, y) in blob_coords or grid.get_tile(
                        x, y
                    ).tile_key != "BUILDABLE":
                        continue

                    blob_coords.add((x, y))

                    # Add neighbors to the queue with a chance
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        if random.random() > 0.4:  # Chance to not expand in a direction
                            q.append((x + dx, y + dy))

                # Convert the valid coordinates to tiles
                for x, y in blob_coords:
                    grid.set_tile_type(x, y, tile_key)
                return

    @staticmethod
    def _place_scatter(grid: Grid, tile_key: str):
        """Places a single tile in a random buildable location (e.g., for trees)."""
        for _ in range(20):  # 20 placement attempts
            x = random.randint(1, grid.width - 2)
            y = random.randint(1, grid.height - 2)
            if grid.get_tile(x, y).tile_key == "BUILDABLE":
                grid.set_tile_type(x, y, tile_key)
                return
