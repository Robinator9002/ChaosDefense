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
            if pos in occupied:
                return float("inf")  # Absolutely impassable
            if pos in buffer_zone:
                return 50.0  # High cost to strongly discourage entering the buffer
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
        """
        logger.info(f"Creating wandering path from {start} to {end}.")
        # Note: The generator will create the final, comprehensive cost function.
        # This is a simplified version for the fallback path.
        cost_function = Pathfinder._create_buffered_cost_func(occupied, buffer=2)
        return Pathfinder.find_path(grid, start, end, cost_function)

    @staticmethod
    def create_elbow_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        turn_x_range: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
        cost_func_factory: Callable,
    ) -> List[Tuple[int, int]] | None:
        """
        Creates a path with a guaranteed 'elbow' shape, but a wandering second half.
        """
        logger.info(
            f"Creating hybrid elbow path from {start} to {end} via x-range {turn_x_range}."
        )

        turn_x = random.randint(turn_x_range[0], turn_x_range[1])
        start_x, start_y = start

        # 1. Create the geometric horizontal segment
        segment1 = []
        for x in range(start_x, turn_x + 1):
            pos = (x, start_y)
            if not grid.is_valid_coord(pos[0], pos[1]) or pos in occupied:
                logger.warning(
                    f"Elbow path failed: horizontal segment blocked at {pos}."
                )
                return None
            segment1.append(pos)

        turn_point = (turn_x, start_y)

        # 2. Find the second segment with A*
        newly_occupied = occupied.union(segment1)
        cost_func_seg2 = cost_func_factory(newly_occupied)
        segment2 = Pathfinder.find_path(grid, turn_point, end, cost_func_seg2)

        if not segment2:
            logger.warning(
                f"Elbow path failed: A* could not find path from turn point {turn_point} to {end}."
            )
            return None

        # Combine and return, removing duplicates from the turn point
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
            # Manhattan distance is a perfect heuristic for a 4-directional grid
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = [(0, start)]  # Priority queue: (f_score, position)
        heapq.heapify(open_set)

        came_from = {}  # Stores the preceding node in the best path

        g_score = {
            (x, y): float("inf") for y in range(grid.height) for x in range(grid.width)
        }
        g_score[start] = 0

        f_score = {
            (x, y): float("inf") for y in range(grid.height) for x in range(grid.width)
        }
        f_score[start] = heuristic(start, end)

        open_set_hash = {start}  # For fast lookups

        while open_set:
            _, current = heapq.heappop(open_set)
            open_set_hash.remove(current)

            if current == end:
                # Reconstruct path from end to start
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:  # 4-directional movement
                neighbor = (current[0] + dx, current[1] + dy)

                if not grid.is_valid_coord(neighbor[0], neighbor[1]):
                    continue

                # --- REFACTORED: Removed hardcoded impassable tile check (Issue #8) ---
                # The responsibility for determining if a tile is impassable
                # now belongs entirely to the cost_func. The Pathfinder is now
                # a generic algorithm that only cares about costs, not tile types.

                tentative_g_score = g_score[current] + cost_func(neighbor)

                if tentative_g_score < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, end)
                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        open_set_hash.add(neighbor)

        logger.warning(f"A* could not find a path from {start} to {end}.")
        return None
