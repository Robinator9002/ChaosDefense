# pathfinding/pathfinder.py
import heapq
import logging
from typing import List, Tuple, Callable

# Import Grid for type hinting
from game_logic.level_generation.grid import Grid

logger = logging.getLogger(__name__)


class Pathfinder:
    """
    A utility class providing pathfinding algorithms.

    Currently implements the A* (A-star) algorithm to find the optimal path
    between two points on a grid, considering variable movement costs.
    """

    @staticmethod
    def find_path(
        grid: Grid,
        start: Tuple[int, int],
        end: Tuple[int, int],
        cost_func: Callable[[Tuple[int, int]], float] = lambda pos: 1.0,
    ) -> List[Tuple[int, int]]:
        """
        Finds the shortest path between two points using the A* algorithm.

        Args:
            grid (Grid): The grid to search on.
            start (Tuple[int, int]): The (x, y) starting coordinate.
            end (Tuple[int, int]): The (x, y) ending coordinate.
            cost_func (Callable): A function that takes a position (x, y) tuple
                                 and returns the cost of moving onto that tile.
                                 Defaults to a uniform cost of 1.0 for every tile.

        Returns:
            List[Tuple[int, int]]: The found path as a list of coordinates from
                                   start to end, or an empty list if no path is found.
        """

        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            """Calculates the Manhattan distance heuristic for A*."""
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        # The set of nodes to be evaluated, implemented as a priority queue.
        # Structure: (f_score, position)
        open_set = [(0, start)]
        heapq.heapify(open_set)

        # Stores the preceding node in the path for each node.
        came_from = {}

        # g_score is the cost of the cheapest path from start to the current node.
        g_score = {
            (x, y): float("inf") for y in range(grid.height) for x in range(grid.width)
        }
        g_score[start] = 0

        # f_score is g_score + heuristic. It's our best guess for the total path cost.
        f_score = {
            (x, y): float("inf") for y in range(grid.height) for x in range(grid.width)
        }
        f_score[start] = heuristic(start, end)

        while open_set:
            # Get the node in the open set with the lowest f_score.
            _, current = heapq.heappop(open_set)

            # If we've reached the end, reconstruct and return the path.
            if current == end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]  # Reverse to get path from start to end

            # Check all neighbors of the current node.
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)

                if not grid.is_valid_coord(neighbor[0], neighbor[1]):
                    continue

                # Check if the neighbor is an impassable obstacle.
                # The end node itself is always considered a valid target.
                tile = grid.get_tile(neighbor[0], neighbor[1])
                if tile.tile_key in ["BORDER", "MOUNTAIN"] and neighbor != end:
                    continue

                # Calculate the tentative g_score for this path to the neighbor.
                move_cost = cost_func(neighbor)
                tentative_g_score = g_score[current] + move_cost

                # If this path to the neighbor is better than any previous one, record it.
                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, end)

                    # Check if neighbor is already in the open set to avoid duplicates
                    if not any(n[1] == neighbor for n in open_set):
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        # If the loop finishes and we haven't reached the end, no path exists.
        logger.warning(f"A* could not find a path from {start} to {end}.")
        return []
