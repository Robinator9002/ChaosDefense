# game_logic/game_ai/waves/wave_composer.py
import logging
import random
from typing import Dict, Any, List, Tuple, Optional

# Using TYPE_CHECKING to avoid circular imports for type hinting
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...game_state import GameState
    from ..director_ai import DirectorAI

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
        logger.info(f"Wave Composer initialized with {len(formations)} formations.")

    def compose_wave(
        self, game_state: "GameState", director_ai: "DirectorAI"
    ) -> List[Squad]:
        """
        The main entry point for creating a wave. It uses heuristics to decide
        on a strategy and then builds a wave plan to execute it.
        """
        wave_plan: List[Squad] = []

        # 1. Determine the weakest path from the AI's analysis
        weakest_path_index = 0
        if director_ai.path_threat_analysis:
            # Find the path index with the lowest threat score
            weakest_path_index = min(
                director_ai.path_threat_analysis,
                key=lambda p: director_ai.path_threat_analysis[p]["threat_score"],
            )

        # 2. Calculate the total budget for this wave
        budget = self._calculate_wave_budget(game_state, director_ai)

        # 3. Heuristic Strategy Selection
        # Find the enemy type that has leaked the most, relative to how many have been sent
        leakiest_enemy = None
        max_leak_ratio = 0.1  # Require at least a 10% leak rate to be considered

        for enemy_id, stats in director_ai.enemy_performance_stats.items():
            total_spawned = stats["leaked"] + stats["died"]
            if total_spawned > 5:  # Require a minimum sample size
                leak_ratio = stats["leaked"] / total_spawned
                if leak_ratio > max_leak_ratio:
                    max_leak_ratio = leak_ratio
                    leakiest_enemy = enemy_id

        # 4. Build the wave plan based on the chosen strategy
        if leakiest_enemy and random.random() < 0.6:  # 60% chance to exploit weakness
            logger.info(
                f"AI Strategy: EXPLOIT. Leakiest enemy is '{leakiest_enemy}'. Targeting path {weakest_path_index}."
            )
            wave_plan = self._compose_exploit_wave(
                game_state, budget, leakiest_enemy, weakest_path_index
            )
        else:
            logger.info(f"AI Strategy: BALANCED. Sending a standard assault.")
            wave_plan = self._compose_balanced_wave(game_state, budget)

        return wave_plan

    def _compose_balanced_wave(
        self, game_state: "GameState", budget: int
    ) -> List[Squad]:
        """Creates a wave with a mix of standard units and formations."""
        wave_plan: List[Squad] = []

        # Spend 40% of budget on a random formation
        formation_budget = int(budget * 0.4)
        chosen_formation_id = random.choice(list(self.formations.keys()))
        formation_squad = self._create_squad_from_formation(
            game_state, chosen_formation_id
        )
        wave_plan.append((formation_squad, 3.0))  # Add formation and a pause

        # Spend the rest on individual units, distributed across paths
        remaining_budget = budget - formation_budget
        # This part can be expanded with more complex logic to buy individual units
        # For now, we'll just add a few grunts as a placeholder for the remaining budget.
        num_grunts = min(10, remaining_budget // 10)  # Assume grunt costs ~10
        grunt_squad = []
        for i in range(num_grunts):
            grunt_squad.append(
                {
                    "type": "grunt",
                    "level": game_state.current_wave_number,
                    "path_index": i % 2,
                }
            )
        wave_plan.append((grunt_squad, 0.0))

        return wave_plan

    def _compose_exploit_wave(
        self, game_state: "GameState", budget: int, enemy_id: str, path_index: int
    ) -> List[Squad]:
        """Creates a wave focused on sending many units of the successful 'leaky' type."""
        wave_plan: List[Squad] = []

        # Find a formation that contains the leaky enemy, if possible
        best_formation = None
        for formation_id, data in self.formations.items():
            if enemy_id in data["units"]:
                best_formation = formation_id
                break

        if best_formation:
            squad_jobs = self._create_squad_from_formation(
                game_state, best_formation, path_index
            )
            wave_plan.append((squad_jobs, 4.0))

        # Spend the rest of the budget on more of the leaky unit
        # Simplified cost calculation for now
        unit_cost = (
            self.all_enemy_types.get(enemy_id, {})
            .get("base_stats", {})
            .get("bounty", 10)
        )
        num_extra_units = max(1, int((budget * 0.5) // unit_cost))

        extra_squad = []
        for _ in range(num_extra_units):
            extra_squad.append(
                {
                    "type": enemy_id,
                    "level": game_state.current_wave_number,
                    "path_index": path_index,
                }
            )

        wave_plan.append((extra_squad, 0.0))
        return wave_plan

    def _create_squad_from_formation(
        self,
        game_state: "GameState",
        formation_id: str,
        override_path: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Builds a list of spawn jobs from a named formation."""
        squad_jobs = []
        formation_data = self.formations.get(formation_id)
        if not formation_data:
            return []

        for unit_type in formation_data["units"]:
            path = (
                override_path if override_path is not None else random.randint(0, 1)
            )  # Fallback
            squad_jobs.append(
                {
                    "type": unit_type,
                    "level": game_state.current_wave_number,
                    "path_index": path,
                }
            )
        return squad_jobs

    def _calculate_wave_budget(
        self, game_state: "GameState", director_ai: "DirectorAI"
    ) -> int:
        """
        Calculates the total "threat points" or "budget" for this wave.
        """
        base = director_ai.wave_scaling_config["enemy_count"]["base"]
        per_wave = director_ai.wave_scaling_config["enemy_count"]["per_wave"]
        per_diff = director_ai.wave_scaling_config["enemy_count"][
            "per_level_difficulty"
        ]

        # Budget is a proxy for total enemy value. We'll use bounty as a rough cost.
        # This formula mirrors the old enemy count formula to maintain a similar power level.
        budget = int(
            base
            + (game_state.current_wave_number * per_wave)
            + (game_state.effective_level_difficulty * per_diff)
        )
        return budget * 8  # Multiply by average enemy cost
