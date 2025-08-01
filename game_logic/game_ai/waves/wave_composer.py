# game_logic/game_ai/waves/wave_composer.py
import logging
from typing import Dict, Any, List, Tuple

# Using TYPE_CHECKING to avoid circular imports for type hinting
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...game_state import GameState

# Get a logger instance for this module
logger = logging.getLogger(__name__)


# Define a type alias for clarity. A "Squad" is a tuple containing:
# 1. A list of spawn jobs (dictionaries).
# 2. A float representing the delay in seconds *after* this squad is spawned.
Squad = Tuple[List[Dict[str, Any]], float]


class WaveComposer:
    """
    A tactical utility class responsible for composing the specific contents
    and pacing of an enemy wave based on a strategic goal provided by the

    Director AI.

    This class translates high-level commands (e.g., "create a balanced wave,"
    "create a counter-wave for runners") into a structured list of "squads."
    Each squad is a group of enemies spawned close together, followed by a
    defined pause, creating the dynamic burst-and-pause rhythm for waves.
    """

    def __init__(self, all_enemy_types: Dict[str, Any], formations: Dict[str, Any]):
        """
        Initializes the WaveComposer.

        Args:
            all_enemy_types (Dict[str, Any]): A combined dictionary of all
                available enemy types (standard, buffer, boss).
            formations (Dict[str, Any]): A dictionary defining pre-set enemy
                groups from formations.json.
        """
        self.all_enemy_types = all_enemy_types
        self.formations = formations
        logger.info("Wave Composer initialized.")

    def compose_wave(
        self,
        game_state: "GameState",
        strategy: Dict[str, Any],
        path_threat: Dict[int, Dict[str, float]],
    ) -> List[Squad]:
        """
        The main entry point for creating a wave. It delegates to a specific
        composition method based on the provided strategy.

        Args:
            game_state (GameState): The current state of the game.
            strategy (Dict[str, Any]): A dictionary defining the AI's goal for
                this wave (e.g., {"type": "exploit", "enemy": "runner"}).
            path_threat (Dict[int, Dict[str, float]]): The AI's analysis of
                each path's defensive strength.

        Returns:
            List[Squad]: A list of squads that constitutes the entire wave plan.
        """
        # This will be the main logic hub that calls different private methods
        # based on the strategy. For now, it's a placeholder.
        logger.debug(f"Composing wave with strategy: {strategy}")

        # Placeholder: Return a simple, hard-coded wave for demonstration.
        # In the future, this will be replaced with complex heuristic logic.
        placeholder_squad_1_jobs = [
            {"type": "scout", "level": game_state.current_wave_number, "path_index": 0},
            {"type": "scout", "level": game_state.current_wave_number, "path_index": 0},
        ]
        placeholder_squad_2_jobs = [
            {"type": "grunt", "level": game_state.current_wave_number, "path_index": 1},
            {"type": "grunt", "level": game_state.current_wave_number, "path_index": 1},
        ]

        # Structure: (list_of_jobs, post_squad_delay_seconds)
        wave_plan: List[Squad] = [
            (placeholder_squad_1_jobs, 2.5),  # Spawn 2 scouts, then wait 2.5s
            (placeholder_squad_2_jobs, 0.0),  # Spawn 2 grunts, then end the wave
        ]

        return wave_plan

    def _calculate_wave_budget(self, game_state: "GameState") -> int:
        """
        Calculates the total "threat points" or "budget" available for this
        wave, based on wave number and difficulty. This budget is then "spent"
        on purchasing enemies for the wave.

        (This is a core component of future heuristic logic).
        """
        # Placeholder logic
        budget = 100 + (game_state.current_wave_number * 20)
        return budget
