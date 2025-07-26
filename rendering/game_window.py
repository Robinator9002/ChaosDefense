# rendering/game_window.py
import pygame
import logging
from pathlib import Path

# Project-specific imports for core components.
from game_logic.game_state import GameState

# Correctly import the LevelManager from its new location
from game_logic.levels.level_manager import LevelManager

# Import the missing Grid class
from level_generation.grid import Grid
from rendering.sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# --- Control Constants ---
MAX_ZOOM = 3.0
ZOOM_INCREMENT = 0.07


class Game:
    """
    The main game class. Manages the game loop, event handling, state,
    and rendering orchestration.
    """

    def __init__(self, game_settings: dict, level_styles: dict, assets_path: Path):
        """
        Initializes Pygame, the window, and all game subsystems.

        Args:
            game_settings (dict): Loaded configuration from game_settings.json.
            level_styles (dict): Loaded configuration from level_styles.json.
            assets_path (Path): The path to the 'assets' directory.
        """
        pygame.init()
        pygame.font.init()

        self.game_settings = game_settings
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

        # --- Game Components ---
        # The LevelManager is now responsible for level creation.
        self.level_manager = LevelManager(level_styles)
        self.game_state: GameState | None = None
        self.grid: Grid | None = None
        self.sprite_renderer: SpriteRenderer | None = None
        self.background_color = (0, 0, 0)
        self.gui_font = pygame.font.SysFont("segoeui", 22, bold=True)
        self.tile_size = self.game_settings.get("tile_size", 32)

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
        Initializes all necessary game objects before the main loop starts.
        This now uses the LevelManager to build the level from a preset.
        """
        logger.info("--- Starting Game Setup ---")
        self.game_state = GameState(gold=150, base_hp=20)

        # --- Level Loading via LevelManager ---
        # For now, we hardcode the preset to load. Later, this could come
        # from a main menu or game state.
        try:
            preset_to_load = "Forest"
            self.grid, style_config = self.level_manager.build_level_from_preset(
                preset_to_load
            )
        except (KeyError, ValueError) as e:
            logger.critical(f"Failed to build level: {e}", exc_info=True)
            self.running = False
            return

        self.game_state.level_grid = self.grid

        # Use the style config returned by the manager for rendering setup.
        self.background_color = style_config.get("background_color", (0, 0, 0))
        tile_definitions = style_config.get("tile_definitions", {})

        self.sprite_renderer = SpriteRenderer(
            grid=self.grid,
            tile_size=self.tile_size,
            style_definitions=tile_definitions,
            assets_path=self.assets_path,
        )

        # Calculate the dynamic minimum zoom level and center the camera.
        self._calculate_min_zoom()
        self.zoom = self.min_zoom  # Start fully zoomed out
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
                self.screen_width = event.w
                self.screen_height = event.h
                self.screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE
                )
                self._calculate_min_zoom()
                self._clamp_zoom()
                self._clamp_camera_offset()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2 or event.button == 3:
                    self.is_panning = True
                    self.pan_start_mouse_pos = pygame.Vector2(event.pos)
                    self.pan_start_camera_offset = self.camera_offset.copy()
                elif event.button == 4:
                    self.zoom += ZOOM_INCREMENT
                    self._clamp_zoom()
                    self._clamp_camera_offset()
                elif event.button == 5:
                    self.zoom -= ZOOM_INCREMENT
                    self._clamp_zoom()
                    self._clamp_camera_offset()

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2 or event.button == 3:
                    self.is_panning = False

            elif event.type == pygame.MOUSEMOTION:
                if self.is_panning:
                    mouse_delta = pygame.Vector2(event.pos) - self.pan_start_mouse_pos
                    self.camera_offset = self.pan_start_camera_offset + mouse_delta
                    self._clamp_camera_offset()

    def _calculate_min_zoom(self):
        """Calculates the minimum zoom to ensure the entire map is visible."""
        if not self.sprite_renderer:
            return
        map_width_px = self.sprite_renderer.map_surface.get_width()
        map_height_px = self.sprite_renderer.map_surface.get_height()

        if map_width_px == 0 or map_height_px == 0:
            return

        zoom_fit_x = self.screen_width / map_width_px
        zoom_fit_y = self.screen_height / map_height_px

        self.min_zoom = min(zoom_fit_x, zoom_fit_y)

    def _clamp_zoom(self):
        """Clamps the zoom level within the defined min/max boundaries."""
        self.zoom = max(self.min_zoom, min(self.zoom, MAX_ZOOM))

    def _clamp_camera_offset(self):
        """Prevents the camera from moving outside the map boundaries."""
        if not self.sprite_renderer:
            return

        map_w = self.sprite_renderer.map_surface.get_width() * self.zoom
        map_h = self.sprite_renderer.map_surface.get_height() * self.zoom

        max_x = 0
        min_x = self.screen_width - map_w
        max_y = 0
        min_y = self.screen_height - map_h

        if map_w < self.screen_width:
            self.camera_offset.x = (self.screen_width - map_w) / 2
        else:
            self.camera_offset.x = max(min_x, min(self.camera_offset.x, max_x))

        if map_h < self.screen_height:
            self.camera_offset.y = (self.screen_height - map_h) / 2
        else:
            self.camera_offset.y = max(min_y, min(self.camera_offset.y, max_y))

    def _update(self, dt: float):
        """Updates game logic."""
        pass

    def _draw(self):
        """Draws everything to the screen."""
        self.screen.fill(self.background_color)

        if self.sprite_renderer:
            self.sprite_renderer.draw(self.screen, self.camera_offset, self.zoom)

        self._draw_gui()
        pygame.display.flip()

    def _draw_gui(self):
        """Draws the static user interface elements in a horizontal row."""
        if not self.game_state:
            return

        colors = {"gold": (255, 215, 0), "hp": (220, 20, 60), "wave": (0, 191, 255)}
        padding = 20
        y_pos = 15

        gold_surf = self.gui_font.render(
            f"Gold: {self.game_state.gold}", True, colors["gold"]
        )
        hp_surf = self.gui_font.render(
            f"Base HP: {self.game_state.base_hp}", True, colors["hp"]
        )
        wave_surf = self.gui_font.render(
            f"Wave: {self.game_state.current_wave_number}", True, colors["wave"]
        )

        surfaces = [gold_surf, hp_surf, wave_surf]

        total_text_width = sum(s.get_width() for s in surfaces)
        total_padding = padding * (len(surfaces) + 1)
        panel_width = total_text_width + total_padding
        panel_height = max(s.get_height() for s in surfaces) + (padding / 2)

        panel_rect = pygame.Rect(5, 5, panel_width, panel_height)
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 150))
        self.screen.blit(panel_surf, panel_rect.topleft)

        current_x = panel_rect.left + padding
        for surf in surfaces:
            self.screen.blit(surf, (current_x, y_pos))
            current_x += surf.get_width() + padding
