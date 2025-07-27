# game_logic/waves/wave_manager.py
import random
import logging
from typing import List, Dict, Any

# Using absolute import path from the project's root source folder
from game_logic.entities.enemy import Enemy

logger = logging.getLogger(__name__)


class WaveManager:
    """
    Manages the logic of enemy waves, including timing, composition,
    and difficulty scaling over the course of a game.

    This class is purely logical and does not handle rendering or direct
    Pygame event handling.
    """

    def __init__(
        self,
        difficulty_config: Dict[str, Any],
        enemy_types: Dict[str, Any],
        player_difficulty: int,
        initial_level_difficulty: int,
    ):
        """
        Initializes the WaveManager.

        Args:
            difficulty_config (Dict[str, Any]): The loaded difficulty_scaling.json data.
            enemy_types (Dict[str, Any]): The loaded enemy_types.json data.
            player_difficulty (int): The difficulty level chosen by the player (e.g., 1-4).
            initial_level_difficulty (int): The base difficulty of the map, determining initial enemy types.
        """
        self.difficulty_config = difficulty_config
        self.enemy_types = enemy_types
        self.player_difficulty = str(player_difficulty)  # Use string for JSON keys
        self.initial_level_difficulty = initial_level_difficulty

        # --- State Variables ---
        self.current_wave_number = 0
        self.active_enemies: List[Enemy] = []
        self.is_spawning_wave = False
        self.time_until_next_wave = 5.0  # Initial delay before the first wave
        self.effective_level_difficulty = initial_level_difficulty
        self.game_over = False
        self.victory = False

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

    def update(self, dt: float):
        """
        Updates the wave manager's state, handling timers and wave progression.

        Args:
            dt (float): The time elapsed since the last frame, in seconds.

        Returns:
            bool: True if a new wave should be spawned, False otherwise.
        """
        if self.game_over or self.victory:
            return False

        # If a wave is active (enemies are on screen), do nothing until it's cleared.
        # This can be changed later to allow overlapping waves.
        if self.active_enemies:
            return False

        # If the last wave was completed, check for victory.
        if self.current_wave_number >= self.max_waves:
            self.victory = True
            logger.info("VICTORY! All waves cleared.")
            return False

        self.time_until_next_wave -= dt
        if self.time_until_next_wave <= 0:
            self._prepare_next_wave()
            return True  # Signal to the main game loop to spawn the wave.

        return False

    def _prepare_next_wave(self):
        """
        Sets up the state for the upcoming wave.
        """
        self.current_wave_number += 1
        logger.info(
            f"--- Preparing Wave {self.current_wave_number}/{self.max_waves} ---"
        )

        # Check if it's time to increase the effective difficulty
        increase_interval = self.settings["level_difficulty_increase_interval"]
        if (
            self.current_wave_number - 1
        ) % increase_interval == 0 and self.current_wave_number > 1:
            self.effective_level_difficulty += 1
            logger.warning(
                f"Effective level difficulty increased to {self.effective_level_difficulty}"
            )

        # Reset the timer for the next wave
        self.time_until_next_wave = self.settings["time_between_waves"]

    def generate_wave(self) -> List[Dict[str, Any]]:
        """
        Generates the composition of the current wave.

        Returns:
            A list of dictionaries, where each dictionary defines an enemy to be spawned
            (e.g., {'type': 'grunt', 'level': 3}).
        """
        wave_composition = []

        # 1. Determine the pool of available enemies
        available_enemies = {
            enemy_key: data
            for enemy_key, data in self.enemy_types.items()
            if data["min_level_difficulty"] <= self.effective_level_difficulty
        }
        if not available_enemies:
            logger.error(
                f"No enemies available for effective difficulty {self.effective_level_difficulty}!"
            )
            return []

        # 2. Define a "budget" for the wave. This is a simple scaling formula.
        wave_budget = (
            10 + (self.current_wave_number * 5) + (self.current_wave_number**1.5)
        )

        # 3. "Spend" the budget on enemies from the available pool.
        while wave_budget > 0:
            enemy_key = random.choice(list(available_enemies.keys()))
            enemy_data = available_enemies[enemy_key]

            # The "cost" of an enemy can be its base bounty.
            cost = enemy_data["base_stats"].get("bounty", 1)
            if cost <= 0:
                cost = 1  # Avoid infinite loops

            if wave_budget - cost >= 0:
                wave_budget -= cost
                # The level of the enemy can also scale with the wave number
                enemy_level = 1 + (self.current_wave_number // 4)
                wave_composition.append({"type": enemy_key, "level": enemy_level})
            else:
                # Can't afford this enemy, break the loop.
                break

        logger.info(f"Generated wave with {len(wave_composition)} enemies.")
        return wave_composition

    def register_spawned_enemies(self, enemies: List[Enemy]):
        """
        Registers a list of newly spawned enemies as active.
        """
        self.active_enemies.extend(enemies)

    def clear_dead_enemies(self):
        """
        Removes dead enemies from the active list.
        This should be called each frame to keep the list clean.
        """
        # A list comprehension is an efficient way to create a new list
        # containing only the living enemies.
        initial_count = len(self.active_enemies)
        self.active_enemies = [enemy for enemy in self.active_enemies if enemy.is_alive]
        cleared_count = initial_count - len(self.active_enemies)
        if cleared_count > 0:
            logger.debug(f"Cleared {cleared_count} dead enemies.")
