# game_logic/waves/wave_state.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
from collections import deque

# --- NEW: Import Squad for type hinting ---
from ..game_ai.waves.wave_composer import Squad


@dataclass
class WaveState:
    """
    A data class holding the core state for the wave progression system.

    REFACTORED: This state object has been upgraded to support the Director AI's
    squad-based, dynamically paced wave plans.
    """

    # --- Core Progression State ---
    current_wave_number: int = 0
    time_until_next_wave: float = 5.0  # Initial delay before the first wave
    effective_level_difficulty: int = 1

    # --- Game Flow Flags ---
    game_over: bool = False
    victory: bool = False

    # --- Spawning System State ---
    # Per-lane queues for individual units within a squad.
    spawn_queues: Dict[int, deque] = field(default_factory=dict)

    # Tracks the spawn cooldown for each path (lane).
    lane_cooldowns: Dict[int, float] = field(default_factory=dict)

    # --- NEW: AI-Driven Wave Plan State ---
    # A deque of squads. The WaveManager will process one squad at a time.
    wave_plan: deque[Squad] = field(default_factory=deque)

    # A timer to enforce the delay *after* a squad has finished spawning.
    post_squad_delay_timer: float = 0.0

    def __post_init__(self):
        """Called by the dataclass constructor after the instance is created."""
        pass

    def reset_for_next_wave(self, time_between_waves: float):
        """Resets timers and clears the plan for the upcoming wave."""
        self.current_wave_number += 1
        self.time_until_next_wave = time_between_waves

        # --- NEW: Clear AI-related state ---
        self.wave_plan.clear()
        self.post_squad_delay_timer = 0.0

    def initialize_lane_cooldowns(self, num_paths: int):
        """Sets up the lane cooldown and spawn queue dictionaries."""
        self.lane_cooldowns = {i: 0.0 for i in range(num_paths)}
        self.spawn_queues = {i: deque() for i in range(num_paths)}
