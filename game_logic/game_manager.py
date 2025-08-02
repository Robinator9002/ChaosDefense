# game_logic/game_manager.py
import logging
import uuid
import pygame
from typing import Dict, List, Any, Tuple, Optional, TYPE_CHECKING

from .game_state import GameState
from .levels.level_manager import LevelManager
from .level_generation.grid import Grid
from .waves.wave_manager import WaveManager
from .entities.tower import Tower
from .entities.enemies.enemy import Enemy
from .entities.enemies.boss_enemy import BossEnemy
from .entities.enemies.buffer_enemy import BufferEnemy
from .entities.projectiles.projectile import Projectile
from .entities.projectiles.persistent_ground_aura import PersistentGroundAura
from .entities.projectiles.persistent_attached_aura import PersistentAttachedAura
from .upgrades.upgrade_manager import UpgradeManager
from .effects.status_effect import StatusEffect
from .game_ai.targeting.targeting_manager import TargetingManager
from .game_ai.director_ai import DirectorAI

if TYPE_CHECKING:
    from .progression.progression_manager import ProgressionManager


logger = logging.getLogger(__name__)


class GameManager:
    """
    The central "headless" engine for the game.

    REFACTORED: Now accepts a level_id upon creation to dynamically build
    the selected level.
    """

    def __init__(
        self,
        all_configs: Dict[str, Any],
        progression_manager: "ProgressionManager",
        level_id: str,
    ):
        """
        Initializes the game engine and all its core systems for a specific level.
        """
        logger.info("--- Initializing Game Manager ---")
        self.configs = all_configs
        self.progression_manager = progression_manager
        self.current_level_id = level_id

        self.tile_size = self.configs["game_settings"].get("tile_size", 32)
        self.game_state: GameState = GameState()
        self.level_manager: LevelManager = LevelManager(self.configs["level_styles"])
        self.upgrade_manager: UpgradeManager = UpgradeManager(
            self.configs.get("upgrade_definitions", {})
        )
        targeting_ai_config = self.configs.get("targeting_ai", {})
        self.targeting_manager: TargetingManager = TargetingManager(
            cell_size=120, targeting_ai_config=targeting_ai_config
        )
        player_difficulty = self.configs["game_settings"].get("difficulty", 1)
        self.director_ai: DirectorAI = DirectorAI(
            difficulty_settings=self.configs["difficulty_scaling"].get(
                str(player_difficulty)
            ),
            wave_scaling_config=self.configs["wave_scaling"],
        )
        self.wave_manager: Optional[WaveManager] = None
        self.grid: Optional[Grid] = None
        self.paths: List[List[Tuple[int, int]]] = []

        self.enemies: Dict[uuid.UUID, Enemy] = {}
        self.towers: Dict[uuid.UUID, Tower] = {}
        self.projectiles: Dict[uuid.UUID, Any] = {}

        self._setup_new_game()

    def _setup_new_game(self):
        """Sets up all necessary objects for a new game session."""
        logger.info(f"--- Setting up new game for level: {self.current_level_id} ---")
        try:
            self.grid, self.paths, style_config = (
                self.level_manager.build_level_from_preset(self.current_level_id)
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
            buffer_types=self.configs["buffer_types"],
            allowed_boss_types=gen_params.get("allowed_boss_types", []),
            player_difficulty=player_difficulty,
            initial_level_difficulty=level_difficulty,
            num_paths=len(self.paths),
            director_ai=self.director_ai,
        )
        logger.info("--- Game Manager setup complete ---")

    def end_game_session(self, victory: bool):
        """
        Calculates and awards meta-currency and unlocks the next level upon
        victory, then saves the player's progress.
        """
        logger.info(f"Game session ended. Victory: {victory}")
        waves_cleared = self.game_state.current_wave_number

        player_data = self.progression_manager.get_player_data()

        shards_per_wave = 5
        victory_bonus = 100 if victory else 0
        total_shards_earned = (waves_cleared * shards_per_wave) + victory_bonus

        if total_shards_earned > 0:
            logger.info(f"Awarding {total_shards_earned} Chaos Shards to the player.")
            player_data.meta_currency += total_shards_earned

        if waves_cleared > player_data.highest_wave_reached:
            player_data.highest_wave_reached = waves_cleared

        if victory and self.current_level_id:
            all_levels = self.level_manager.get_level_presets()
            try:
                current_level_index = all_levels.index(self.current_level_id)
                if current_level_index + 1 < len(all_levels):
                    next_level_id = all_levels[current_level_index + 1]
                    if next_level_id not in player_data.unlocked_levels:
                        player_data.unlocked_levels.add(next_level_id)
                        logger.warning(f"NEW LEVEL UNLOCKED: {next_level_id}")
            except ValueError:
                logger.error(
                    f"Could not find current level '{self.current_level_id}' in level list."
                )

        self.progression_manager.player_data_manager.save_data(player_data)

    def update(self, dt: float):
        """The main update loop for the entire game simulation."""
        if self.game_state.game_over or self.game_state.victory:
            return

        if self.wave_manager:
            spawn_job = self.wave_manager.update(dt, len(self.enemies))
            if spawn_job:
                self._spawn_enemy(spawn_job)
            self.game_state.current_wave_number = (
                self.wave_manager.wave_state.current_wave_number
            )
            if self.wave_manager.wave_state.victory:
                self.game_state.victory = True

        newly_created_entities: List[Any] = []
        for tower in self.towers.values():
            new_entities = tower.update(dt, self.game_state, self.targeting_manager)
            if new_entities:
                newly_created_entities.extend(new_entities)

        for enemy in list(self.enemies.values()):
            leaked_enemy = enemy.update(dt, self.game_state, self.targeting_manager)
            if leaked_enemy:
                self.director_ai.record_enemy_leak(leaked_enemy)
            if enemy.is_alive:
                self.targeting_manager.update_entity_position(enemy)

        for projectile in self.projectiles.values():
            projectile.update(dt, self.game_state, self.targeting_manager)

        for entity in newly_created_entities:
            if isinstance(
                entity, (Projectile, PersistentGroundAura, PersistentAttachedAura)
            ):
                self.projectiles[entity.entity_id] = entity
                if not isinstance(entity, Projectile):
                    self.targeting_manager.add_entity(entity)
            else:
                logger.warning(f"Unhandled new entity type created: {type(entity)}")

        self._cleanup_dead_entities()

    def _cleanup_dead_entities(self):
        """Removes all dead entities from the game."""
        dead_enemy_ids = [eid for eid, e in self.enemies.items() if not e.is_alive]
        for enemy_id in dead_enemy_ids:
            dead_enemy = self.enemies[enemy_id]
            self.game_state.add_gold(dead_enemy.bounty)
            self._handle_on_death_effects(dead_enemy)
            self.director_ai.record_enemy_death(dead_enemy)
            self.targeting_manager.remove_entity(dead_enemy)
            del self.enemies[enemy_id]

        dead_projectile_ids = [
            pid for pid, p in self.projectiles.items() if not p.is_alive
        ]
        for proj_id in dead_projectile_ids:
            entity_to_remove = self.projectiles[proj_id]
            if not isinstance(entity_to_remove, Projectile):
                self.targeting_manager.remove_entity(entity_to_remove)
            del self.projectiles[proj_id]

        dead_tower_ids = [tid for tid, t in self.towers.items() if not t.is_alive]
        for tower_id in dead_tower_ids:
            dead_tower = self.towers[tower_id]
            self.targeting_manager.remove_entity(dead_tower)
            del self.towers[tower_id]

    def _handle_on_death_effects(self, dead_enemy: Enemy):
        """Checks for on-death effects, like explosions."""
        for effect in dead_enemy.effect_handler.status_effects:
            if effect.source_entity_id:
                source_tower = self.towers.get(effect.source_entity_id)
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
        status_effects_cfg = self.configs.get("status_effects", {})
        new_enemy = None

        config = {}
        if entity_id in self.configs["boss_types"]:
            config = self.configs["boss_types"][entity_id]
            config["id"] = entity_id
            new_enemy = BossEnemy(
                boss_type_data=config,
                path=path,
                tile_size=self.tile_size,
                level=enemy_spawn_level,
                difficulty_modifier=difficulty_mod,
                status_effects_config=status_effects_cfg,
            )
        elif entity_id in self.configs["buffer_types"]:
            config = self.configs["buffer_types"][entity_id]
            config["id"] = entity_id
            new_enemy = BufferEnemy(
                enemy_type_data=config,
                level=enemy_spawn_level,
                path=path,
                tile_size=self.tile_size,
                difficulty_modifier=difficulty_mod,
                status_effects_config=status_effects_cfg,
            )
        elif entity_id in self.configs["enemy_types"]:
            config = self.configs["enemy_types"][entity_id]
            config["id"] = entity_id
            new_enemy = Enemy(
                enemy_type_data=config,
                level=enemy_spawn_level,
                path=path,
                tile_size=self.tile_size,
                difficulty_modifier=difficulty_mod,
                status_effects_config=status_effects_cfg,
            )
        else:
            logger.error(f"Could not find definition for entity ID: {entity_id}")
            return

        self.enemies[new_enemy.entity_id] = new_enemy
        self.targeting_manager.add_entity(new_enemy)

    def place_tower(self, tower_type_id: str, tile_x: int, tile_y: int) -> bool:
        """Handles the logic for a player attempting to place a new tower."""
        tower_data = self.configs.get("tower_types", {}).get(tower_type_id)
        if not tower_data or not self.grid:
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

        self.towers[new_tower.entity_id] = new_tower
        self.targeting_manager.add_entity(new_tower)
        self.grid.set_tile_type(tile_x, tile_y, "TOWER_OCCUPIED")
        return True

    def purchase_tower_upgrade(self, tower_id: uuid.UUID, upgrade_id: str):
        """Handles a request to purchase an upgrade for a specific tower."""
        target_tower = self.towers.get(tower_id)
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
        target_tower = self.towers.get(tower_id)
        if not target_tower or not self.grid:
            return

        refund_amount = int(target_tower.total_investment * self.get_salvage_rate())
        self.game_state.add_gold(refund_amount)
        tile_x = int(target_tower.pos.x // self.tile_size)
        tile_y = int(target_tower.pos.y // self.tile_size)
        if self.grid.is_valid_coord(tile_x, tile_y):
            self.grid.set_tile_type(tile_x, tile_y, "BUILDABLE")

        target_tower.kill()
        self.game_state.clear_selection()

    def change_tower_persona(self, tower_id: uuid.UUID, new_persona_id: str):
        """Finds a tower by its ID and requests it to change its persona."""
        target_tower = self.towers.get(tower_id)
        if not target_tower:
            logger.error(f"Could not find tower with ID {tower_id} to change persona.")
            return
        target_tower.set_persona(new_persona_id)

    def get_salvage_rate(self) -> float:
        """Safely retrieves the current salvage refund percentage."""
        if self.wave_manager and self.wave_manager.difficulty_settings:
            return self.wave_manager.difficulty_settings.get(
                "salvage_refund_percentage", 0.0
            )
        return 0.0
