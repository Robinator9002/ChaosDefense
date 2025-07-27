# game_logic/game_manager.py
import logging
from typing import Dict, List, Any, Tuple, Optional

# --- Core Game Logic Imports ---
from .game_state import GameState
from .levels.level_manager import LevelManager
from .level_generation.grid import Grid
from .waves.wave_manager import WaveManager
from .entities.enemy import Enemy
from .entities.tower import Tower
from .entities.projectile import Projectile

logger = logging.getLogger(__name__)


class GameManager:
    """
    The central "headless" engine for the game.
    """

    def __init__(self, all_configs: Dict[str, Any]):
        """
        Initializes the game engine with all necessary configurations.
        """
        logger.info("--- Initializing Game Manager ---")
        self.configs = all_configs
        self.tile_size = self.configs["game_settings"].get("tile_size", 32)

        self.game_state: GameState = GameState()
        self.level_manager: LevelManager = LevelManager(self.configs["level_styles"])
        self.wave_manager: Optional[WaveManager] = None
        self.grid: Optional[Grid] = None
        self.paths: List[List[Tuple[int, int]]] = []

        self.enemies: List[Enemy] = []
        self.towers: List[Tower] = []
        self.projectiles: List[Projectile] = []

        self._setup_new_game()

    def _setup_new_game(self):
        """Sets up all necessary objects for a new game session."""
        logger.info("--- Setting up new game via Game Manager ---")
        self.game_state = GameState(gold=150, base_hp=20)
        try:
            preset_to_load = "Forest"
            self.grid, self.paths, style_config = (
                self.level_manager.build_level_from_preset(preset_to_load)
            )
            self.game_state.level_grid = self.grid
        except (KeyError, ValueError) as e:
            logger.critical(f"FATAL: Failed to build level: {e}", exc_info=True)
            self.game_state.end_game()
            return

        player_difficulty = self.configs["game_settings"].get("difficulty", 1)
        level_difficulty = style_config.get("generation_params", {}).get(
            "level_difficulty", 1
        )
        self.wave_manager = WaveManager(
            difficulty_config=self.configs["difficulty_scaling"],
            wave_scaling_config=self.configs["wave_scaling"],
            enemy_types=self.configs["enemy_types"],
            player_difficulty=player_difficulty,
            initial_level_difficulty=level_difficulty,
            num_paths=len(self.paths),
        )
        logger.info("--- Game Manager setup complete ---")

    def update(self, dt: float):
        """The main update loop for the entire game simulation."""
        if self.game_state.game_over:
            return

        if self.wave_manager:
            spawn_job = self.wave_manager.update(dt, len(self.enemies))
            if spawn_job:
                self._spawn_enemy(spawn_job)
            self.game_state.current_wave_number = self.wave_manager.current_wave_number

        newly_fired_projectiles: List[Projectile] = []
        for tower in self.towers:
            projectile = tower.update(dt, self.game_state, self.enemies)
            if projectile:
                newly_fired_projectiles.append(projectile)
        self.projectiles.extend(newly_fired_projectiles)

        for enemy in self.enemies:
            enemy.update(dt, self.game_state)

        for projectile in self.projectiles:
            projectile.update(dt, self.game_state)

        self._cleanup_dead_entities()

    def _cleanup_dead_entities(self):
        """Removes all entities that are no longer alive from the game."""
        dead_enemies = [e for e in self.enemies if not e.is_alive]
        if dead_enemies:
            self.enemies = [e for e in self.enemies if e.is_alive]
            for dead_enemy in dead_enemies:
                self.game_state.add_gold(dead_enemy.bounty)

        self.projectiles = [p for p in self.projectiles if p.is_alive]

    def _spawn_enemy(self, spawn_job: Dict[str, Any]):
        """Creates an Enemy instance based on data from the WaveManager."""
        enemy_type_id = spawn_job["type"]
        enemy_types_config = self.configs["enemy_types"]
        if enemy_type_id not in enemy_types_config:
            logger.error(f"Unknown enemy type '{enemy_type_id}' in wave data.")
            return

        path_index = spawn_job["path_index"]
        if not (0 <= path_index < len(self.paths)):
            logger.error(f"Invalid path index {path_index} for spawning.")
            return

        chosen_path = self.paths[path_index]
        difficulty_settings = self.wave_manager.settings
        stat_modifier = difficulty_settings.get("stat_modifier", 1.0)

        enemy = Enemy(
            enemy_type_data=enemy_types_config[enemy_type_id],
            level=spawn_job["level"],
            path=chosen_path,
            tile_size=self.tile_size,
            difficulty_modifier=stat_modifier,
        )
        self.enemies.append(enemy)

    def place_tower(self, tower_type_id: str, tile_x: int, tile_y: int):
        """Attempts to place a tower on the grid."""
        tower_types_config = self.configs["tower_types"]
        if tower_type_id not in tower_types_config:
            logger.warning(f"Attempted to place unknown tower type: {tower_type_id}")
            return

        tile = self.grid.get_tile(tile_x, tile_y)
        if not tile or tile.tile_key != "BUILDABLE":
            logger.info(
                f"Cannot build on tile ({tile_x}, {tile_y}). Type: {tile.tile_key if tile else 'None'}"
            )
            return

        tower_data = tower_types_config[tower_type_id]
        cost = tower_data.get("cost", 9999)
        if not self.game_state.spend_gold(cost):
            logger.info(
                f"Not enough gold to build {tower_type_id}. Cost: {cost}, Have: {self.game_state.gold}"
            )
            return

        pos_x = tile_x * self.tile_size + self.tile_size / 2
        pos_y = tile_y * self.tile_size + self.tile_size / 2

        # --- MODIFIED: Pass the status effects config to the Tower constructor ---
        new_tower = Tower(
            x=pos_x,
            y=pos_y,
            tile_size=self.tile_size,
            tower_type_data=tower_data,
            status_effects_config=self.configs.get("status_effects", {}),
        )
        self.towers.append(new_tower)
        self.grid.set_tile_type(tile_x, tile_y, "TOWER_OCCUPIED")
        logger.info(
            f"Successfully placed '{tower_type_id}' at grid ({tile_x}, {tile_y})."
        )
