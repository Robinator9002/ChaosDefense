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

logger = logging.getLogger(__name__)


class GameManager:
    """
    The central "headless" engine for the game.

    This class manages the entire game simulation, including the game state,
    level, entities (enemies and towers), and wave progression. It is designed
    to be completely independent of any rendering library, allowing the game
    to be run, tested, or even simulated in the background without a GUI.
    """

    def __init__(self, all_configs: Dict[str, Any]):
        """
        Initializes the game engine with all necessary configurations.

        Args:
            all_configs (Dict[str, Any]): A dictionary containing all loaded
                                          JSON configuration files.
        """
        logger.info("--- Initializing Game Manager ---")
        self.configs = all_configs
        self.tile_size = self.configs["game_settings"].get("tile_size", 32)

        # --- Core Components ---
        self.game_state: GameState = GameState()
        self.level_manager: LevelManager = LevelManager(self.configs["level_styles"])
        self.wave_manager: Optional[WaveManager] = None
        self.grid: Optional[Grid] = None
        self.paths: List[List[Tuple[int, int]]] = []

        # --- Entity Management ---
        self.enemies: List[Enemy] = []
        self.towers: List[Tower] = []

        self._setup_new_game()

    def _setup_new_game(self):
        """
        Sets up all necessary objects for a new game session.
        """
        logger.info("--- Setting up new game via Game Manager ---")
        self.game_state = GameState(gold=150, base_hp=20)

        # 1. Generate the level layout.
        try:
            # For now, we hardcode the "Forest" preset. This could be a parameter.
            preset_to_load = "Forest"
            self.grid, self.paths, style_config = (
                self.level_manager.build_level_from_preset(preset_to_load)
            )
            self.game_state.level_grid = self.grid
        except (KeyError, ValueError) as e:
            logger.critical(f"FATAL: Failed to build level: {e}", exc_info=True)
            # In a real game, this should propagate up to stop the game.
            self.game_state.end_game()
            return

        # 2. Initialize the Wave Manager with level and difficulty data.
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
        """
        The main update loop for the entire game simulation.

        Args:
            dt (float): The time elapsed since the previous frame.
        """
        if self.game_state.game_over:
            return

        # 1. Update Wave Manager to see if we need to spawn new enemies.
        if self.wave_manager:
            spawn_job = self.wave_manager.update(dt, len(self.enemies))
            if spawn_job:
                self._spawn_enemy(spawn_job)
            self.game_state.current_wave_number = self.wave_manager.current_wave_number

        # 2. Update all active towers.
        for tower in self.towers:
            tower.update(dt, self.game_state, self.enemies)

        # 3. Update all active enemies.
        for enemy in self.enemies:
            enemy.update(dt, self.game_state)

        # 4. Clean up dead enemies and award gold.
        dead_enemies = [e for e in self.enemies if not e.is_alive]
        if dead_enemies:
            self.enemies = [e for e in self.enemies if e.is_alive]
            for dead_enemy in dead_enemies:
                self.game_state.add_gold(dead_enemy.bounty)

    def _spawn_enemy(self, spawn_job: Dict[str, Any]):
        """Creates an Enemy instance based on data from the WaveManager."""
        enemy_type_id = spawn_job["type"]
        enemy_level = spawn_job["level"]
        path_index = spawn_job["path_index"]

        enemy_types_config = self.configs["enemy_types"]
        if enemy_type_id not in enemy_types_config:
            logger.error(f"Unknown enemy type '{enemy_type_id}' in wave data.")
            return

        if not (0 <= path_index < len(self.paths)):
            logger.error(f"Invalid path index {path_index} for spawning.")
            return

        chosen_path = self.paths[path_index]
        difficulty_settings = self.wave_manager.settings
        stat_modifier = difficulty_settings.get("stat_modifier", 1.0)

        enemy = Enemy(
            enemy_type_data=enemy_types_config[enemy_type_id],
            level=enemy_level,
            path=chosen_path,
            tile_size=self.tile_size,
            difficulty_modifier=stat_modifier,
        )
        self.enemies.append(enemy)

    # --- Player Action Interface ---
    # These methods are the public API for the rendering layer to interact with.

    def place_tower(self, tower_type_id: str, tile_x: int, tile_y: int):
        """
        Attempts to place a tower on the grid.

        This method contains the core logic for validating a build action,
        checking costs, and updating the game state.

        Args:
            tower_type_id (str): The key of the tower type to place (e.g., "turret").
            tile_x (int): The grid x-coordinate for placement.
            tile_y (int): The grid y-coordinate for placement.
        """
        tower_types_config = self.configs["tower_types"]
        if tower_type_id not in tower_types_config:
            logger.warning(f"Attempted to place unknown tower type: {tower_type_id}")
            return

        # 1. Check if the tile is buildable.
        tile = self.grid.get_tile(tile_x, tile_y)
        if not tile or tile.tile_key != "BUILDABLE":
            logger.info(
                f"Cannot build on tile ({tile_x}, {tile_y}). Type: {tile.tile_key if tile else 'None'}"
            )
            return

        # 2. Check cost and deduct gold.
        tower_data = tower_types_config[tower_type_id]
        cost = tower_data.get("cost", 9999)
        if not self.game_state.spend_gold(cost):
            logger.info(
                f"Not enough gold to build {tower_type_id}. Cost: {cost}, Have: {self.game_state.gold}"
            )
            return

        # 3. Create and place the tower.
        # Convert tile coordinates to centered pixel coordinates.
        pos_x = tile_x * self.tile_size + self.tile_size / 2
        pos_y = tile_y * self.tile_size + self.tile_size / 2

        new_tower = Tower(
            x=pos_x,
            y=pos_y,
            tile_size=self.tile_size,
            tower_type_data=tower_data,
        )
        self.towers.append(new_tower)

        # Mark the tile as occupied by changing its type.
        self.grid.set_tile_type(tile_x, tile_y, "TOWER_OCCUPIED")

        logger.info(
            f"Successfully placed '{tower_type_id}' at grid ({tile_x}, {tile_y})."
        )
