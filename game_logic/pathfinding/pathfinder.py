# game_logic/pathfinding/pathfinder.py
import heapq
import logging
import random
from typing import List, Tuple, Callable, Set

# To avoid circular imports, we use a relative path if the modules are in the same package.
from ..level_generation.grid import Grid

logger = logging.getLogger(__name__)


class Pathfinder:
    """
    A utility class providing pathfinding algorithms and path creation strategies.
    This version specializes in creating paths that are both organic and maintain
    a specified distance from one another.
    """

    @staticmethod
    def _create_buffered_cost_func(
        occupied: Set[Tuple[int, int]], buffer: int = 2
    ) -> Callable[[Tuple[int, int]], float]:
        """
        A factory function that creates a cost function for A*.
        This cost function penalizes proximity to already occupied coordinates,
        creating a buffer zone around existing paths.

        Args:
            occupied (Set[Tuple[int, int]]): A set of coordinates already used by other paths.
            buffer (int): The minimum distance to keep from occupied cells.

        Returns:
            A callable cost function for use in the A* algorithm.
        """
        # Pre-calculate the buffer zone for efficiency.
        # A tile is in the buffer zone if it's within the buffer distance of any occupied tile.
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
            if pos in occupied:
                return float("inf")  # Absolutely impassable
            if pos in buffer_zone:
                return 50.0  # High cost to strongly discourage entering the buffer
            # Add a small amount of randomness to make paths less predictable.
            return random.uniform(1.0, 1.5)

        return cost_func

    @staticmethod
    def create_wandering_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]] | None:
        """
        Creates a relatively direct but slightly randomized path that respects buffer zones.

        Args:
            grid (Grid): The grid to search on.
            start (Tuple[int, int]): The starting coordinate.
            end (Tuple[int, int]): The ending coordinate.
            occupied (Set[Tuple[int, int]]): A set of coordinates already used by other paths.

        Returns:
            The found path as a list of coordinates, or None if it fails.
        """
        logger.info(f"Creating wandering path from {start} to {end}.")
        cost_function = Pathfinder._create_buffered_cost_func(occupied, buffer=2)
        return Pathfinder.find_path(grid, start, end, cost_function)

    @staticmethod
    def create_elbow_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        turn_x_range: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]] | None:
        """
        Creates an organic, meandering path with a distinct "elbow" shape.
        The path is generated in two wandering segments.

        Args:
            grid (Grid): The grid to search on.
            start (Tuple[int, int]): The starting coordinate.
            end (Tuple[int, int]): The ending coordinate.
            turn_x_range (Tuple[int, int]): A (min, max) range for the random turn column.
            occupied (Set[Tuple[int, int]]): A set of coordinates already used by other paths.

        Returns:
            The combined path as a list of coordinates, or None if it fails.
        """
        logger.info(
            f"Creating elbow path from {start} to {end} via x-range {turn_x_range}."
        )

        turn_x = random.randint(turn_x_range[0], turn_x_range[1])

        possible_turn_ys = [
            y for y in range(1, grid.height - 1) if (turn_x, y) not in occupied
        ]
        if not possible_turn_ys:
            logger.warning(f"No available turn points in column x={turn_x}.")
            return None
        turn_y = random.choice(possible_turn_ys)
        turn_point = (turn_x, turn_y)

        # --- Create the first segment ---
        cost_func_seg1 = Pathfinder._create_buffered_cost_func(occupied, buffer=2)
        segment1 = Pathfinder.find_path(grid, start, turn_point, cost_func_seg1)
        if not segment1:
            logger.warning(
                f"Elbow path failed: Could not find path from {start} to turn point {turn_point}."
            )
            return None

        # --- Create the second segment ---
        newly_occupied = occupied.union(segment1)
        cost_func_seg2 = Pathfinder._create_buffered_cost_func(newly_occupied, buffer=2)
        segment2 = Pathfinder.find_path(grid, turn_point, end, cost_func_seg2)
        if not segment2:
            logger.warning(
                f"Elbow path failed: Could not find path from turn point {turn_point} to {end}."
            )
            return None

        return list(dict.fromkeys(segment1 + segment2))

    @staticmethod
    def find_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        cost_func: Callable[[Tuple[int, int]], float],
    ) -> List[Tuple[int, int]] | None:
        """Finds a path between two points using the A* algorithm."""

        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = [(0, start)]
        heapq.heapify(open_set)
        came_from = {}
        g_score = {
            (x, y): float("inf") for y in range(grid.height) for x in range(grid.width)
        }
        g_score[start] = 0
        f_score = {
            (x, y): float("inf") for y in range(grid.height) for x in range(grid.width)
        }
        f_score[start] = heuristic(start, end)

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)

                if not grid.is_valid_coord(neighbor[0], neighbor[1]):
                    continue

                tile = grid.get_tile(neighbor[0], neighbor[1])
                if tile.tile_key in ["BORDER", "MOUNTAIN"] and neighbor != end:
                    continue

                tentative_g_score = g_score[current] + cost_func(neighbor)

                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, end)
                    if not any(n[1] == neighbor for n in open_set):
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        logger.warning(f"A* could not find a path from {start} to {end}.")
        return None
