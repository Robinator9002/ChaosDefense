# rendering/game_window.py
import pygame
import logging
from pathlib import Path

# Project-specific imports for core components.
from game_logic.game_state import GameState
from level_generation.grid import Grid
from level_generation.generator import LevelGenerator
from rendering.sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# --- Control Constants ---
MIN_ZOOM = 0.3
MAX_ZOOM = 2.5
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
        self.level_styles = level_styles
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
        self.game_state: GameState | None = None
        self.grid: Grid | None = None
        self.sprite_renderer: SpriteRenderer | None = None
        self.background_color = (0, 0, 0)
        self.gui_font = pygame.font.SysFont("segoeui", 24)

        # --- Camera & Input State ---
        self.zoom = 1.0
        self.camera_offset = pygame.Vector2(0, 0)
        self.is_panning = False
        self.pan_start_mouse_pos = pygame.Vector2(0, 0)
        self.pan_start_camera_offset = pygame.Vector2(0, 0)

        self._setup_game()

    def _setup_game(self):
        """
        Initializes all necessary game objects before the main loop starts.
        """
        logger.info("--- Starting Game Setup ---")
        self.game_state = GameState(gold=150, base_hp=20)

        grid_width = self.game_settings.get("grid_width", 40)
        grid_height = self.game_settings.get("grid_height", 22)
        self.grid = Grid(grid_width, grid_height)

        LevelGenerator.generate(self.grid)
        self.game_state.level_grid = self.grid

        current_style = self.level_styles.get("Forest", {})
        style_definitions = current_style.get("tile_definitions", {})
        self.background_color = current_style.get("background_color", (0, 0, 0))

        tile_size = self.game_settings.get("tile_size", 32)
        self.sprite_renderer = SpriteRenderer(
            grid=self.grid,
            tile_size=tile_size,
            style_definitions=style_definitions,
            assets_path=self.assets_path,
        )
        logger.info("--- Game Setup Complete ---")

    def run(self):
        """The main game loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time in seconds.
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

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:  # Middle mouse button
                    self.is_panning = True
                    self.pan_start_mouse_pos = pygame.Vector2(event.pos)
                    self.pan_start_camera_offset = self.camera_offset.copy()
                elif event.button == 4:  # Scroll up
                    self.zoom = min(MAX_ZOOM, self.zoom + ZOOM_INCREMENT)
                elif event.button == 5:  # Scroll down
                    self.zoom = max(MIN_ZOOM, self.zoom - ZOOM_INCREMENT)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    self.is_panning = False

            elif event.type == pygame.MOUSEMOTION:
                if self.is_panning:
                    mouse_delta = pygame.Vector2(event.pos) - self.pan_start_mouse_pos
                    self.camera_offset = self.pan_start_camera_offset + mouse_delta

    def _update(self, dt: float):
        """
        Updates game logic. (Currently empty, for future use).
        Args:
            dt (float): The time elapsed since the last frame, in seconds.
        """
        pass

    def _draw(self):
        """Draws everything to the screen."""
        self.screen.fill(self.background_color)

        if self.sprite_renderer:
            self.sprite_renderer.draw(self.screen, self.camera_offset, self.zoom)

        self._draw_gui()

        pygame.display.flip()

    def _draw_gui(self):
        """Draws the static user interface elements."""
        if not self.game_state:
            return

        # Define colors for text
        colors = {"gold": (255, 215, 0), "hp": (220, 20, 60), "wave": (0, 191, 255)}

        # Create text surfaces
        gold_text = f"Gold: {self.game_state.gold}"
        hp_text = f"Base HP: {self.game_state.base_hp}"
        wave_text = f"Wave: {self.game_state.current_wave_number}"

        gold_surf = self.gui_font.render(gold_text, True, colors["gold"])
        hp_surf = self.gui_font.render(hp_text, True, colors["hp"])
        wave_surf = self.gui_font.render(wave_text, True, colors["wave"])

        # Draw a background panel for readability
        panel_rect = pygame.Rect(5, 5, 220, 100)
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 150))
        self.screen.blit(panel_surf, panel_rect.topleft)

        # Blit text onto the screen
        self.screen.blit(gold_surf, (15, 15))
        self.screen.blit(hp_surf, (15, 45))
        self.screen.blit(wave_surf, (15, 75))
