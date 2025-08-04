# game_logic/level_generation/generator.py
import random
import logging
import math
from typing import Tuple, List, Callable, Set, Dict

from ..pathfinding.pathfinder import Pathfinder
from .grid import Grid


logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    A static class responsible for procedural level generation.
    """

    # --- NEW: Centralized definition of impassable tiles for pathfinding ---
    IMPASSABLE_TILE_KEYS = ["BORDER", "MOUNTAIN", "BASE_ZONE"]

    @staticmethod
    def _create_path_cost_func(
        grid: Grid, occupied: Set[Tuple[int, int]], buffer: int = 2
    ) -> Callable[[Tuple[int, int]], float]:
        """
        A factory that creates a comprehensive cost function for the A* algorithm.
        This function encapsulates all game-specific rules about pathfinding costs.
        """
        buffer_zone = set()
        if buffer > 0:
            for ox, oy in occupied:
                for dx in range(-buffer, buffer + 1):
                    for dy in range(-buffer, buffer + 1):
                        if dx == 0 and dy == 0:
                            continue
                        buffer_zone.add((ox + dx, oy + dy))

        def cost_func(pos: Tuple[int, int]) -> float:
            """The actual cost function returned by the factory."""
            # --- REFACTORED: Game-specific logic now lives here (Issue #8) ---
            # This is where we tell the generic Pathfinder which tiles are obstacles.
            tile = grid.get_tile(pos[0], pos[1])
            if tile and tile.tile_key in LevelGenerator.IMPASSABLE_TILE_KEYS:
                return float("inf")

            if pos in occupied:
                return float("inf")
            if pos in buffer_zone:
                return 50.0  # High cost to discourage paths being too close
            return random.uniform(1.0, 1.5)  # Slight randomness for organic paths

        return cost_func

    @staticmethod
    def generate(grid: Grid, params: dict) -> Tuple[Grid, List[List[Tuple[int, int]]]]:
        """
        Orchestrates the entire level generation process.
        """
        logger.info("Starting procedural level generation with dynamic paths.")

        LevelGenerator._create_border(grid)
        target_points = LevelGenerator._place_base_zone(grid, size=4)

        paths_config = params.get("paths_config")
        if not paths_config or not isinstance(paths_config, dict):
            logger.error(
                "Level generation failed: 'paths_config' is missing or invalid."
            )
            return grid, []

        total_paths_requested = sum(paths_config.values())
        logger.info(
            f"Configuration requests {total_paths_requested} paths: {paths_config}"
        )

        start_points = LevelGenerator._define_start_points(grid, total_paths_requested)

        paths = LevelGenerator._request_paths(
            grid, start_points, target_points, paths_config
        )
        if not paths:
            logger.critical(
                "CRITICAL: Pathfinder failed to generate required paths. Creating fallback."
            )
            fallback_start = (1, grid.height // 2)
            fallback_end = (grid.width - 5, grid.height // 2)
            fallback_path = Pathfinder.create_wandering_path(
                grid, fallback_start, fallback_end, set()
            )
            if not fallback_path:
                logger.critical(
                    "FATAL: Fallback path generation also failed. The game cannot proceed."
                )
                return grid, []
            paths = [fallback_path]
            logger.warning("Successfully generated a fallback path to prevent a crash.")

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

        logger.info(f"Level generation complete. Created {len(paths)} paths.")
        return grid, paths

    @staticmethod
    def _request_paths(
        grid: Grid,
        start_points: List[Tuple[int, int]],
        all_targets: List[Tuple[int, int]],
        paths_config: Dict[str, int],
    ) -> List[List[Tuple[int, int]]]:
        """
        Generates a set of paths based on a configuration dictionary.
        """
        all_paths: List[List[Tuple[int, int]]] = []
        occupied_coords: Set[Tuple[int, int]] = set()

        available_starts = list(start_points)
        available_targets = list(all_targets)
        random.shuffle(available_targets)

        turn_x_range_short = (int(grid.width * 0.3), int(grid.width * 0.45))
        turn_x_range_long = (int(grid.width * 0.55), int(grid.width * 0.7))

        # Create a factory for our new cost function
        cost_func_factory = lambda occupied: LevelGenerator._create_path_cost_func(
            grid, occupied
        )

        path_num = 1
        for path_type, count in paths_config.items():
            for _ in range(count):
                if not available_starts or not available_targets:
                    return []

                start = available_starts.pop(0)
                target = available_targets.pop(0)

                path = None
                if path_type == "wandering":
                    cost_func = cost_func_factory(occupied_coords)
                    path = Pathfinder.find_path(grid, start, target, cost_func)
                elif path_type == "elbow":
                    turn_range = (
                        turn_x_range_short if path_num % 2 != 0 else turn_x_range_long
                    )
                    path = Pathfinder.create_elbow_path(
                        grid,
                        start,
                        target,
                        turn_range,
                        occupied_coords,
                        cost_func_factory,
                    )
                else:
                    logger.warning(f"Unknown path type: '{path_type}'. Skipping.")
                    continue

                if path:
                    all_paths.append(path)
                    occupied_coords.update(path)
                    path_num += 1
                else:
                    logger.error(
                        f"FATAL: Pathfinder failed to create path #{path_num} ('{path_type}')."
                    )
                    return []

        return all_paths

    @staticmethod
    def _create_border(grid: Grid):
        for x in range(grid.width):
            grid.set_tile_type(x, 0, "BORDER")
            grid.set_tile_type(x, grid.height - 1, "BORDER")
        for y in range(grid.height):
            grid.set_tile_type(0, y, "BORDER")
            grid.set_tile_type(grid.width - 1, y, "BORDER")

    @staticmethod
    def _place_base_zone(grid: Grid, size: int) -> List[Tuple[int, int]]:
        start_y = grid.height // 2 - size // 2
        start_x = grid.width - 1 - size
        for y in range(start_y, start_y + size):
            for x in range(start_x, start_x + size):
                if grid.is_valid_coord(x, y):
                    grid.set_tile_type(x, y, "BASE_ZONE")

        target_top = (start_x + size // 2, start_y - 1)
        target_left = (start_x - 1, start_y + size // 2)
        target_bottom = (start_x + size // 2, start_y + size)

        return [
            t
            for t in [target_top, target_left, target_bottom]
            if grid.is_valid_coord(t[0], t[1])
        ]

    @staticmethod
    def _define_start_points(grid: Grid, num_paths: int) -> List[Tuple[int, int]]:
        if num_paths <= 0:
            return []
        points = []
        spacing = grid.height / (num_paths + 1)
        for i in range(num_paths):
            y_coord = int(spacing * (i + 1))
            points.append((1, y_coord))
        return sorted(points, key=lambda p: p[1])

    @staticmethod
    def _place_terrain_feature(
        grid: Grid,
        tile_key: str,
        min_count: int,
        max_count: int,
        placement_func: Callable,
    ):
        if min_count > max_count or min_count < 0:
            return
        count = random.randint(min_count, max_count)
        for _ in range(count):
            placement_func(grid, tile_key)

    @staticmethod
    def _place_cluster(grid: Grid, tile_key: str):
        cluster_w, cluster_h = random.randint(2, 4), random.randint(2, 4)
        for _ in range(10):  # 10 attempts to find a valid spot
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
        blob_size = random.randint(5, 12)
        for _ in range(10):  # 10 attempts
            start_x, start_y = random.randint(1, grid.width - 2), random.randint(
                1, grid.height - 2
            )
            if grid.get_tile(start_x, start_y).tile_key == "BUILDABLE":
                blob_coords, q = set(), [(start_x, start_y)]
                while q and len(blob_coords) < blob_size:
                    x, y = q.pop(0)
                    if not (
                        grid.is_valid_coord(x, y)
                        and grid.get_tile(x, y).tile_key == "BUILDABLE"
                        and (x, y) not in blob_coords
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
        for _ in range(20):  # 20 attempts
            x, y = random.randint(1, grid.width - 2), random.randint(1, grid.height - 2)
            if grid.get_tile(x, y).tile_key == "BUILDABLE":
                grid.set_tile_type(x, y, tile_key)
                return
