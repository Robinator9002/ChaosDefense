# level_generation/generator.py
import random
import logging
from typing import Tuple, List, Callable

from .grid import Grid
from game_logic.pathfinding.pathfinder import Pathfinder

logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    A static class responsible for procedural level generation.

    This class acts as a "dungeon master" for creating levels. It uses a
    Pathfinder utility to create multiple, distinct enemy paths and then
    populates the grid with terrain features based on parameters from a
    level style configuration.
    """

    @staticmethod
    def generate(grid: Grid, params: dict) -> Tuple[Grid, List[List[Tuple[int, int]]]]:
        """
        Orchestrates the entire level generation process.

        The generation follows a strict sequence to ensure logical and playable maps:
        1. Border Creation: Seals the map edges.
        2. Base & Start Placement: Defines the objective and spawn points.
        3. Path Generation: Creates routes between spawns and the base. This is
           done *before* placing obstacles to guarantee paths are always possible.
        4. Path Carving: Makes the calculated paths visually distinct on the grid.
        5. Feature Placement: Scatters obstacles like mountains and trees around
           the established paths.

        Args:
            grid (Grid): The Grid instance to be populated.
            params (dict): A dictionary containing generation parameters.

        Returns:
            A tuple containing the populated Grid and a list of the generated enemy paths.
        """
        logger.info("Starting procedural level generation with A* pathfinding...")

        # --- Generation Sequence ---
        LevelGenerator._create_border(grid)
        target_pos = LevelGenerator._place_base_zone(grid, size=4)
        start_points = LevelGenerator._define_start_points(grid)

        paths = LevelGenerator._create_paths(grid, start_points, target_pos)
        if not paths:
            logger.error(
                "Failed to generate any valid paths. Aborting feature placement."
            )
            return grid, []

        for path in paths:
            for x, y in path:
                if grid.get_tile(x, y).tile_key != "BASE_ZONE":
                    grid.set_tile_type(x, y, "PATH")

        features_params = params.get("features", {})
        feature_map = {
            "mountains": LevelGenerator._place_cluster,
            "lakes": LevelGenerator._place_blob,
            "trees": LevelGenerator._place_scatter,
        }
        for feature_key, placement_func in feature_map.items():
            feature_config = features_params.get(feature_key)
            if feature_config and isinstance(feature_config, dict):
                min_count, max_count = feature_config.get("min", 0), feature_config.get(
                    "max", 0
                )
                tile_key = feature_key.rstrip("s").upper()
                LevelGenerator._place_terrain_feature(
                    grid, tile_key, min_count, max_count, placement_func
                )

        logger.info("Level generation complete.")
        return grid, paths

    @staticmethod
    def _create_paths(
        grid: Grid, starts: list, target: tuple
    ) -> List[List[Tuple[int, int]]]:
        """
        Creates three distinct paths using different A* cost functions.

        This method generates each path sequentially. After a path is found, its
        tiles are temporarily marked as "TEMP_PATH". This allows subsequent
        pathfinding runs to "see" the existing path and be heavily penalized
        for crossing or following it, forcing them to find unique routes.
        """
        all_paths = []

        # --- Path 1: The Direct Route (Middle) ---
        # This path uses the default cost, resulting in the most direct A* route.
        path1 = Pathfinder.find_path(grid, starts[1], target)
        if path1:
            all_paths.append(path1)
            for x, y in path1:
                grid.get_tile(x, y).tile_key = "TEMP_PATH"

        # --- Path 2: The Wandering Route (Top) ---
        # This cost function introduces randomness, making the path less direct.
        def wandering_cost(pos: Tuple[int, int]) -> float:
            """Assigns a high cost to existing paths and a random cost otherwise."""
            tile = grid.get_tile(pos[0], pos[1])
            if tile.tile_key == "TEMP_PATH":
                return 100.0  # High cost makes the algorithm avoid this tile.
            return random.uniform(1.0, 3.0)  # Random cost encourages zig-zagging.

        path2 = Pathfinder.find_path(grid, starts[0], target, wandering_cost)
        if path2:
            all_paths.append(path2)
            for x, y in path2:
                grid.get_tile(x, y).tile_key = "TEMP_PATH"

        # --- Path 3: The Side-Hugging Route (Bottom) ---
        # This cost function is weighted by the tile's position on the grid.
        def side_hugging_cost(pos: Tuple[int, int]) -> float:
            """Prefers staying low on the map for the first half of the journey."""
            tile = grid.get_tile(pos[0], pos[1])
            if tile.tile_key == "TEMP_PATH":
                return 100.0  # High cost to avoid other paths.

            # For the first 60% of the map's width, make higher tiles more "expensive".
            # This incentivizes the pathfinder to stay near the bottom edge.
            if pos[0] < grid.width * 0.6:
                return 1.0 + (pos[1] / 4.0)  # Cost increases with y-coordinate.
            return 1.0  # Normal cost for the final stretch to the base.

        path3 = Pathfinder.find_path(grid, starts[2], target, side_hugging_cost)
        if path3:
            all_paths.append(path3)

        # --- Cleanup ---
        # After all paths are found, reset the temporary markers back to buildable.
        for y in range(grid.height):
            for x in range(grid.width):
                if grid.get_tile(x, y).tile_key == "TEMP_PATH":
                    grid.set_tile_type(x, y, "BUILDABLE")

        return all_paths

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
        """Places a square 'BASE_ZONE' on the right edge of the map."""
        min_y, max_y = size, grid.height - size - 1
        start_y = random.randint(min_y, max_y)
        start_x = grid.width - 1 - size
        for y in range(start_y, start_y + size):
            for x in range(start_x, start_x + size):
                if grid.is_valid_coord(x, y):
                    grid.set_tile_type(x, y, "BASE_ZONE")
        # The target for pathfinding is the entrance, not the center of the base.
        return (start_x, start_y + size // 2)

    @staticmethod
    def _define_start_points(grid: Grid) -> list[Tuple[int, int]]:
        """Defines three path starting points on the left edge of the map."""
        y_top, y_mid, y_bot = grid.height // 4, grid.height // 2, grid.height * 3 // 4
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
        """Places a rectangular cluster of tiles, avoiding existing paths."""
        cluster_w, cluster_h = random.randint(2, 4), random.randint(2, 4)
        for _ in range(10):  # Attempt to place 10 times before giving up.
            start_x, start_y = random.randint(
                1, grid.width - cluster_w - 1
            ), random.randint(1, grid.height - cluster_h - 1)
            # Check if the entire area is buildable before placing.
            if all(
                grid.is_valid_coord(x, y)
                and grid.get_tile(x, y).tile_key == "BUILDABLE"
                for y in range(start_y, start_y + cluster_h)
                for x in range(start_x, start_x + cluster_w)
            ):
                for y in range(start_y, start_y + cluster_h):
                    for x in range(start_x, start_x + cluster_w):
                        grid.set_tile_type(x, y, tile_key)
                return

    @staticmethod
    def _place_blob(grid: Grid, tile_key: str):
        """Places a randomly shaped blob of tiles, avoiding existing paths."""
        blob_size = random.randint(5, 12)
        for _ in range(10):
            start_x, start_y = random.randint(1, grid.width - 2), random.randint(
                1, grid.height - 2
            )
            if grid.get_tile(start_x, start_y).tile_key == "BUILDABLE":
                blob_coords, q = set(), [(start_x, start_y)]
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
            x, y = random.randint(1, grid.width - 2), random.randint(1, grid.height - 2)
            if grid.get_tile(x, y).tile_key == "BUILDABLE":
                grid.set_tile_type(x, y, tile_key)
                return
