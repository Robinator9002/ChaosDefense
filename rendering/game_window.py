# rendering/game_window.py
import pygame
import logging
import random
from pathlib import Path
from typing import Dict, Any

# --- Core Game Logic Imports ---
from game_logic.game_state import GameState
from game_logic.levels.level_manager import LevelManager
from game_logic.level_generation.grid import Grid
from game_logic.waves.wave_manager import WaveManager
from game_logic.entities.enemy import Enemy

# --- Rendering Imports ---
from rendering.sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# --- Control Constants ---
MAX_ZOOM = 3.0
ZOOM_INCREMENT = 0.07


class Game:
    """
    The main game class. Manages the game loop, event handling, state,
    and all major subsystems.
    """

    def __init__(
        self,
        game_settings: Dict,
        level_styles: Dict,
        enemy_types: Dict,
        difficulty_scaling: Dict,
        assets_path: Path,
    ):
        """
        Initializes Pygame, the window, and all game subsystems.

        This constructor is now the central point for receiving all game configurations.
        """
        pygame.init()
        pygame.font.init()

        # --- Store all configurations ---
        self.game_settings = game_settings
        self.level_styles = level_styles
        self.enemy_types = enemy_types
        self.difficulty_scaling = difficulty_scaling
        self.assets_path = assets_path

        # --- Window Setup ---
        self.screen_width = self.game_settings.get("screen_width", 1280)
        self.screen_height = self.game_settings.get("screen_height", 720)
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.RESIZABLE
        )
        pygame.display.set_caption(
            self.game_settings.get("screen_title", "ChaosDefense")
        )
        self.clock = pygame.time.Clock()
        self.running = True

        # --- Game Components & State ---
        self.level_manager = LevelManager(self.level_styles)
        self.game_state: GameState | None = None
        self.wave_manager: WaveManager | None = None
        self.grid: Grid | None = None
        self.paths: list | None = None
        self.sprite_renderer: SpriteRenderer | None = None
        self.active_enemies: list[Enemy] = []

        self.background_color = (0, 0, 0)
        self.gui_font = pygame.font.SysFont("segoeui", 22, bold=True)
        self.tile_size = self.game_settings.get("tile_size", 32)
        self.difficulty_settings: Dict[str, Any] = {}

        # --- Camera & Input State ---
        self.zoom = 1.0
        self.min_zoom = 0.1
        self.camera_offset = pygame.Vector2(0, 0)
        self.is_panning = False
        self.pan_start_mouse_pos = pygame.Vector2(0, 0)
        self.pan_start_camera_offset = pygame.Vector2(0, 0)

        self._setup_game()

    def _setup_game(self):
        """
        Initializes all necessary game objects for a new game.
        """
        logger.info("--- Starting New Game Setup ---")
        self.game_state = GameState(gold=150, base_hp=20)

        # --- Level Loading ---
        try:
            preset_to_load = "Forest"  # This could be chosen from a menu later
            self.grid, self.paths, style_config = (
                self.level_manager.build_level_from_preset(preset_to_load)
            )
        except (KeyError, ValueError) as e:
            logger.critical(f"Failed to build level: {e}", exc_info=True)
            self.running = False
            return

        self.game_state.level_grid = self.grid

        # --- Wave Manager Initialization ---
        player_difficulty = self.game_settings.get("difficulty", 1)
        self.difficulty_settings = self.difficulty_scaling.get(
            str(player_difficulty), self.difficulty_scaling["1"]
        )

        level_difficulty = style_config.get("generation_params", {}).get(
            "level_difficulty", 1
        )

        self.wave_manager = WaveManager(
            difficulty_config=self.difficulty_scaling,
            enemy_types=self.enemy_types,
            player_difficulty=player_difficulty,
            initial_level_difficulty=level_difficulty,
        )

        # --- Rendering Setup ---
        self.background_color = style_config.get("background_color", (0, 0, 0))
        tile_definitions = style_config.get("tile_definitions", {})
        self.sprite_renderer = SpriteRenderer(
            grid=self.grid,
            tile_size=self.tile_size,
            style_definitions=tile_definitions,
            assets_path=self.assets_path,
        )

        self._calculate_min_zoom()
        self.zoom = self.min_zoom
        self._clamp_camera_offset()
        logger.info("--- Game Setup Complete ---")

    def run(self):
        """The main game loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        """Processes all events from the Pygame event queue."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen_width, self.screen_height = event.w, event.h
                self.screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE
                )
                self._calculate_min_zoom()
                self._clamp_camera_offset()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2 or event.button == 3:  # Middle or Right-click
                    self.is_panning = True
                    self.pan_start_mouse_pos = pygame.Vector2(event.pos)
                    self.pan_start_camera_offset = self.camera_offset.copy()
                elif event.button == 4:
                    self.zoom = min(self.zoom + ZOOM_INCREMENT, MAX_ZOOM)
                    self._clamp_camera_offset()
                elif event.button == 5:
                    self.zoom = max(self.zoom - ZOOM_INCREMENT, self.min_zoom)
                    self._clamp_camera_offset()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2 or event.button == 3:
                    self.is_panning = False
            elif event.type == pygame.MOUSEMOTION:
                if self.is_panning:
                    mouse_delta = pygame.Vector2(event.pos) - self.pan_start_mouse_pos
                    self.camera_offset = self.pan_start_camera_offset + mouse_delta
                    self._clamp_camera_offset()

    def _update(self, dt: float):
        """Updates all game logic, including wave spawning and entity updates."""
        if self.game_state.game_over:
            return

        # --- Wave Spawning Logic ---
        if self.wave_manager.update(dt):
            # The WaveManager signals that it's time to spawn a new wave.
            wave_data = self.wave_manager.generate_wave()
            newly_spawned = []
            stat_modifier = self.difficulty_settings.get("stat_modifier", 1.0)

            for enemy_info in wave_data:
                enemy_type = enemy_info["type"]
                enemy_level = enemy_info["level"]

                if enemy_type not in self.enemy_types:
                    logger.error(f"Unknown enemy type '{enemy_type}' in wave data.")
                    continue

                if not self.paths:
                    logger.error("No paths available for enemy spawning.")
                    continue
                chosen_path = random.choice(self.paths)

                # Create the enemy instance with all required parameters.
                enemy = Enemy(
                    enemy_type_data=self.enemy_types[enemy_type],
                    level=enemy_level,
                    path=chosen_path,
                    tile_size=self.tile_size,
                    difficulty_modifier=stat_modifier,
                )
                self.active_enemies.append(enemy)
                newly_spawned.append(enemy)

            # Inform the wave manager about the newly created enemies.
            self.wave_manager.register_spawned_enemies(newly_spawned)

        # --- Update all active enemies ---
        for enemy in self.active_enemies:
            enemy.update(dt, self.game_state)

        # --- Clear dead enemies and award gold ---
        dead_enemies = [e for e in self.active_enemies if not e.is_alive]
        if dead_enemies:
            self.active_enemies = [e for e in self.active_enemies if e.is_alive]
            for dead_enemy in dead_enemies:
                self.game_state.add_gold(dead_enemy.bounty)
            # Update the wave manager's internal list to reflect the cleared enemies.
            self.wave_manager.active_enemies = self.active_enemies

        # Update game state with the current wave number for the GUI.
        self.game_state.current_wave_number = self.wave_manager.current_wave_number

    def _draw(self):
        """Draws everything to the screen in the correct order."""
        self.screen.fill(self.background_color)

        # Draw the static map first.
        if self.sprite_renderer:
            self.sprite_renderer.draw(self.screen, self.camera_offset, self.zoom)

        # Draw all active enemies on top of the map.
        for enemy in self.active_enemies:
            enemy.draw(self.screen, self.camera_offset, self.zoom)

        # Draw the GUI on top of everything else.
        self._draw_gui()
        pygame.display.flip()

    def _draw_gui(self):
        """Draws the static user interface elements."""
        if not self.game_state or not self.wave_manager:
            return
        colors = {"gold": (255, 215, 0), "hp": (220, 20, 60), "wave": (0, 191, 255)}
        padding, y_pos = 20, 15
        wave_text = f"Wave: {self.game_state.current_wave_number} / {self.wave_manager.max_waves}"
        surfaces = [
            self.gui_font.render(f"Gold: {self.game_state.gold}", True, colors["gold"]),
            self.gui_font.render(
                f"Base HP: {self.game_state.base_hp}", True, colors["hp"]
            ),
            self.gui_font.render(wave_text, True, colors["wave"]),
        ]
        panel_width = sum(s.get_width() for s in surfaces) + (
            padding * (len(surfaces) + 1)
        )
        panel_height = max(s.get_height() for s in surfaces) + (padding / 2)
        panel_rect = pygame.Rect(5, 5, panel_width, panel_height)
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 150))
        self.screen.blit(panel_surf, panel_rect.topleft)
        current_x = panel_rect.left + padding
        for surf in surfaces:
            self.screen.blit(surf, (current_x, y_pos))
            current_x += surf.get_width() + padding

    def _calculate_min_zoom(self):
        if not self.sprite_renderer:
            return
        map_w = self.sprite_renderer.map_surface.get_width()
        map_h = self.sprite_renderer.map_surface.get_height()
        if map_w == 0 or map_h == 0:
            return
        self.min_zoom = min(self.screen_width / map_w, self.screen_height / map_h)

    def _clamp_camera_offset(self):
        if not self.sprite_renderer:
            return
        map_w, map_h = (
            self.sprite_renderer.map_surface.get_width() * self.zoom,
            self.sprite_renderer.map_surface.get_height() * self.zoom,
        )
        max_x, min_x = 0, self.screen_width - map_w
        max_y, min_y = 0, self.screen_height - map_h
        self.camera_offset.x = (
            (self.screen_width - map_w) / 2
            if map_w < self.screen_width
            else max(min_x, min(self.camera_offset.x, max_x))
        )
        self.camera_offset.y = (
            (self.screen_height - map_h) / 2
            if map_h < self.screen_height
            else max(min_y, min(self.camera_offset.y, max_y))
        )
