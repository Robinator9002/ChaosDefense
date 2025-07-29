# game_logic/waves/wave_state.py
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class WaveState:
    """
    A data class holding the core state for the wave progression system.

    This object acts as a centralized "source of truth" for all wave-related
    data, separating the state from the logic that modifies it. This makes the
    flow of data explicit and easier to manage as the system grows in complexity.
    """

    # --- Core Progression State ---
    current_wave_number: int = 0
    time_until_next_wave: float = 5.0  # Initial delay before the first wave
    effective_level_difficulty: int = 1

    # --- Game Flow Flags ---
    game_over: bool = False
    victory: bool = False

    # --- Spawning System State ---
    # The queue of enemies waiting to be spawned in the current wave.
    # Each item is a dictionary (a "spawn job") defining an enemy.
    spawn_queue: List[Dict[str, Any]] = field(default_factory=list)

    # Tracks the spawn cooldown for each path (lane).
    # The key is the path_index (int), the value is the remaining cooldown (float).
    lane_cooldowns: Dict[int, float] = field(default_factory=dict)

    def __post_init__(self):
        """Called by the dataclass constructor after the instance is created."""
        # This can be used for any initial setup logic if needed in the future.
        pass

    def reset_for_next_wave(self, time_between_waves: float):
        """Resets the inter-wave timer and increments the wave number."""
        self.current_wave_number += 1
        self.time_until_next_wave = time_between_waves

    def initialize_lane_cooldowns(self, num_paths: int):
        """Sets up the lane cooldown dictionary based on the number of paths."""
        self.lane_cooldowns = {i: 0.0 for i in range(num_paths)}
