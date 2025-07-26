# game_logic/level_generation/generator.py
import random
import logging
import math
from typing import Tuple, List, Callable, Set

# The generator now only needs to know about the Pathfinder, not its inner workings.
from ..pathfinding.pathfinder import Pathfinder
from .grid import Grid


logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    A static class responsible for procedural level generation.

    This class orchestrates the creation of playable maps by requesting
    different types of paths from the Pathfinder and then placing
    environmental features.
    """

    @staticmethod
    def generate(grid: Grid, params: dict) -> Tuple[Grid, List[List[Tuple[int, int]]]]:
        """
        Orchestrates the entire level generation process.

        Args:
            grid (Grid): The Grid instance to be populated.
            params (dict): A dictionary containing generation parameters,
                           including the configurable `num_paths`.

        Returns:
            A tuple containing the populated Grid and a list of the generated enemy paths.
        """
        logger.info("Starting procedural level generation...")

        # --- Generation Sequence ---
        LevelGenerator._create_border(grid)
        target_pos = LevelGenerator._place_base_zone(grid, size=4)

        num_paths = max(1, min(params.get("num_paths", 3), 5))
        logger.info(f"Requesting {num_paths} paths from the Pathfinder.")
        start_points = LevelGenerator._define_start_points(grid, num_paths)

        # The core logic now delegates path creation to the Pathfinder.
        paths = LevelGenerator._request_paths_from_pathfinder(
            grid, start_points, target_pos, num_paths
        )
        if not paths:
            logger.error("Pathfinder failed to generate any valid paths. Aborting.")
            return grid, []

        # Carve the final, successful paths onto the grid.
        for path in paths:
            for x, y in path:
                if grid.get_tile(x, y).tile_key != "BASE_ZONE":
                    grid.set_tile_type(x, y, "PATH")

        # Place environmental features.
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

        logger.info(f"Level generation complete. Created {len(paths)} paths.")
        return grid, paths

    @staticmethod
    def _request_paths_from_pathfinder(
        grid: Grid,
        start_points: List[Tuple[int, int]],
        target: Tuple[int, int],
        num_paths: int,
    ) -> List[List[Tuple[int, int]]]:
        """
        Requests and orchestrates the creation of all paths from the Pathfinder.

        This method determines the *type* of path to request based on the
        configuration (e.g., straight, long elbow) and then calls the
        appropriate Pathfinder method to do the actual work.
        """
        all_paths: List[List[Tuple[int, int]]] = []
        occupied_coords: Set[Tuple[int, int]] = set()

        long_turn_x = int(grid.width * 0.4)
        super_long_turn_x = int(grid.width * 0.7)

        # Handle the straight middle path if num_paths is odd
        mid_index = len(start_points) // 2
        if num_paths % 2 != 0:
            logger.info("Requesting a wandering (straight) path for the middle lane.")
            middle_start = start_points.pop(mid_index)
            # Request the path from the Pathfinder
            path = Pathfinder.create_wandering_path(
                grid, middle_start, target, occupied_coords
            )
            if path:
                all_paths.append(path)
                occupied_coords.update(path)
            else:
                logger.warning("Pathfinder failed to create the middle path.")

        # Group remaining start points for elbow paths
        elbow_starts = sorted(start_points, key=lambda p: p[1])
        path_configs = [("long", long_turn_x), ("super-duper long", super_long_turn_x)]

        pair_index = 0
        while len(elbow_starts) >= 2:
            if pair_index >= len(path_configs):
                break

            path_type, turn_x = path_configs[pair_index]
            logger.info(f"Requesting a pair of '{path_type}' elbow paths.")

            top_start = elbow_starts.pop(0)
            bottom_start = elbow_starts.pop(-1)

            # Request top path
            top_path = Pathfinder.create_elbow_path(
                grid, top_start, target, turn_x, occupied_coords
            )
            if top_path:
                all_paths.append(top_path)
                occupied_coords.update(top_path)
            else:
                logger.warning(f"Pathfinder failed to create top '{path_type}' path.")

            # Request bottom path
            bottom_path = Pathfinder.create_elbow_path(
                grid, bottom_start, target, turn_x, occupied_coords
            )
            if bottom_path:
                all_paths.append(bottom_path)
                occupied_coords.update(bottom_path)
            else:
                logger.warning(
                    f"Pathfinder failed to create bottom '{path_type}' path."
                )

            pair_index += 1

        # Handle leftover path for even numbers
        if elbow_starts:
            path_type, turn_x = path_configs[pair_index]
            logger.info(f"Requesting a single '{path_type}' elbow path.")
            last_start = elbow_starts.pop(0)
            last_path = Pathfinder.create_elbow_path(
                grid, last_start, target, turn_x, occupied_coords
            )
            if last_path:
                all_paths.append(last_path)
            else:
                logger.warning(f"Pathfinder failed to create final '{path_type}' path.")

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
        start_y = grid.height // 2 - size // 2
        start_x = grid.width - 1 - size
        for y in range(start_y, start_y + size):
            for x in range(start_x, start_x + size):
                if grid.is_valid_coord(x, y):
                    grid.set_tile_type(x, y, "BASE_ZONE")
        return (start_x, start_y + size // 2)

    @staticmethod
    def _define_start_points(grid: Grid, num_paths: int) -> List[Tuple[int, int]]:
        """Defines evenly distributed starting points on the left edge of the map."""
        if num_paths == 0:
            return []
        points = []
        for i in range(num_paths):
            y = math.ceil(((i + 1) * grid.height) / (num_paths + 1))
            y = max(1, min(y, grid.height - 2))
            points.append((1, y))
        return sorted(points, key=lambda p: p[1])

    @staticmethod
    def _place_terrain_feature(
        grid: Grid,
        tile_key: str,
        min_count: int,
        max_count: int,
        placement_func: Callable,
    ):
        """A generic method to place a number of features on the grid."""
        if min_count > max_count or min_count < 0:
            return
        count = random.randint(min_count, max_count)
        for _ in range(count):
            placement_func(grid, tile_key)

    @staticmethod
    def _place_cluster(grid: Grid, tile_key: str):
        """Places a rectangular cluster of tiles, avoiding existing paths."""
        cluster_w, cluster_h = random.randint(2, 4), random.randint(2, 4)
        for _ in range(10):
            start_x, start_y = random.randint(
                1, grid.width - cluster_w - 1
            ), random.randint(1, grid.height - cluster_h - 1)
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
                for x_coord, y_coord in blob_coords:
                    grid.set_tile_type(x_coord, y_coord, tile_key)
                return

    @staticmethod
    def _place_scatter(grid: Grid, tile_key: str):
        """Places a single tile in a random buildable location."""
        for _ in range(20):
            x, y = random.randint(1, grid.width - 2), random.randint(1, grid.height - 2)
            if grid.get_tile(x, y).tile_key == "BUILDABLE":
                grid.set_tile_type(x, y, tile_key)
                return
