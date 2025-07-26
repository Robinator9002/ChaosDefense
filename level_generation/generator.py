# level_generation/generator.py
import random
import logging
from .grid import Grid

logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    A static class responsible for procedural level generation.

    It takes a Grid object and populates it with terrain features based on
    a dictionary of parameters, making it a reusable and data-driven tool.
    """

    @staticmethod
    def generate(grid: Grid, params: dict) -> Grid:
        """
        Orchestrates the level generation process using provided parameters.

        Args:
            grid (Grid): The Grid instance to be populated.
            params (dict): A dictionary containing generation parameters,
                           typically from a level style preset.

        Returns:
            Grid: The same Grid instance, now populated with a level.
        """
        logger.info("Starting procedural level generation with provided parameters...")

        LevelGenerator._create_border(grid)
        LevelGenerator._create_path(grid)

        features_params = params.get("features", {})

        # Define the features to be placed and their corresponding placement functions.
        # This makes it easy to add new feature types in the future.
        feature_map = {
            "mountains": LevelGenerator._place_cluster,
            "lakes": LevelGenerator._place_blob,
            "trees": LevelGenerator._place_scatter,
        }

        for feature_key, placement_func in feature_map.items():
            feature_config = features_params.get(feature_key)

            if feature_config and isinstance(feature_config, dict):
                min_count = feature_config.get("min", 0)
                max_count = feature_config.get("max", 0)

                # Derive the tile key (e.g., "mountains" -> "MOUNTAIN")
                tile_key = feature_key.rstrip("s").upper()

                LevelGenerator._place_terrain_feature(
                    grid, tile_key, min_count, max_count, placement_func
                )
            else:
                logger.debug(f"No valid config for feature '{feature_key}', skipping.")

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
        """
        start_y = grid.height // 2 + random.randint(-grid.height // 6, grid.height // 6)
        pos = (1, start_y)
        path_coords = []

        while pos[0] < grid.width - 1:
            path_coords.append(pos)
            grid.set_tile_type(pos[0], pos[1], "PATH")

            potential_moves = {
                "right": ((pos[0] + 1, pos[1]), 10),
                "up": ((pos[0], pos[1] - 1), 1),
                "down": ((pos[0], pos[1] + 1), 1),
            }

            valid_moves = []
            weights = []
            for move, (coord, weight) in potential_moves.items():
                if (
                    grid.is_valid_coord(coord[0], coord[1])
                    and grid.get_tile(coord[0], coord[1]).tile_key != "BORDER"
                    and coord not in path_coords
                ):
                    valid_moves.append(coord)
                    weights.append(weight)

            if not valid_moves:
                logger.warning("Path generation got stuck. Path may be incomplete.")
                break

            pos = random.choices(valid_moves, weights=weights, k=1)[0]

    @staticmethod
    def _place_terrain_feature(
        grid: Grid, tile_key: str, min_count: int, max_count: int, placement_func
    ):
        """
        A generic method to place a number of features on the grid.
        """
        if min_count > max_count:
            logger.warning(
                f"For '{tile_key}', min_count ({min_count}) > max_count ({max_count}). Skipping."
            )
            return

        count = random.randint(min_count, max_count)
        for _ in range(count):
            placement_func(grid, tile_key)

    @staticmethod
    def _place_cluster(grid: Grid, tile_key: str):
        """Places a rectangular cluster of tiles (e.g., for mountains)."""
        cluster_width = random.randint(2, 4)
        cluster_height = random.randint(2, 4)

        for _ in range(10):
            start_x = random.randint(1, grid.width - cluster_width - 1)
            start_y = random.randint(1, grid.height - cluster_height - 1)

            is_valid_spot = True
            for y in range(start_y, start_y + cluster_height):
                for x in range(start_x, start_x + cluster_width):
                    if grid.get_tile(x, y).tile_key != "BUILDABLE":
                        is_valid_spot = False
                        break
                if not is_valid_spot:
                    break

            if is_valid_spot:
                for y in range(start_y, start_y + cluster_height):
                    for x in range(start_x, start_x + cluster_width):
                        grid.set_tile_type(x, y, tile_key)
                return

    @staticmethod
    def _place_blob(grid: Grid, tile_key: str):
        """Places a randomly shaped blob of tiles (e.g., for lakes)."""
        blob_size = random.randint(5, 12)

        for _ in range(10):
            start_x = random.randint(1, grid.width - 2)
            start_y = random.randint(1, grid.height - 2)

            if grid.get_tile(start_x, start_y).tile_key == "BUILDABLE":
                blob_coords = set()
                q = [(start_x, start_y)]

                while q and len(blob_coords) < blob_size:
                    x, y = q.pop(0)
                    if (
                        (x, y) in blob_coords
                        or not grid.is_valid_coord(x, y)
                        or grid.get_tile(x, y).tile_key != "BUILDABLE"
                    ):
                        continue

                    blob_coords.add((x, y))

                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        if random.random() > 0.4:
                            q.append((x + dx, y + dy))

                for x, y in blob_coords:
                    grid.set_tile_type(x, y, tile_key)
                return

    @staticmethod
    def _place_scatter(grid: Grid, tile_key: str):
        """Places a single tile in a random buildable location (e.g., for trees)."""
        for _ in range(20):
            x = random.randint(1, grid.width - 2)
            y = random.randint(1, grid.height - 2)
            if grid.get_tile(x, y).tile_key == "BUILDABLE":
                grid.set_tile_type(x, y, tile_key)
                return
