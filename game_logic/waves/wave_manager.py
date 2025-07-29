# game_logic/waves/wave_manager.py
import logging
from typing import List, Dict, Any, Optional

# --- Refactor Imports ---
# Import the new specialized classes that will handle the logic.
from .wave_state import WaveState
from .wave_generator import WaveGenerator
from .boss_handler import BossHandler

logger = logging.getLogger(__name__)


class WaveManager:
    """
    Orchestrates the logic of enemy waves, acting as a conductor for specialized
    handler and generator classes.

    This refactored class is responsible for:
    - Maintaining the central wave state (`WaveState`).
    - Managing the high-level timing between waves.
    - Delegating the creation of wave content to `WaveGenerator` and `BossHandler`.
    - Managing the staggered spawning of enemies from the spawn queue.
    """

    def __init__(
        self,
        difficulty_config: Dict[str, Any],
        wave_scaling_config: Dict[str, Any],
        enemy_types: Dict[str, Any],
        boss_types: Dict[str, Any],  # NEW
        allowed_boss_types: List[str],  # NEW
        player_difficulty: int,
        initial_level_difficulty: int,
        num_paths: int,
    ):
        """
        Initializes the WaveManager and its specialized sub-components.
        """
        self.difficulty_settings = difficulty_config.get(
            str(player_difficulty), difficulty_config["1"]
        )
        self.num_paths = num_paths
        self.base_enemy_types = enemy_types

        # --- Initialize Specialized Handlers ---
        self.wave_state = WaveState(effective_level_difficulty=initial_level_difficulty)
        self.wave_state.initialize_lane_cooldowns(num_paths)

        self.wave_generator = WaveGenerator(wave_scaling_config)
        self.boss_handler = BossHandler(boss_types, allowed_boss_types)

        self.max_waves = self.difficulty_settings["max_waves"]
        logger.info(
            f"WaveManager initialized for Player Difficulty '{self.difficulty_settings['name']}'."
        )

    def update(self, dt: float, current_enemy_count: int) -> Optional[Dict[str, Any]]:
        """
        Updates timers and determines if an enemy should be spawned from the queue.
        """
        if self.wave_state.game_over or self.wave_state.victory:
            return None

        # --- Inter-Wave Timer Logic ---
        if not self.wave_state.spawn_queue and current_enemy_count == 0:
            if self.wave_state.current_wave_number >= self.max_waves:
                self.wave_state.victory = True
                logger.info("VICTORY! All waves cleared.")
                return None

            self.wave_state.time_until_next_wave -= dt
            if self.wave_state.time_until_next_wave <= 0:
                self._prepare_next_wave()
            return None

        # --- Intra-Wave Spawning Logic ---
        self.wave_state.lane_cooldowns = {
            lane: max(0.0, cd - dt)
            for lane, cd in self.wave_state.lane_cooldowns.items()
        }

        if self.wave_state.spawn_queue:
            for i, enemy_job in enumerate(self.wave_state.spawn_queue):
                lane_index = enemy_job["path_index"]
                if self.wave_state.lane_cooldowns.get(lane_index, 0) <= 0:
                    spawn_data = self.wave_state.spawn_queue.pop(i)
                    self.wave_state.lane_cooldowns[lane_index] = (
                        self._calculate_spawn_cooldown()
                    )
                    return spawn_data

        return None

    def _prepare_next_wave(self):
        """
        Orchestrates the creation of the next wave by delegating to the
        appropriate handler (Boss or Standard).
        """
        # 1. Update the core wave state.
        self.wave_state.reset_for_next_wave(
            self.difficulty_settings["time_between_waves"]
        )
        self._update_difficulty()
        logger.info(
            f"--- Preparing Wave {self.wave_state.current_wave_number}/{self.max_waves} ---"
        )

        # 2. High-level decision: Is this a boss wave or a standard wave?
        if self.boss_handler.check_for_boss_wave(self.wave_state):
            # Delegate to the BossHandler to generate the scripted wave.
            self.wave_state.spawn_queue = self.boss_handler.generate_boss_wave(
                self.wave_state, self.num_paths
            )
        else:
            # For a standard wave, first determine the pool of available enemies.
            # The BossHandler may add bosses to this pool if they've met their
            # spawn_difficulty threshold.
            available_enemies = self.boss_handler.update_available_enemies(
                self.wave_state, self.base_enemy_types
            )
            # Delegate to the WaveGenerator to create a random wave.
            self.wave_state.spawn_queue = self.wave_generator.generate_standard_wave(
                self.wave_state, self.num_paths, available_enemies
            )

    def _update_difficulty(self):
        """Increments the effective level difficulty based on the wave interval."""
        increase_interval = self.difficulty_settings[
            "level_difficulty_increase_interval"
        ]
        # Ensure interval is at least 1 to avoid division by zero.
        if (
            increase_interval > 0
            and (self.wave_state.current_wave_number - 1) % increase_interval == 0
            and self.wave_state.current_wave_number > 1
        ):
            self.wave_state.effective_level_difficulty += 1
            logger.warning(
                f"Effective level difficulty increased to {self.wave_state.effective_level_difficulty}"
            )

    def _calculate_spawn_cooldown(self) -> float:
        """
        Calculates the time between individual enemy spawns on a single lane.
        This logic remains in the manager as it's part of the core spawning rhythm.
        """
        cooldown_cfg = self.wave_generator.wave_scaling_config["spawn_cooldown"]
        cooldown = (
            cooldown_cfg["base_seconds"]
            - (self.wave_state.current_wave_number * cooldown_cfg["reduction_per_wave"])
            - (
                self.wave_state.effective_level_difficulty
                * cooldown_cfg["reduction_per_level_difficulty"]
            )
        )
        return max(cooldown_cfg["minimum_seconds"], cooldown)
