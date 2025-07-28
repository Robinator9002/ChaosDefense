# game_logic/waves/wave_manager.py
import random
import logging
from typing import List, Dict, Any, Optional

# Using absolute import path from the project's root source folder
from game_logic.entities.enemies.enemy import Enemy

logger = logging.getLogger(__name__)


class WaveManager:
    """
    Manages the logic of enemy waves, including timing, composition,
    and the dynamic spawning of enemies over time.

    This class has been refactored to handle staggered spawns. It now maintains
    an internal queue of enemies for the current wave and manages cooldowns for
    each enemy path (lane), ensuring a continuous but not instantaneous flow.
    """

    def __init__(
        self,
        difficulty_config: Dict[str, Any],
        wave_scaling_config: Dict[str, Any],
        enemy_types: Dict[str, Any],
        player_difficulty: int,
        initial_level_difficulty: int,
        num_paths: int,
    ):
        """
        Initializes the WaveManager.
        """
        self.difficulty_config = difficulty_config
        self.wave_scaling_config = wave_scaling_config
        self.enemy_types = enemy_types
        self.player_difficulty = str(player_difficulty)
        self.initial_level_difficulty = initial_level_difficulty
        self.num_paths = num_paths

        # --- State Variables ---
        self.current_wave_number = 0
        self.active_enemies_on_map = 0
        self.time_until_next_wave = 5.0  # Initial delay before the first wave
        self.effective_level_difficulty = initial_level_difficulty
        self.game_over = False
        self.victory = False

        # --- New Spawning System State ---
        self._wave_spawn_queue: List[Dict[str, Any]] = []
        self._lane_cooldowns: Dict[int, float] = {i: 0.0 for i in range(num_paths)}

        # --- Load Difficulty Settings ---
        self.settings = self.difficulty_config.get(
            self.player_difficulty, self.difficulty_config["1"]
        )
        self.max_waves = self.settings["max_waves"]

        logger.info(
            f"WaveManager initialized for Player Difficulty '{self.settings['name']}'."
        )
        logger.info(
            f"Max waves: {self.max_waves}, Time between waves: {self.settings['time_between_waves']}s."
        )

    def update(self, dt: float, current_enemy_count: int) -> Optional[Dict[str, Any]]:
        """
        Updates timers and determines if an enemy should be spawned.

        Args:
            dt (float): The time elapsed since the last frame.
            current_enemy_count (int): The number of enemies currently on the map.

        Returns:
            A dictionary defining the next enemy to spawn, or None if no enemy
            is ready to be spawned.
        """
        self.active_enemies_on_map = current_enemy_count
        if self.game_over or self.victory:
            return None

        # --- Inter-Wave Timer Logic ---
        # If the spawn queue is empty and no enemies are on the map, we are between waves.
        if not self._wave_spawn_queue and self.active_enemies_on_map == 0:
            if self.current_wave_number >= self.max_waves:
                self.victory = True
                logger.info("VICTORY! All waves cleared.")
                return None

            self.time_until_next_wave -= dt
            if self.time_until_next_wave <= 0:
                self._prepare_next_wave()
            return None

        # --- Intra-Wave Spawning Logic ---
        # Decrement all lane cooldowns.
        for i in range(self.num_paths):
            self._lane_cooldowns[i] = max(0.0, self._lane_cooldowns[i] - dt)

        # If there are enemies waiting to be spawned, check if any can be spawned now.
        if self._wave_spawn_queue:
            for i, enemy_job in enumerate(self._wave_spawn_queue):
                lane_index = enemy_job["path_index"]
                if self._lane_cooldowns[lane_index] <= 0:
                    # This lane is ready! Pop the job from the queue.
                    spawn_data = self._wave_spawn_queue.pop(i)

                    # Reset the cooldown for this lane.
                    self._lane_cooldowns[lane_index] = self._calculate_spawn_cooldown()

                    # Return the data so the main game loop can create the enemy.
                    return spawn_data

        return None

    def _prepare_next_wave(self):
        """
        Calculates the composition of the next wave and populates the spawn queue.
        This does NOT spawn enemies, it only prepares the list of what to spawn.
        """
        self.current_wave_number += 1
        logger.info(
            f"--- Preparing Wave {self.current_wave_number}/{self.max_waves} ---"
        )

        # Update effective difficulty
        increase_interval = self.settings["level_difficulty_increase_interval"]
        if (
            self.current_wave_number - 1
        ) % increase_interval == 0 and self.current_wave_number > 1:
            self.effective_level_difficulty += 1
            logger.warning(
                f"Effective level difficulty increased to {self.effective_level_difficulty}"
            )

        # Reset the inter-wave timer
        self.time_until_next_wave = self.settings["time_between_waves"]

        # --- Generate Wave Composition ---
        # 1. Calculate total number of enemies for this wave
        count_cfg = self.wave_scaling_config["enemy_count"]
        total_enemies = (
            count_cfg["base"]
            + (self.current_wave_number * count_cfg["per_wave"])
            + (self.effective_level_difficulty * count_cfg["per_level_difficulty"])
        )
        total_enemies = int(total_enemies)

        # 2. Get pool of available enemies
        available_enemies = {
            key: data
            for key, data in self.enemy_types.items()
            # --- BUG FIX: VALIDATION STEP ---
            # Ensure we only process actual enemy dictionaries, skipping comments.
            if isinstance(data, dict)
            and data.get("min_level_difficulty", 999) <= self.effective_level_difficulty
        }
        if not available_enemies:
            logger.error("No enemies available for current difficulty!")
            return

        # 3. Create the list of "spawn jobs"
        for _ in range(total_enemies):
            enemy_type = random.choice(list(available_enemies.keys()))
            enemy_level = 1 + (
                self.current_wave_number // 5
            )  # Enemies get stronger in later waves
            path_index = random.randint(0, self.num_paths - 1)

            self._wave_spawn_queue.append(
                {"type": enemy_type, "level": enemy_level, "path_index": path_index}
            )

        logger.info(
            f"Wave {self.current_wave_number} prepared with {len(self._wave_spawn_queue)} enemies."
        )

    def _calculate_spawn_cooldown(self) -> float:
        """
        Calculates the time between individual enemy spawns on a single lane.
        """
        cooldown_cfg = self.wave_scaling_config["spawn_cooldown"]
        cooldown = (
            cooldown_cfg["base_seconds"]
            - (self.current_wave_number * cooldown_cfg["reduction_per_wave"])
            - (
                self.effective_level_difficulty
                * cooldown_cfg["reduction_per_level_difficulty"]
            )
        )
        return max(cooldown_cfg["minimum_seconds"], cooldown)
