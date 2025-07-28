# game_logic/game_manager.py
import logging
import uuid
import pygame
from typing import Dict, List, Any, Tuple, Optional

# --- Core Game Logic Imports ---
from .game_state import GameState
from .levels.level_manager import LevelManager
from .level_generation.grid import Grid
from .waves.wave_manager import WaveManager
from .entities.entity import Entity
from .entities.tower import Tower
from .entities.enemies.enemy import Enemy
from .entities.projectile import Projectile
from .upgrades.upgrade_manager import UpgradeManager
from .effects.status_effect import StatusEffect

logger = logging.getLogger(__name__)


class GameManager:
    """
    The central "headless" engine for the game. It orchestrates all game
    logic, including entity updates, wave spawning, and handling all
    tower placement and upgrade requests.
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
        self.upgrade_manager: UpgradeManager = UpgradeManager(
            self.configs.get("upgrade_definitions", {})
        )
        self.wave_manager: Optional[WaveManager] = None
        self.grid: Optional[Grid] = None
        self.paths: List[List[Tuple[int, int]]] = []
        self.enemies: List[Enemy] = []
        self.towers: List[Tower] = []
        self.projectiles: List[Projectile] = []
        self._setup_new_game()

    def _setup_new_game(self):
        """
        Sets up all necessary objects for a new game session.
        This now reads starting gold and HP from the loaded level's style config.
        """
        logger.info("--- Setting up new game via Game Manager ---")

        try:
            # In a full game, this might be selectable from a menu.
            preset_to_load = "Forest"
            self.grid, self.paths, style_config = (
                self.level_manager.build_level_from_preset(preset_to_load)
            )

            gen_params = style_config.get("generation_params", {})
            start_gold = gen_params.get("starting_gold", 150)
            start_hp = gen_params.get("base_hp", 20)
            self.game_state = GameState(gold=start_gold, base_hp=start_hp)

            self.game_state.level_grid = self.grid

        except (KeyError, ValueError) as e:
            logger.critical(f"FATAL: Failed to build level: {e}", exc_info=True)
            self.game_state = GameState(gold=0, base_hp=1)
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
            projectiles = tower.update(dt, self.game_state, self.enemies)
            if projectiles:
                newly_fired_projectiles.extend(projectiles)
        self.projectiles.extend(newly_fired_projectiles)

        for enemy in self.enemies:
            enemy.update(dt, self.game_state)

        for projectile in self.projectiles:
            projectile.update(dt, self.game_state, self.enemies)

        self._cleanup_dead_entities()

    def _cleanup_dead_entities(self):
        """
        Removes all dead entities (enemies, projectiles, and now salvaged towers)
        from the game lists and processes any on-death effects.
        """
        # Check for dead enemies to process their bounties and on-death effects.
        dead_enemies = [e for e in self.enemies if not e.is_alive]
        if dead_enemies:
            for dead_enemy in dead_enemies:
                self.game_state.add_gold(dead_enemy.bounty)
                self._handle_on_death_effects(dead_enemy)

        # Filter all entity lists to remove any entity where is_alive is False.
        self.enemies = [e for e in self.enemies if e.is_alive]
        self.projectiles = [p for p in self.projectiles if p.is_alive]
        # NEW: Ensure salvaged towers are removed from the active list.
        self.towers = [t for t in self.towers if t.is_alive]

    def _handle_on_death_effects(self, dead_enemy: Enemy):
        """
        Checks a dead enemy for effects that trigger an action from their source,
        like the Frost Tower's "Shatter" explosion.
        """
        for effect in dead_enemy.status_effects:
            if effect.source_entity_id:
                source_tower = next(
                    (t for t in self.towers if t.entity_id == effect.source_entity_id),
                    None,
                )
                if source_tower and source_tower.on_death_explosion:
                    logger.info(
                        f"Triggering 'on_death_explosion' from tower {source_tower.entity_id}"
                    )
                    self._create_explosion(
                        dead_enemy.pos, source_tower.on_death_explosion
                    )
                    break

    def _create_explosion(
        self, position: pygame.Vector2, explosion_data: Dict[str, Any]
    ):
        """
        Creates an instantaneous area-of-effect explosion that damages and
        applies effects to nearby enemies.
        """
        radius = explosion_data.get("radius", 0)
        damage = explosion_data.get("damage", 0)
        effect_id = explosion_data.get("effect_id")

        for enemy in self.enemies:
            if enemy.is_alive and position.distance_to(enemy.pos) <= radius:
                enemy.take_damage(damage)
                if effect_id:
                    effect_config = self.configs.get("status_effects", {}).get(
                        effect_id
                    )
                    if effect_config:
                        effect_instance = StatusEffect(
                            effect_id=effect_id,
                            effect_data=effect_config,
                            duration=2.0,
                            potency=0.5,
                        )
                        enemy.apply_status_effect(effect_instance)

    def _spawn_enemy(self, spawn_job: Dict[str, Any]):
        """Creates an Enemy instance based on data from the WaveManager."""
        enemy_type_id = spawn_job["type"]
        enemy_types_config = self.configs["enemy_types"]
        if enemy_type_id not in enemy_types_config:
            return

        path_index = spawn_job["path_index"]
        if not (0 <= path_index < len(self.paths)):
            return

        enemy = Enemy(
            enemy_type_data=enemy_types_config[enemy_type_id],
            level=spawn_job["level"],
            path=self.paths[path_index],
            tile_size=self.tile_size,
            difficulty_modifier=self.wave_manager.settings.get("stat_modifier", 1.0),
        )
        self.enemies.append(enemy)

    def place_tower(self, tower_type_id: str, tile_x: int, tile_y: int) -> bool:
        """
        Handles the logic for a player attempting to place a new tower.
        Returns True if the tower was successfully placed, False otherwise.
        """
        tower_types_config = self.configs["tower_types"]
        if tower_type_id not in tower_types_config:
            logger.warning(f"Attempted to place unknown tower type: {tower_type_id}")
            return False

        tile = self.grid.get_tile(tile_x, tile_y)
        if not tile or tile.tile_key != "BUILDABLE":
            logger.debug(
                f"Tower placement failed: Tile ({tile_x}, {tile_y}) is not BUILDABLE."
            )
            return False

        tower_data = tower_types_config[tower_type_id]
        if not self.game_state.spend_gold(tower_data.get("cost", 9999)):
            logger.info(
                f"Tower placement failed: Not enough gold for '{tower_type_id}'."
            )
            return False

        new_tower = Tower(
            x=tile_x * self.tile_size + self.tile_size / 2,
            y=tile_y * self.tile_size + self.tile_size / 2,
            tile_size=self.tile_size,
            tower_type_id=tower_type_id,
            tower_type_data=tower_data,
            status_effects_config=self.configs.get("status_effects", {}),
        )
        self.towers.append(new_tower)
        self.grid.set_tile_type(tile_x, tile_y, "TOWER_OCCUPIED")
        logger.info(
            f"Successfully placed '{tower_type_id}' at grid ({tile_x}, {tile_y})."
        )
        return True

    def purchase_tower_upgrade(self, tower_id: uuid.UUID, path_id: str):
        """
        Handles a request from the UI to purchase an upgrade for a specific tower.
        Now also updates the tower's total investment value.
        """
        target_tower = next((t for t in self.towers if t.entity_id == tower_id), None)
        if not target_tower:
            return

        upgrade = self.upgrade_manager.get_next_upgrade(target_tower, path_id)
        if not upgrade:
            return

        if not self.game_state.spend_gold(upgrade.cost):
            return

        # Apply the upgrade's effects to the tower.
        self.upgrade_manager.apply_upgrade(target_tower, upgrade)

        # NEW: Add the cost of this upgrade to the tower's total investment.
        target_tower.total_investment += upgrade.cost

        # Update the tower's tier for the specified path.
        if path_id == "path_a":
            target_tower.path_a_tier += 1
        elif path_id == "path_b":
            target_tower.path_b_tier += 1

        logger.info(
            f"Successfully purchased upgrade '{upgrade.id}' for tower {tower_id}. "
            f"New total investment: {target_tower.total_investment}G."
        )

    def salvage_tower(self, tower_id: uuid.UUID):
        """
        NEW: Handles all logic for salvaging a tower.
        Calculates refund, restores gold, frees the tile, and removes the tower.
        """
        target_tower = next((t for t in self.towers if t.entity_id == tower_id), None)
        if not target_tower:
            logger.error(f"Attempted to salvage non-existent tower with ID: {tower_id}")
            return

        if not self.wave_manager:
            logger.error("Cannot salvage tower: WaveManager is not available.")
            return

        # 1. Get the refund percentage from the current difficulty settings.
        refund_percentage = self.wave_manager.settings.get(
            "salvage_refund_percentage", 0.0
        )

        # 2. Calculate the refund amount.
        refund_amount = int(target_tower.total_investment * refund_percentage)

        # 3. Add the gold back to the player's total.
        self.game_state.add_gold(refund_amount)
        logger.info(
            f"Salvaged tower {tower_id} for {refund_amount}G "
            f"({target_tower.total_investment}G * {refund_percentage * 100}%)."
        )

        # 4. Free up the grid tile where the tower was located.
        tile_x = int(target_tower.pos.x // self.tile_size)
        tile_y = int(target_tower.pos.y // self.tile_size)
        if self.grid.is_valid_coord(tile_x, tile_y):
            self.grid.set_tile_type(tile_x, tile_y, "BUILDABLE")

        # 5. Mark the tower as not alive. It will be removed by _cleanup_dead_entities.
        target_tower.kill()

        # 6. Clear the player's selection to close the UI.
        self.game_state.clear_selection()
