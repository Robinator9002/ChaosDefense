# game_logic/waves/wave_generator.py
import random
import logging
from typing import List, Dict, Any

# Import the new WaveState data class
from .wave_state import WaveState

logger = logging.getLogger(__name__)


class WaveGenerator:
    """
    A specialized class responsible for composing the contents of a standard wave.

    This class encapsulates the logic for determining how many enemies should
    spawn in a given wave and which types of enemies are available, based on
    the current game difficulty and progression. It is a stateless utility;
    it receives the current WaveState, performs calculations, and returns a
    list of spawn jobs.
    """

    def __init__(self, wave_scaling_config: Dict[str, Any]):
        """
        Initializes the WaveGenerator with necessary configuration.

        Args:
            wave_scaling_config (Dict[str, Any]): The configuration data from
                                                 wave_scaling.json, which defines
                                                 the formulas for enemy counts.
        """
        self.wave_scaling_config = wave_scaling_config
        logger.info("WaveGenerator initialized.")

    def generate_standard_wave(
        self,
        wave_state: WaveState,
        num_paths: int,
        available_enemies: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generates a list of "spawn jobs" for a standard, randomized wave.

        Args:
            wave_state (WaveState): The current state of the wave system.
            num_paths (int): The number of available paths for enemies to spawn on.
            available_enemies (Dict[str, Any]): A dictionary of enemy types that
                                               are currently allowed to spawn.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  is a spawn job for a single enemy.
        """
        spawn_jobs = []

        # --- BUG FIX: Create a fully filtered pool of valid enemy types ---
        # This process now involves two crucial filtering steps:
        # 1. It ensures the enemy_data is a dictionary, gracefully ignoring comments.
        # 2. It checks if the enemy's 'min_level_difficulty' is less than or
        #    equal to the current 'effective_level_difficulty' from the wave state.
        # This prevents late-game enemies from appearing in early waves.
        enemy_pool = [
            enemy_id
            for enemy_id, enemy_data in available_enemies.items()
            if isinstance(enemy_data, dict)
            and enemy_data.get("min_level_difficulty", 999)
            <= wave_state.effective_level_difficulty
        ]

        if not enemy_pool:
            logger.error(
                f"Cannot generate wave: No valid enemies available for effective difficulty {wave_state.effective_level_difficulty}!"
            )
            return spawn_jobs

        # 1. Calculate the total number of enemies for the current wave.
        count_cfg = self.wave_scaling_config["enemy_count"]
        total_enemies = (
            count_cfg["base"]
            + (wave_state.current_wave_number * count_cfg["per_wave"])
            + (
                wave_state.effective_level_difficulty
                * count_cfg["per_level_difficulty"]
            )
        )
        total_enemies = int(total_enemies)

        # 2. Create the list of spawn jobs from the correctly filtered pool.
        for _ in range(total_enemies):
            enemy_type_id = random.choice(enemy_pool)

            enemy_level = 1 + (wave_state.current_wave_number // 5)
            path_index = random.randint(0, num_paths - 1)

            spawn_jobs.append(
                {
                    "type": enemy_type_id,
                    "level": enemy_level,
                    "path_index": path_index,
                    "is_boss": False,
                }
            )

        logger.info(
            f"Generated standard wave {wave_state.current_wave_number} with {len(spawn_jobs)} enemies from a pool of {len(enemy_pool)} types."
        )
        return spawn_jobs
