# game_logic/game_manager.py
import logging
import uuid
import pygame
from typing import Dict, List, Any, Tuple, Optional

from .game_state import GameState
from .levels.level_manager import LevelManager
from .waves.wave_manager import WaveManager
from .entities.tower import Tower
from .entities.enemies.enemy import Enemy
from .entities.enemies.boss_enemy import BossEnemy
from .level_generation.grid import Grid
from .upgrades.upgrade_manager import UpgradeManager
from .effects.status_effect import StatusEffect

# --- NEW: Import the TargetingManager ---
from ..game_ai.targeting.targeting_manager import TargetingManager

logger = logging.getLogger(__name__)


class GameManager:
    """
    The central "headless" engine for the game.

    REFACTORED: Now owns and operates the TargetingManager, which provides
    a highly performant way for entities to query their surroundings. This
    resolves the N*M performance bottleneck and enables complex aura and AI systems.
    """

    def __init__(self, all_configs: Dict[str, Any]):
        """
        Initializes the game engine and all its core systems.
        """
        logger.info("--- Initializing Game Manager ---")
        self.configs = all_configs
        self.tile_size = self.configs["game_settings"].get("tile_size", 32)
        self.game_state: GameState = GameState()
        self.level_manager: LevelManager = LevelManager(self.configs["level_styles"])
        self.upgrade_manager: UpgradeManager = UpgradeManager(
            self.configs.get("upgrade_definitions", {})
        )
        # --- NEW: Initialize the TargetingManager ---
        # We also load the AI config which the TargetingManager will use.
        targeting_ai_config = self.configs.get("targeting_ai", {})
        self.targeting_manager: TargetingManager = TargetingManager(
            cell_size=120, targeting_ai_config=targeting_ai_config
        )

        self.wave_manager: Optional[WaveManager] = None
        self.grid: Optional[Grid] = None
        self.paths: List[List[Tuple[int, int]]] = []
        self.enemies: List[Enemy] = []
        self.towers: List[Tower] = []
        self.projectiles: List[Any] = []  # Can be multiple types
        self._setup_new_game()

    def _setup_new_game(self):
        """Sets up all necessary objects for a new game session."""
        logger.info("--- Setting up new game via Game Manager ---")
        try:
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
        level_difficulty = gen_params.get("level_difficulty", 1)
        self.wave_manager = WaveManager(
            difficulty_config=self.configs["difficulty_scaling"],
            wave_scaling_config=self.configs["wave_scaling"],
            enemy_types=self.configs["enemy_types"],
            boss_types=self.configs["boss_types"],
            allowed_boss_types=gen_params.get("allowed_boss_types", []),
            player_difficulty=player_difficulty,
            initial_level_difficulty=level_difficulty,
            num_paths=len(self.paths),
        )
        logger.info("--- Game Manager setup complete ---")

    def update(self, dt: float):
        """The main update loop for the entire game simulation."""
        if self.game_state.game_over:
            return

        # --- REFACTORED: Centralized Awareness Phase ---
        # 1. Clear the spatial grids from the previous frame.
        self.targeting_manager.clear()
        # 2. Populate the grids with the current positions of all entities.
        for enemy in self.enemies:
            self.targeting_manager.register_entity(enemy)
        for tower in self.towers:
            self.targeting_manager.register_entity(tower)

        # --- Update Game Systems ---
        if self.wave_manager:
            spawn_job = self.wave_manager.update(dt, len(self.enemies))
            if spawn_job:
                self._spawn_enemy(spawn_job)
            self.game_state.current_wave_number = (
                self.wave_manager.wave_state.current_wave_number
            )

        # --- Update Entities ---
        newly_created_entities: List[Any] = []
        # BUGFIX: Pass the targeting_manager to the update methods.
        # This provides battlefield awareness without costly full-list iterations.
        for tower in self.towers:
            new_entities = tower.update(dt, self.game_state, self.targeting_manager)
            if new_entities:
                newly_created_entities.extend(new_entities)

        for enemy in self.enemies:
            enemy.update(dt, self.game_state, self.targeting_manager)

        self.projectiles.extend(newly_created_entities)

        for projectile in self.projectiles:
            projectile.update(dt, self.game_state, self.targeting_manager)

        self._cleanup_dead_entities()

    def _cleanup_dead_entities(self):
        """Removes all dead entities from the game lists."""
        dead_enemies = [e for e in self.enemies if not e.is_alive]
        if dead_enemies:
            for dead_enemy in dead_enemies:
                self.game_state.add_gold(dead_enemy.bounty)
                self._handle_on_death_effects(dead_enemy)
        self.enemies = [e for e in self.enemies if e.is_alive]
        self.projectiles = [p for p in self.projectiles if p.is_alive]
        self.towers = [t for t in self.towers if t.is_alive]

    def _handle_on_death_effects(self, dead_enemy: Enemy):
        """Checks for on-death effects, like explosions."""
        for effect in dead_enemy.effect_handler.status_effects:
            if effect.source_entity_id:
                source_tower = next(
                    (t for t in self.towers if t.entity_id == effect.source_entity_id),
                    None,
                )
                if source_tower and source_tower.on_death_explosion:
                    self._create_explosion(
                        dead_enemy.pos, source_tower.on_death_explosion
                    )
                    break

    def _create_explosion(
        self, position: pygame.Vector2, explosion_data: Dict[str, Any]
    ):
        """Creates an instantaneous area-of-effect explosion."""
        radius = explosion_data.get("radius", 0)
        damage = explosion_data.get("damage", 0)
        effect_id = explosion_data.get("effect_id")

        # Use the targeting manager for an efficient query
        nearby_enemies = self.targeting_manager.get_nearby_enemies(position, radius)

        for enemy in nearby_enemies:
            enemy.take_damage(damage)
            if effect_id:
                effect_config = self.configs.get("status_effects", {}).get(effect_id)
                if effect_config:
                    effect_instance = StatusEffect(
                        effect_id=effect_id,
                        effect_data=effect_config,
                        duration=2.0,
                        potency=0.5,
                    )
                    enemy.apply_status_effect(effect_instance)

    def _spawn_enemy(self, spawn_job: Dict[str, Any]):
        """Creates an Enemy or BossEnemy instance based on a spawn job."""
        entity_id = spawn_job["type"]
        path_index = spawn_job["path_index"]
        if not (0 <= path_index < len(self.paths)) or not self.wave_manager:
            return
        path = self.paths[path_index]
        difficulty_mod = self.wave_manager.difficulty_settings.get("stat_modifier", 1.0)
        enemy_spawn_level = max(1, self.game_state.current_wave_number)

        if entity_id in self.configs["boss_types"]:
            config = self.configs["boss_types"][entity_id]
            new_enemy = BossEnemy(
                config, path, self.tile_size, enemy_spawn_level, difficulty_mod
            )
        elif entity_id in self.configs["enemy_types"]:
            config = self.configs["enemy_types"][entity_id]
            new_enemy = Enemy(
                config, enemy_spawn_level, path, self.tile_size, difficulty_mod
            )
        else:
            logger.error(f"Could not find definition for entity ID: {entity_id}")
            return
        self.enemies.append(new_enemy)

    def place_tower(self, tower_type_id: str, tile_x: int, tile_y: int) -> bool:
        """Handles the logic for a player attempting to place a new tower."""
        tower_data = self.configs.get("tower_types", {}).get(tower_type_id)
        if not tower_data:
            return False

        tile = self.grid.get_tile(tile_x, tile_y)
        if not tile or tile.tile_key != "BUILDABLE":
            return False
        if not self.game_state.spend_gold(tower_data.get("cost", 9999)):
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
        return True

    def purchase_tower_upgrade(self, tower_id: uuid.UUID, upgrade_id: str):
        """Handles a request to purchase an upgrade for a specific tower."""
        target_tower = next((t for t in self.towers if t.entity_id == tower_id), None)
        if not target_tower:
            return

        path_char = upgrade_id.split("_")[-1][0]
        path_id = f"path_{path_char}"
        upgrade = self.upgrade_manager.get_next_upgrade(target_tower, path_id)
        if not upgrade or upgrade.id != upgrade_id:
            return
        if not self.game_state.spend_gold(upgrade.cost):
            return

        self.upgrade_manager.apply_upgrade(target_tower, upgrade)
        target_tower.total_investment += upgrade.cost
        if path_id == "path_a":
            target_tower.path_a_tier += 1
        elif path_id == "path_b":
            target_tower.path_b_tier += 1

    def salvage_tower(self, tower_id: uuid.UUID):
        """Handles all logic for salvaging a tower."""
        target_tower = next((t for t in self.towers if t.entity_id == tower_id), None)
        if not target_tower:
            return

        refund_amount = int(target_tower.total_investment * self.get_salvage_rate())
        self.game_state.add_gold(refund_amount)
        tile_x = int(target_tower.pos.x // self.tile_size)
        tile_y = int(target_tower.pos.y // self.tile_size)
        if self.grid.is_valid_coord(tile_x, tile_y):
            self.grid.set_tile_type(tile_x, tile_y, "BUILDABLE")
        target_tower.kill()
        self.game_state.clear_selection()

    def get_salvage_rate(self) -> float:
        """Safely retrieves the current salvage refund percentage."""
        if self.wave_manager and self.wave_manager.difficulty_settings:
            return self.wave_manager.difficulty_settings.get(
                "salvage_refund_percentage", 0.0
            )
        return 0.0
