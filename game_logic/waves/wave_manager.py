# game_logic/waves/wave_manager.py
import logging
from typing import List, Dict, Any, Optional
from collections import deque

from .wave_state import WaveState
from .wave_generator import WaveGenerator
from .boss_handler import BossHandler

# --- NEW: Import AI components ---
from ..game_ai.director_ai import DirectorAI
from ..game_ai.waves.wave_composer import WaveComposer, Squad


logger = logging.getLogger(__name__)


class WaveManager:
    """
    Orchestrates the logic of enemy waves, acting as a conductor for specialized
    handler and generator classes.

    REFACTORED: This class now integrates with the DirectorAI. It requests a
    strategic wave plan from the AI and executes it using a squad-based
    spawning system for dynamic pacing. If the AI provides no plan, it falls
    back to the original random WaveGenerator.
    """

    def __init__(
        self,
        difficulty_config: Dict[str, Any],
        wave_scaling_config: Dict[str, Any],
        enemy_types: Dict[str, Any],
        boss_types: Dict[str, Any],
        buffer_types: Dict[str, Any],
        allowed_boss_types: List[str],
        player_difficulty: int,
        initial_level_difficulty: int,
        num_paths: int,
        director_ai: DirectorAI,  # --- NEW: Accept DirectorAI instance ---
    ):
        """
        Initializes the WaveManager and its specialized sub-components.
        """
        self.difficulty_settings = difficulty_config.get(
            str(player_difficulty), difficulty_config["1"]
        )
        self.num_paths = num_paths
        self.director_ai = director_ai

        self.base_standard_enemies = {**enemy_types, **buffer_types}
        self.all_enemy_types = {**self.base_standard_enemies, **boss_types}

        self.wave_state = WaveState(effective_level_difficulty=initial_level_difficulty)
        self.wave_state.initialize_lane_cooldowns(num_paths)

        # The WaveGenerator is now a fallback for when the AI is not active.
        self.wave_generator = WaveGenerator(wave_scaling_config)
        self.boss_handler = BossHandler(boss_types, allowed_boss_types)

        # --- NEW: Instantiate the WaveComposer ---
        # TODO: Load formations.json and pass it here.
        self.wave_composer = WaveComposer(self.all_enemy_types, formations={})

        self.max_waves = self.difficulty_settings["max_waves"]
        logger.info(
            f"WaveManager initialized for Player Difficulty '{self.difficulty_settings['name']}' with DirectorAI integration."
        )

    def update(self, dt: float, current_enemy_count: int) -> Optional[Dict[str, Any]]:
        """
        Updates timers and manages the entire wave lifecycle, including inter-wave
        delays, inter-squad delays, and per-unit spawning.
        """
        if self.wave_state.game_over or self.wave_state.victory:
            return None

        # --- REFACTORED: Wave Lifecycle Management ---

        # 1. Check for inter-wave period (all enemies dead, all squads spawned)
        all_squads_spawned = not self.wave_state.wave_plan
        all_queues_empty = all(not q for q in self.wave_state.spawn_queues.values())

        if all_squads_spawned and all_queues_empty and current_enemy_count == 0:
            if self.wave_state.current_wave_number >= self.max_waves:
                self.wave_state.victory = True
                logger.info("VICTORY! All waves cleared.")
                return None

            self.wave_state.time_until_next_wave -= dt
            if self.wave_state.time_until_next_wave <= 0:
                self._prepare_next_wave()
            return None

        # 2. Check for inter-squad delay
        if self.wave_state.post_squad_delay_timer > 0:
            self.wave_state.post_squad_delay_timer -= dt
            return None

        # 3. If no delay, and unit queues are empty, try to deploy the next squad
        if all_queues_empty and self.wave_state.wave_plan:
            next_squad, delay = self.wave_state.wave_plan.popleft()
            self._deploy_squad(next_squad)
            self.wave_state.post_squad_delay_timer = delay

        # 4. Per-unit spawning logic (from active squad)
        self.wave_state.lane_cooldowns = {
            lane: max(0.0, cd - dt)
            for lane, cd in self.wave_state.lane_cooldowns.items()
        }

        for lane_index, queue in self.wave_state.spawn_queues.items():
            if self.wave_state.lane_cooldowns.get(lane_index, 0) <= 0 and queue:
                spawn_data = queue.popleft()
                self.wave_state.lane_cooldowns[lane_index] = (
                    self._calculate_spawn_cooldown()
                )
                return spawn_data

        return None

    def _prepare_next_wave(self):
        """
        Orchestrates the creation of the next wave by delegating to the
        DirectorAI or falling back to the WaveGenerator.
        """
        self.wave_state.reset_for_next_wave(
            self.difficulty_settings["time_between_waves"]
        )
        self._update_difficulty()
        logger.info(
            f"--- Preparing Wave {self.wave_state.current_wave_number}/{self.max_waves} ---"
        )

        # --- NEW: AI Override Logic ---
        wave_plan = self.director_ai.compose_next_wave(
            self.wave_state, self.all_enemy_types
        )

        if wave_plan:
            logger.info(
                f"DirectorAI composed a strategic wave with {len(wave_plan)} squads."
            )
            self.wave_state.wave_plan = deque(wave_plan)
        else:
            # AI chose not to act, fall back to procedural generation
            logger.info(
                "DirectorAI deferred. Falling back to procedural wave generation."
            )
            spawn_jobs: List[Dict[str, Any]] = []
            if self.boss_handler.check_for_boss_wave(self.wave_state):
                spawn_jobs = self.boss_handler.generate_boss_wave(
                    self.wave_state, self.num_paths
                )
            else:
                available_enemies = self.boss_handler.update_available_enemies(
                    self.wave_state, self.base_standard_enemies
                )
                spawn_jobs = self.wave_generator.generate_standard_wave(
                    self.wave_state, self.num_paths, available_enemies
                )

            # Convert the single list of jobs into a single-squad wave plan
            fallback_squad: Squad = (spawn_jobs, 0.0)
            self.wave_state.wave_plan = deque([fallback_squad])

    def _deploy_squad(self, spawn_jobs: List[Dict[str, Any]]):
        """
        Populates the per-lane spawn queues with the jobs from a single squad.
        """
        for job in spawn_jobs:
            path_index = job.get("path_index")
            if path_index is not None and path_index in self.wave_state.spawn_queues:
                self.wave_state.spawn_queues[path_index].append(job)

    def _update_difficulty(self):
        """Increments the effective level difficulty based on the wave interval."""
        increase_interval = self.difficulty_settings[
            "level_difficulty_increase_interval"
        ]
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
        Calculates the time between individual enemy spawns within a squad.
        """
        # This could also be controlled by the AI in the future.
        # For now, we use the existing scaling config for a rapid, burst-like feel.
        return 0.2
