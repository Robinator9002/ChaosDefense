# game_logic/waves/boss_handler.py
import random
import logging
from typing import List, Dict, Any, Optional

# Import the WaveState data class to read from it
from .wave_state import WaveState

logger = logging.getLogger(__name__)


class BossHandler:
    """
    Manages all logic related to boss encounters.

    This class is responsible for:
    1. Loading and filtering boss definitions based on the current level.
    2. Determining if the current wave should be a special, scripted boss wave.
    3. Generating the precise list of spawn jobs for a boss and its phalanx.
    4. Updating the pool of available standard enemies to include bosses that
       have passed their 'spawn_difficulty' threshold.
    """

    def __init__(
        self, boss_types_config: Dict[str, Any], allowed_boss_types: List[str]
    ):
        """
        Initializes the BossHandler.

        Args:
            boss_types_config (Dict[str, Any]): The full data from boss_types.json.
            allowed_boss_types (List[str]): A list of boss 'types' (e.g., "soldier")
                                            that are permitted to spawn on the
                                            current level.
        """
        self.all_bosses = boss_types_config
        # A dictionary mapping the wave number to the ID of the boss that spawns.
        self.scheduled_boss_waves: Dict[int, str] = {}
        # A pool of bosses that can be added to regular waves.
        self.available_regular_bosses: Dict[str, Any] = {}

        self._filter_and_schedule_bosses(allowed_boss_types)
        logger.info(
            f"BossHandler initialized with {len(self.scheduled_boss_waves)} scheduled boss encounters."
        )

    def _filter_and_schedule_bosses(self, allowed_boss_types: List[str]):
        """
        Filters the global boss list based on the allowed types for the current
        level and schedules their special waves.
        """
        for boss_id, boss_data in self.all_bosses.items():
            if not isinstance(boss_data, dict):
                continue

            if boss_data.get("type") in allowed_boss_types:
                wave_num = boss_data.get("boss_difficulty")
                if wave_num:
                    self.scheduled_boss_waves[wave_num] = boss_id

    def check_for_boss_wave(self, wave_state: WaveState) -> bool:
        """
        Checks if the current wave number is a scheduled boss wave.
        """
        return wave_state.current_wave_number in self.scheduled_boss_waves

    def generate_boss_wave(
        self, wave_state: WaveState, num_paths: int
    ) -> List[Dict[str, Any]]:
        """
        Generates the list of spawn jobs for a specific, scripted boss wave.

        This includes the boss itself and its pre-defined 'phalanx' of escorts.
        """
        wave_num = wave_state.current_wave_number
        boss_id = self.scheduled_boss_waves.get(wave_num)
        if not boss_id:
            return []

        boss_data = self.all_bosses[boss_id]
        spawn_jobs = []

        boss_path_index = random.randint(0, num_paths - 1)

        spawn_jobs.append(
            {
                "type": boss_id,
                "level": 1,
                "path_index": boss_path_index,
                "is_boss": True,
            }
        )

        phalanx_data = boss_data.get("phalanx", [])
        for group in phalanx_data:
            for _ in range(group["count"]):
                spawn_jobs.append(
                    {
                        "type": group["type"],
                        "level": 1 + (wave_num // 5),
                        "path_index": boss_path_index,
                        "is_boss": False,
                    }
                )

        logger.warning(
            f"Generating special BOSS WAVE {wave_num} featuring '{boss_data['name']}'!"
        )
        random.shuffle(spawn_jobs)
        return spawn_jobs

    def update_available_enemies(
        self, wave_state: WaveState, current_enemy_pool: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checks if any bosses have met their 'spawn_difficulty' and adds them
        to the regular enemy pool if so.
        """
        updated_pool = current_enemy_pool.copy()
        for boss_id, boss_data in self.all_bosses.items():
            # --- FIX: Added validation to prevent crashes from JSON comments (Issue #5) ---
            # This check ensures we only process actual boss data dictionaries,
            # safely ignoring any string-based comments in the config file.
            if not isinstance(boss_data, dict):
                continue

            if (
                boss_id not in updated_pool
                and boss_id in self.scheduled_boss_waves.values()
            ):
                spawn_difficulty = boss_data.get("spawn_difficulty")
                if (
                    spawn_difficulty
                    and wave_state.effective_level_difficulty >= spawn_difficulty
                ):
                    logger.info(
                        f"Boss '{boss_data['name']}' has been added to the regular spawn pool."
                    )
                    updated_pool[boss_id] = boss_data

        return updated_pool
