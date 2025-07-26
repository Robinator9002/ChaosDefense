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

    This class orchestrates the creation of playable maps by requesting a
    configurable number of paths (1-3) from the Pathfinder.
    """

    @staticmethod
    def generate(grid: Grid, params: dict) -> Tuple[Grid, List[List[Tuple[int, int]]]]:
        """
        Orchestrates the entire level generation process.
        """
        logger.info("Starting procedural level generation with configurable paths.")

        # --- Generation Sequence ---
        LevelGenerator._create_border(grid)
        target_points = LevelGenerator._place_base_zone(grid, size=4)

        # Read num_paths from config, clamp it to a valid range (1-3).
        num_paths = params.get("num_paths", 3)
        num_paths = max(1, min(num_paths, 3))
        logger.info(f"Configuration requests {num_paths} path(s).")

        start_points = LevelGenerator._define_start_points(grid, num_paths)

        paths = LevelGenerator._request_paths(
            grid, start_points, target_points, num_paths
        )
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
    def _request_paths(
        grid: Grid,
        start_points: List[Tuple[int, int]],
        all_targets: List[Tuple[int, int]],
        num_paths: int,
    ) -> List[List[Tuple[int, int]]]:
        """
        Requests a configurable number of paths from the Pathfinder sequentially,
        ensuring that each path generation step is aware of all previous paths to prevent overlaps.
        """
        if not all_targets or len(all_targets) < num_paths:
            logger.error(
                "Not enough valid target points on base provided for the requested number of paths."
            )
            return []

        all_paths: List[List[Tuple[int, int]]] = []
        occupied_coords: Set[Tuple[int, int]] = set()

        turn_x_range_short = (int(grid.width * 0.3), int(grid.width * 0.45))
        turn_x_range_long = (int(grid.width * 0.55), int(grid.width * 0.7))

        target_top, target_left, target_bottom = (
            all_targets[0],
            all_targets[1],
            all_targets[2],
        )

        # --- Define the sequence of path requests as a list of "jobs" ---
        requests = []
        if num_paths == 1:
            # For 1 path, it's a wandering path to the left entrance.
            requests.append(
                {
                    "start": start_points[0],
                    "target": target_left,
                    "type": "wandering",
                    "args": None,
                }
            )
        elif num_paths == 2:
            # For 2 paths, they are both elbows to the top and bottom.
            requests.append(
                {
                    "start": start_points[0],
                    "target": target_top,
                    "type": "elbow",
                    "args": turn_x_range_short,
                }
            )
            requests.append(
                {
                    "start": start_points[1],
                    "target": target_bottom,
                    "type": "elbow",
                    "args": turn_x_range_long,
                }
            )
        elif num_paths == 3:
            # For 3 paths, generate the middle one first as it's the most constrained.
            requests.append(
                {
                    "start": start_points[1],
                    "target": target_left,
                    "type": "wandering",
                    "args": None,
                }
            )
            requests.append(
                {
                    "start": start_points[0],
                    "target": target_top,
                    "type": "elbow",
                    "args": turn_x_range_short,
                }
            )
            requests.append(
                {
                    "start": start_points[2],
                    "target": target_bottom,
                    "type": "elbow",
                    "args": turn_x_range_long,
                }
            )

        # --- Execute the requests sequentially ---
        for i, job in enumerate(requests):
            path = None
            logger.info(
                f"Requesting path #{i+1} (type: {job['type']}) from {job['start']} to {job['target']}"
            )

            if job["type"] == "wandering":
                path = Pathfinder.create_wandering_path(
                    grid, job["start"], job["target"], occupied_coords
                )
            elif job["type"] == "elbow":
                path = Pathfinder.create_elbow_path(
                    grid, job["start"], job["target"], job["args"], occupied_coords
                )

            if path:
                all_paths.append(path)
                occupied_coords.update(path)  # CRITICAL: Update state for the next job.
            else:
                logger.error(
                    f"FATAL: Pathfinder failed to create path #{i+1}. Aborting generation."
                )
                return []  # Fail fast to avoid a broken map.

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

        # Define three entry points for the paths in a consistent order.
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

        points = []
        # For 1 path, start in the middle.
        if num_paths == 1:
            points.append((1, grid.height // 2))
        # For 2 paths, use top and bottom quarters.
        elif num_paths == 2:
            points.append((1, grid.height // 4))
            points.append((1, grid.height * 3 // 4))
        # For 3 paths, use top, middle, bottom.
        elif num_paths == 3:
            points.append((1, grid.height // 4))
            points.append((1, grid.height // 2))
            points.append((1, grid.height * 3 // 4))

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
