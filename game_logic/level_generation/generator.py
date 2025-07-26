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
    a fixed set of three paths from the Pathfinder, each leading to a
    different side of the player's base.
    """

    @staticmethod
    def generate(grid: Grid, params: dict) -> Tuple[Grid, List[List[Tuple[int, int]]]]:
        """
        Orchestrates the entire level generation process.
        """
        logger.info(
            "Starting procedural level generation with multi-target base and buffered paths."
        )

        # --- Generation Sequence ---
        LevelGenerator._create_border(grid)
        # This function now returns a list of target points.
        target_points = LevelGenerator._place_base_zone(grid, size=4)
        if len(target_points) < 3:
            logger.critical(
                "Base placement failed to generate enough target points. Aborting."
            )
            return grid, []

        start_points = LevelGenerator._define_start_points(grid, 3)

        paths = LevelGenerator._request_three_paths(grid, start_points, target_points)
        if not paths:
            logger.error("Pathfinder failed to generate the required paths. Aborting.")
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
    def _request_three_paths(
        grid: Grid,
        start_points: List[Tuple[int, int]],
        target_points: List[Tuple[int, int]],
    ) -> List[List[Tuple[int, int]]]:
        """
        Requests exactly three paths from the Pathfinder, each to a unique target.
        """
        if len(start_points) != 3 or len(target_points) != 3:
            logger.error("Incorrect number of start or target points provided.")
            return []

        all_paths: List[List[Tuple[int, int]]] = []
        occupied_coords: Set[Tuple[int, int]] = set()

        # Define turn ranges for more variety in elbow paths.
        turn_x_range_short = (int(grid.width * 0.3), int(grid.width * 0.45))
        turn_x_range_long = (int(grid.width * 0.55), int(grid.width * 0.7))

        top_start, middle_start, bottom_start = start_points
        target_top, target_left, target_bottom = target_points

        # 1. Middle Path to Left Target
        logger.info(
            f"Requesting wandering path from {middle_start} to left target {target_left}..."
        )
        middle_path = Pathfinder.create_wandering_path(
            grid, middle_start, target_left, occupied_coords
        )
        if middle_path:
            all_paths.append(middle_path)
            occupied_coords.update(middle_path)
        else:
            logger.critical("Pathfinder FAILED to create the essential middle path.")
            return []

        # 2. Top Path to Top Target
        logger.info(
            f"Requesting elbow path from {top_start} to top target {target_top}..."
        )
        top_path = Pathfinder.create_elbow_path(
            grid, top_start, target_top, turn_x_range_short, occupied_coords
        )
        if top_path:
            all_paths.append(top_path)
            occupied_coords.update(top_path)
        else:
            logger.warning(f"Pathfinder failed to create top elbow path.")

        # 3. Bottom Path to Bottom Target
        logger.info(
            f"Requesting elbow path from {bottom_start} to bottom target {target_bottom}..."
        )
        bottom_path = Pathfinder.create_elbow_path(
            grid, bottom_start, target_bottom, turn_x_range_long, occupied_coords
        )
        if bottom_path:
            all_paths.append(bottom_path)
        else:
            logger.warning(f"Pathfinder failed to create bottom elbow path.")

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
    def _place_base_zone(grid: Grid, size: int) -> List[Tuple[int, int]]:
        """
        Places a square 'BASE_ZONE' and returns three distinct target points
        on its top, left, and bottom walls.
        """
        start_y = grid.height // 2 - size // 2
        start_x = grid.width - 1 - size
        for y in range(start_y, start_y + size):
            for x in range(start_x, start_x + size):
                if grid.is_valid_coord(x, y):
                    grid.set_tile_type(x, y, "BASE_ZONE")

        # Define three entry points for the paths.
        target_top = (start_x + size // 2, start_y - 1)
        target_left = (start_x - 1, start_y + size // 2)
        target_bottom = (start_x + size // 2, start_y + size)

        # Ensure targets are within valid grid coordinates.
        valid_targets = [
            t
            for t in [target_top, target_left, target_bottom]
            if grid.is_valid_coord(t[0], t[1])
        ]
        return valid_targets

    @staticmethod
    def _define_start_points(grid: Grid, num_paths: int) -> List[Tuple[int, int]]:
        """Defines evenly distributed starting points on the left edge of the map."""
        if num_paths <= 0:
            return []

        y_top = grid.height // 4
        y_mid = grid.height // 2
        y_bot = grid.height * 3 // 4
        return [(1, y_top), (1, y_mid), (1, y_bot)]

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
