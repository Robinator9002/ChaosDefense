# level_generation/generator.py
import random
import logging
from typing import Tuple
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
            params (dict): A dictionary containing generation parameters.

        Returns:
            Grid: The same Grid instance, now populated with a level.
        """
        logger.info("Starting procedural level generation...")

        # --- Generation Sequence ---
        # The order of these operations is critical.

        # 1. Create an impassable border.
        LevelGenerator._create_border(grid)

        # 2. Place the base zone, which serves as the target for all paths.
        target_pos = LevelGenerator._place_base_zone(grid, size=4)

        # 3. Define the starting points for the paths.
        start_points = LevelGenerator._define_start_points(grid)

        # 4. (Phase 2) Generate paths from start points to the target.
        #    The old _create_path is removed. This logic will be replaced by A*.
        #    paths = LevelGenerator._create_paths(grid, start_points, target_pos)
        logger.info(
            f"Defined {len(start_points)} start points and target at {target_pos}."
        )

        # 5. Place terrain features around the established paths and base.
        features_params = params.get("features", {})
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
                tile_key = feature_key.rstrip("s").upper()
                LevelGenerator._place_terrain_feature(
                    grid, tile_key, min_count, max_count, placement_func
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
    def _place_base_zone(grid: Grid, size: int) -> Tuple[int, int]:
        """
        Places a square 'BASE_ZONE' on the right edge of the map.

        Args:
            grid (Grid): The grid to modify.
            size (int): The width and height of the base zone.

        Returns:
            Tuple[int, int]: The central coordinate of the base zone.
        """
        # Ensure base is not placed in the very corners.
        min_y = size
        max_y = grid.height - size - 1

        start_y = random.randint(min_y, max_y)
        start_x = grid.width - 1 - size

        for y in range(start_y, start_y + size):
            for x in range(start_x, start_x + size):
                if grid.is_valid_coord(x, y):
                    grid.set_tile_type(x, y, "BASE_ZONE")

        # Return the center point of the entrance to the base
        center_x = start_x
        center_y = start_y + size // 2
        return (center_x, center_y)

    @staticmethod
    def _define_start_points(grid: Grid) -> list[Tuple[int, int]]:
        """
        Defines three path starting points on the left edge of the map.

        Returns:
            list[Tuple[int, int]]: A list of (x, y) coordinates for the start points.
        """
        # Place start points at 1/4, 1/2, and 3/4 of the map's height.
        y_top = grid.height // 4
        y_mid = grid.height // 2
        y_bot = grid.height * 3 // 4

        return [(1, y_top), (1, y_mid), (1, y_bot)]

    @staticmethod
    def _place_terrain_feature(
        grid: Grid, tile_key: str, min_count: int, max_count: int, placement_func
    ):
        """A generic method to place a number of features on the grid."""
        if min_count > max_count:
            return

        count = random.randint(min_count, max_count)
        for _ in range(count):
            placement_func(grid, tile_key)

    @staticmethod
    def _place_cluster(grid: Grid, tile_key: str):
        """Places a rectangular cluster of tiles."""
        cluster_width = random.randint(2, 4)
        cluster_height = random.randint(2, 4)

        for _ in range(10):
            start_x = random.randint(1, grid.width - cluster_width - 1)
            start_y = random.randint(1, grid.height - cluster_height - 1)

            is_valid_spot = True
            for y in range(start_y, start_y + cluster_height):
                for x in range(start_x, start_x + cluster_width):
                    if (
                        not grid.is_valid_coord(x, y)
                        or grid.get_tile(x, y).tile_key != "BUILDABLE"
                    ):
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
        """Places a randomly shaped blob of tiles."""
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
        """Places a single tile in a random buildable location."""
        for _ in range(20):
            x = random.randint(1, grid.width - 2)
            y = random.randint(1, grid.height - 2)
            if grid.get_tile(x, y).tile_key == "BUILDABLE":
                grid.set_tile_type(x, y, tile_key)
                return
