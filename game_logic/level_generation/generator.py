# game_logic/level_generation/generator.py
import random
import logging
import math
from typing import Tuple, List, Callable, Set, Dict

# The generator now only needs to know about the Pathfinder, not its inner workings.
from ..pathfinding.pathfinder import Pathfinder
from .grid import Grid


logger = logging.getLogger(__name__)


class LevelGenerator:
    """
    A static class responsible for procedural level generation.

    REFACTORED: This class now features a fully data-driven path generation
    system. It reads a 'paths_config' dictionary from the level parameters,
    allowing designers to specify any number and combination of path types
    (e.g., "elbow", "wandering") for a level.
    """

    @staticmethod
    def generate(grid: Grid, params: dict) -> Tuple[Grid, List[List[Tuple[int, int]]]]:
        """
        Orchestrates the entire level generation process.
        """
        logger.info("Starting procedural level generation with dynamic paths.")

        # --- Generation Sequence ---
        LevelGenerator._create_border(grid)
        target_points = LevelGenerator._place_base_zone(grid, size=4)

        # --- REFACTORED: Read the new paths_config dictionary ---
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

        # --- FIX: Introduce a fallback in case path generation fails entirely.
        # The crash was caused by `_request_paths` returning an empty list, which
        # then broke the wave manager. This block ensures we have at least one
        # path, even if it's a simple one, to prevent a critical crash.
        paths = LevelGenerator._request_paths(
            grid, start_points, target_points, paths_config
        )
        if not paths:
            logger.critical(
                "CRITICAL: Pathfinder failed to generate the required paths. Attempting to create a single, simple fallback path."
            )
            # Create a simple wandering path as a last resort to prevent a crash
            # The start and end points here are hardcoded for robustness.
            fallback_start = (1, grid.height // 2)
            fallback_end = (grid.width - 5, grid.height // 2)
            paths = [
                Pathfinder.create_wandering_path(
                    grid, fallback_start, fallback_end, set()
                )
            ]

            if not paths[0]:
                logger.critical(
                    "FATAL: Fallback path generation also failed. The game cannot proceed with this level."
                )
                return grid, []

            logger.warning("Successfully generated a fallback path to prevent a crash.")

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
        paths_config: Dict[str, int],
    ) -> List[List[Tuple[int, int]]]:
        """
        Generates a set of paths based on a configuration dictionary. This
        method is now fully dynamic and data-driven.
        """
        total_paths_requested = sum(paths_config.values())
        if not all_targets or len(all_targets) < total_paths_requested:
            logger.error(
                f"Not enough target points ({len(all_targets)}) for the requested number of paths ({total_paths_requested})."
            )
            return []

        all_paths: List[List[Tuple[int, int]]] = []
        occupied_coords: Set[Tuple[int, int]] = set()

        # Create mutable pools of start and target points to draw from
        available_starts = list(start_points)
        available_targets = list(all_targets)
        random.shuffle(available_targets)  # Randomize target assignment

        # Define path generation parameters
        turn_x_range_short = (int(grid.width * 0.3), int(grid.width * 0.45))
        turn_x_range_long = (int(grid.width * 0.55), int(grid.width * 0.7))

        # --- REFACTORED: Dynamic Path Generation Loop ---
        # This loop iterates through the requested path types and counts,
        # replacing the old, rigid if/elif structure.
        path_num = 1
        for path_type, count in paths_config.items():
            for _ in range(count):
                if not available_starts or not available_targets:
                    logger.error(
                        "Ran out of available start or target points during path generation."
                    )
                    return []

                start = available_starts.pop(0)
                target = available_targets.pop(0)

                logger.info(
                    f"Requesting path #{path_num} (type: {path_type}) from {start} to {target}"
                )

                path = None
                if path_type == "wandering":
                    path = Pathfinder.create_wandering_path(
                        grid, start, target, occupied_coords
                    )
                elif path_type == "elbow":
                    # Simple logic to vary the turn range for visual interest
                    turn_range = (
                        turn_x_range_short if path_num % 2 != 0 else turn_x_range_long
                    )
                    path = Pathfinder.create_elbow_path(
                        grid, start, target, turn_range, occupied_coords
                    )
                else:
                    logger.warning(
                        f"Unknown path type in paths_config: '{path_type}'. Skipping."
                    )
                    continue

                if path:
                    all_paths.append(path)
                    occupied_coords.update(path)
                    path_num += 1
                else:
                    logger.error(
                        f"FATAL: Pathfinder failed to create path #{path_num} ('{path_type}'). Aborting generation."
                    )
                    return []

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
        """
        REFACTORED: Dynamically defines evenly distributed starting points on
        the left edge of the map for any number of paths.
        """
        if num_paths <= 0:
            return []

        points = []
        # Calculate vertical spacing to distribute points evenly.
        # The +1 in the denominator ensures padding from the top and bottom edges.
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
