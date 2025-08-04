# game_logic/game_ai/director_ai.py
import logging
from typing import Dict, Any, Optional, List
import pygame

# Using TYPE_CHECKING to avoid circular imports for type hinting
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.enemies.enemy import Enemy
    from ..entities.tower import Tower
    from ..game_state import GameState
    from ..waves.wave_state import WaveState
    from .waves.wave_composer import WaveComposer, Squad

# Get a logger instance for this module
logger = logging.getLogger(__name__)


class DirectorAI:
    """
    The master intelligence of the game, responsible for observing the player's
    strategy and dynamically composing enemy waves to create a challenging and
    reactive experience.
    """

    def __init__(
        self, difficulty_settings: Dict[str, Any], wave_scaling_config: Dict[str, Any]
    ):
        """
        Initializes the Director AI.
        """
        self.difficulty_settings = difficulty_settings
        self.wave_scaling_config = wave_scaling_config
        self.enemy_performance_stats: Dict[str, Dict[str, int]] = {}
        self.path_threat_analysis: Dict[int, Dict[str, float]] = {}
        logger.info("Director AI initialized. The stage is set.")

    def record_enemy_death(self, enemy: "Enemy"):
        """
        Records that an enemy was successfully defeated by the player.
        """
        enemy_type = enemy.enemy_type_id
        if enemy_type not in self.enemy_performance_stats:
            self.enemy_performance_stats[enemy_type] = {"leaked": 0, "died": 0}
        self.enemy_performance_stats[enemy_type]["died"] += 1
        logger.debug(
            f"AI recorded death of: {enemy_type}. Stats: {self.enemy_performance_stats[enemy_type]}"
        )

    def record_enemy_leak(self, enemy: "Enemy"):
        """
        Records that an enemy successfully reached the end of the path.
        """
        enemy_type = enemy.enemy_type_id
        if enemy_type not in self.enemy_performance_stats:
            self.enemy_performance_stats[enemy_type] = {"leaked": 0, "died": 0}
        self.enemy_performance_stats[enemy_type]["leaked"] += 1
        logger.warning(
            f"AI recorded LEAK of: {enemy_type}. Stats: {self.enemy_performance_stats[enemy_type]}"
        )

    def analyze_player_defenses(
        self, towers: Dict[Any, "Tower"], paths: List[List[Any]]
    ):
        """
        Analyzes the player's current tower setup to assess the threat level
        on each path. A higher score means a more well-defended path.
        """
        self.path_threat_analysis.clear()

        for i, path in enumerate(paths):
            path_threat = 0.0
            path_points = [pygame.Vector2(p[0] * 32 + 16, p[1] * 32 + 16) for p in path]

            for tower in towers.values():
                can_hit_path = False
                for point in path_points[::5]:  # Check every 5th point for efficiency
                    if tower.pos.distance_to(point) <= tower.range:
                        can_hit_path = True
                        break

                if can_hit_path:
                    dps = tower.damage * tower.fire_rate
                    threat = dps * (1 + (tower.blast_radius / 100))
                    if tower.armor_shred > 0:
                        threat *= 1.2

                    # --- FIX: Correctly check for crowd-control effects (Issue #15) ---
                    # The original check was syntactically incorrect. This now properly
                    # iterates through the keys of the tower's effects dictionary
                    # to identify crowd-control towers and weigh them appropriately.
                    if any("slow" in effect_id for effect_id in tower.effects):
                        threat *= 1.1

                    path_threat += threat

            self.path_threat_analysis[i] = {"threat_score": path_threat}

        logger.info(f"AI Defense Analysis complete: {self.path_threat_analysis}")

    def compose_next_wave(
        self,
        wave_state: "WaveState",
        enemy_pool: Dict[str, Any],
        wave_composer: "WaveComposer",
    ) -> Optional[List[Squad]]:
        """
        The core decision-making function of the AI. Based on all gathered
        intelligence, it composes the list of spawn jobs for the next wave.
        """
        if wave_state.current_wave_number < 3:
            return None

        # This is where the core heuristic logic will live.
        # For now, we'll use the composer to create a balanced wave.
        return wave_composer.compose_wave(wave_state, self)
