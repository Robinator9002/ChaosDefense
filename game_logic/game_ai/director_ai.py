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

# Get a logger instance for this module
logger = logging.getLogger(__name__)


class DirectorAI:
    """
    The master intelligence of the game, responsible for observing the player's
    strategy and dynamically composing enemy waves to create a challenging and
    reactive experience.

    This class acts as a "Director" in a movie, deciding which "actors" (enemies)
    to send, where to send them, and when, based on the unfolding "scene" of
    the game.
    """

    def __init__(
        self, difficulty_settings: Dict[str, Any], wave_scaling_config: Dict[str, Any]
    ):
        """
        Initializes the Director AI.

        Args:
            difficulty_settings (Dict[str, Any]): The configuration for the
                current player-selected difficulty (e.g., from difficulty_scaling.json).
            wave_scaling_config (Dict[str, Any]): The configuration for how
                waves scale over time (from wave_scaling.json).
        """
        self.difficulty_settings = difficulty_settings
        self.wave_scaling_config = wave_scaling_config

        # --- Intelligence Data Stores ---
        self.enemy_performance_stats: Dict[str, Dict[str, int]] = {}
        self.path_threat_analysis: Dict[int, Dict[str, float]] = {}

        logger.info("Director AI initialized. The stage is set.")

    def record_enemy_death(self, enemy: "Enemy"):
        """
        Records that an enemy was successfully defeated by the player.
        This is a key feedback metric indicating the player's strengths.
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
        This is a key feedback metric indicating the player's weaknesses.
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
            path_points = [pygame.Vector2(p[0], p[1]) for p in path]

            for tower in towers.values():
                # Check if the tower can hit any part of this path
                can_hit_path = False
                # Sample points along the path for efficiency
                for point in path_points[::5]:  # Check every 5th point
                    if tower.pos.distance_to(point) <= tower.range:
                        can_hit_path = True
                        break

                if can_hit_path:
                    # Calculate a heuristic threat score for the tower
                    dps = tower.damage * tower.fire_rate
                    # Add value for AoE and special abilities
                    threat = dps * (1 + (tower.blast_radius / 100))
                    if tower.armor_shred > 0:
                        threat *= 1.2
                    if any("slow" in effect for effect in tower.effects):
                        threat *= 1.1
                    path_threat += threat

            self.path_threat_analysis[i] = {"threat_score": path_threat}

        logger.info(f"AI Defense Analysis complete: {self.path_threat_analysis}")

    def compose_next_wave(
        self, game_state: "GameState", enemy_pool: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """
        The core decision-making function of the AI. Based on all gathered
        intelligence, it composes the list of spawn jobs for the next wave.
        """
        # For now, we will let the AI "sleep" for the first few waves to let
        # the player get established.
        if game_state.current_wave_number < 3:
            return None

        # This is where the core heuristic logic will live.
        # It will use self.enemy_performance_stats and self.path_threat_analysis
        # to make intelligent decisions via the WaveComposer.

        # For now, we return None to use the fallback generator.
        # In the next phase, this will return a full wave plan.
        return None
