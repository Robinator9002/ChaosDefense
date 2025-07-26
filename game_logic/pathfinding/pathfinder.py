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

    This class contains both a low-level A* implementation (`find_path`) and
    high-level methods for generating specific, stylized paths like straight
    routes or meandering "elbow" paths (`create_wandering_path`, `create_elbow_path`).
    """

    @staticmethod
    def create_wandering_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]] | None:
        """
        Creates a relatively direct but slightly randomized path.

        This is ideal for the 'straight' middle path to give it a more
        natural, less-perfectly-linear appearance.

        Args:
            grid (Grid): The grid to search on.
            start (Tuple[int, int]): The starting coordinate.
            end (Tuple[int, int]): The ending coordinate.
            occupied (Set[Tuple[int, int]]): A set of coordinates already used by other paths.

        Returns:
            The found path as a list of coordinates, or None if it fails.
        """
        logger.info(f"Creating wandering path from {start} to {end}.")

        def cost_func(pos: Tuple[int, int]) -> float:
            """A cost function that adds slight randomness."""
            if pos in occupied:
                return 1000.0  # Very high cost to avoid existing paths
            return random.uniform(1.0, 1.5)  # Encourage slight deviations

        return Pathfinder.find_path(grid, start, end, cost_func, occupied)

    @staticmethod
    def create_elbow_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        turn_x: int,
        occupied: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]] | None:
        """
        Creates a path with a distinct "elbow" shape that meanders.

        This path is generated in two stages:
        1. A wandering path from the start to a random point near the 'turn_x' column.
        2. Another wandering path from that turn point to the final destination.
        This creates a much more organic and unpredictable "owl elbow" shape.

        Args:
            grid (Grid): The grid to search on.
            start (Tuple[int, int]): The starting coordinate.
            end (Tuple[int, int]): The ending coordinate.
            turn_x (int): The approximate x-coordinate where the path should turn.
            occupied (Set[Tuple[int, int]]): A set of coordinates already used by other paths.

        Returns:
            The combined path as a list of coordinates, or None if it fails.
        """
        logger.info(f"Creating elbow path from {start} to {end} via x={turn_x}.")

        # --- 1. Find a random turn point in the target column ---
        # Find a valid, unoccupied y-coordinate in the turn column.
        possible_turn_ys = [
            y for y in range(1, grid.height - 1) if (turn_x, y) not in occupied
        ]
        if not possible_turn_ys:
            logger.warning(f"No available turn points in column x={turn_x}.")
            return None
        turn_y = random.choice(possible_turn_ys)
        turn_point = (turn_x, turn_y)

        # --- 2. Create the first segment of the elbow ---
        def cost_func_segment1(pos: Tuple[int, int]) -> float:
            """Cost function for the first leg of the journey."""
            if pos in occupied:
                return 1000.0
            # Add a bit of randomness to make the path meander.
            return random.uniform(1.0, 2.0)

        segment1 = Pathfinder.find_path(
            grid, start, turn_point, cost_func_segment1, occupied
        )
        if not segment1:
            logger.warning(
                f"Elbow path failed: Could not find path from {start} to turn point {turn_point}."
            )
            return None

        # The coordinates of the first segment are now also occupied for the second search.
        newly_occupied = occupied.union(segment1)

        # --- 3. Create the second segment of the elbow ---
        def cost_func_segment2(pos: Tuple[int, int]) -> float:
            """Cost function for the second leg of the journey."""
            if pos in newly_occupied:
                return 1000.0
            # A different random factor can make the segments look distinct.
            return random.uniform(1.0, 1.8)

        segment2 = Pathfinder.find_path(
            grid, turn_point, end, cost_func_segment2, newly_occupied
        )
        if not segment2:
            logger.warning(
                f"Elbow path failed: Could not find path from turn point {turn_point} to {end}."
            )
            return None

        # Combine the paths, removing the duplicate turn_point.
        full_path = list(dict.fromkeys(segment1 + segment2))
        return full_path

    @staticmethod
    def find_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        cost_func: Callable[[Tuple[int, int]], float],
        occupied: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]] | None:
        """
        Finds the shortest path between two points using the A* algorithm.
        This is the low-level pathfinding workhorse.

        Args:
            grid (Grid): The grid to search on.
            start (Tuple[int, int]): The (x, y) starting coordinate.
            end (Tuple[int, int]): The (x, y) ending coordinate.
            cost_func (Callable): A function that takes a position (x, y) tuple
                                 and returns the cost of moving onto that tile.
            occupied (Set[Tuple[int, int]]): A set of coordinates that are impassable.

        Returns:
            The found path as a list of coordinates, or None if no path is found.
        """

        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            """Calculates the Manhattan distance heuristic for A*."""
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
                # Paths cannot cross borders, mountains, or other paths.
                # The end node itself is always a valid target.
                if (
                    tile.tile_key in ["BORDER", "MOUNTAIN"] or neighbor in occupied
                ) and neighbor != end:
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
