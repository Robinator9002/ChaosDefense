# rendering/game_window.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from enum import Enum, auto

from game_logic.game_manager import GameManager
from rendering.sprite_renderer import SpriteRenderer
from rendering.hud.ui_manager import UIManager
from rendering.menu.menu_manager import MenuManager
from rendering.game.camera import Camera
from rendering.game.input_handler import InputHandler
from rendering.text.font_manager import FontManager


if TYPE_CHECKING:
    from game_logic.progression.progression_manager import ProgressionManager

logger = logging.getLogger(__name__)


class GameState(Enum):
    MAIN_MENU = auto()
    IN_GAME = auto()


class Game:
    """
    The main window and application class for the game. It acts as a high-level
    state machine, orchestrating all of its specialized manager classes.
    """

    def __init__(
        self,
        all_configs: Dict[str, Any],
        assets_path: Path,
        progression_manager: "ProgressionManager",
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes the window and all high-level systems.
        """
        # --- FIX: Pygame initialization is now done in main.py ---
        # This class now assumes Pygame has already been initialized.

        self.all_configs = all_configs
        self.game_settings = all_configs["game_settings"]
        self.assets_path = assets_path
        self.progression_manager = progression_manager
        self.ui_theme = ui_theme
        self.font_manager = font_manager

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

        self.game_state = GameState.MAIN_MENU

        self.menu_manager = MenuManager(
            screen_rect=self.screen.get_rect(),
            progression_manager=self.progression_manager,
            all_configs=self.all_configs,
            ui_theme=self.ui_theme,
            font_manager=self.font_manager,
            start_level_callback=self._start_new_game,
            quit_callback=self._quit_game,
        )
        self.game_manager: Optional[GameManager] = None
        self.ui_manager: Optional[UIManager] = None
        self.sprite_renderer: Optional[SpriteRenderer] = None
        self.camera: Optional[Camera] = None
        self.input_handler: Optional[InputHandler] = None

        self.background_color = self.ui_theme.get("colors", {}).get(
            "background_primary", (15, 20, 25)
        )

    def _start_new_game(self, level_id: str):
        """
        Initializes all components for a new game session on a specific level.
        """
        logger.info(f"--- Starting New Game on level: {level_id} ---")

        # --- MODIFIED: Removed obsolete call to apply_global_upgrades ---
        # The GameManager's __init__ method now handles the application of
        # global modifiers internally. This call was causing the crash and
        # is no longer necessary with the new architecture.
        self.game_manager = GameManager(
            self.all_configs, self.progression_manager, level_id
        )

        self.ui_manager = UIManager(
            screen_rect=self.screen.get_rect(),
            game_manager=self.game_manager,
            progression_manager=self.progression_manager,
            assets_path=self.assets_path,
            ui_theme=self.ui_theme,
            font_manager=self.font_manager,
        )

        self.camera = Camera(self.screen_width, self.screen_height)
        self.input_handler = InputHandler(
            game_manager=self.game_manager,
            ui_manager=self.ui_manager,
            camera=self.camera,
        )

        self._setup_rendering()
        self.game_state = GameState.IN_GAME

    def _return_to_main_menu(self):
        """
        Handles the transition from an ended game back to the main menu.
        """
        logger.info("Returning to main menu.")
        self.game_manager = None
        self.ui_manager = None
        self.sprite_renderer = None
        self.camera = None
        self.input_handler = None

        self.background_color = self.ui_theme.get("colors", {}).get(
            "background_primary", (15, 20, 25)
        )
        self.menu_manager.rebuild_all_screens()
        self.game_state = GameState.MAIN_MENU

    def _quit_game(self):
        """Sets the running flag to false to exit the main game loop."""
        self.running = False

    def _setup_rendering(self):
        """Initializes rendering components."""
        if not self.game_manager or not self.camera:
            logger.critical("Cannot setup rendering without GameManager and Camera.")
            self.running = False
            return

        grid = self.game_manager.grid
        if not grid:
            logger.critical("GameManager failed to provide a grid.")
            self.running = False
            return

        style_config = self.game_manager.level_manager.level_styles.get(
            self.game_manager.current_level_id, {}
        )
        self.background_color = style_config.get("background_color", (10, 10, 10))
        tile_definitions = style_config.get("tile_definitions", {})

        self.sprite_renderer = SpriteRenderer(
            grid=grid,
            tile_size=self.game_manager.tile_size,
            style_definitions=tile_definitions,
            assets_path=self.assets_path,
        )

        self.camera.set_map_renderer(self.sprite_renderer)
        logger.info("--- Rendering Setup Complete ---")

    def run(self):
        """The main application loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        """Processes all Pygame events based on the current game state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.VIDEORESIZE:
                self._on_resize(event)

            if self.game_state == GameState.MAIN_MENU:
                self.menu_manager.handle_event(event)

            elif self.game_state == GameState.IN_GAME:
                if (
                    not self.ui_manager
                    or not self.game_manager
                    or not self.camera
                    or not self.input_handler
                ):
                    continue

                ui_handled = self.ui_manager.handle_event(
                    event, self.game_manager.game_state
                )
                if not ui_handled:
                    camera_handled = self.camera.handle_event(event)
                    if not camera_handled:
                        self.input_handler.handle_event(event)

    def _on_resize(self, event):
        """Handles the window being resized."""
        self.screen_width, self.screen_height = event.w, event.h
        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        if self.ui_manager:
            self.ui_manager.on_resize(self.screen.get_rect())
        if self.camera:
            self.camera.on_resize(event.w, event.h)
        if self.menu_manager:
            self.menu_manager.on_resize(self.screen.get_rect())

    def _update(self, dt: float):
        """Updates all systems based on the current game state."""
        if self.game_state == GameState.MAIN_MENU:
            self.menu_manager.update(dt)

        elif self.game_state == GameState.IN_GAME:
            if self.game_manager and self.ui_manager:
                self.game_manager.update(dt)
                self.ui_manager.update(dt, self.game_manager.game_state)

                gs = self.game_manager.game_state
                if gs.victory or gs.game_over:
                    self.game_manager.end_game_session(victory=gs.victory)
                    self._return_to_main_menu()

    def _draw(self):
        """Draws the entire game state to the screen."""
        self.screen.fill(self.background_color)

        if self.game_state == GameState.MAIN_MENU:
            self.menu_manager.draw(self.screen)

        elif self.game_state == GameState.IN_GAME:
            if (
                self.sprite_renderer
                and self.game_manager
                and self.ui_manager
                and self.camera
            ):
                cam_offset = self.camera.offset
                cam_zoom = self.camera.zoom

                self.sprite_renderer.draw(self.screen, cam_offset, cam_zoom)

                all_entities = (
                    list(self.game_manager.enemies.values())
                    + list(self.game_manager.towers.values())
                    + list(self.game_manager.projectiles.values())
                )
                for entity in all_entities:
                    entity.draw(self.screen, cam_offset, cam_zoom)

                self._draw_top_gui()
                self.ui_manager.draw(self.screen, self.game_manager.game_state)

        pygame.display.flip()

    def _draw_top_gui(self):
        """Draws the static user interface elements like gold, hp, and wave count."""
        if not self.game_manager:
            return

        state = self.game_manager.game_state
        wave_mgr = self.game_manager.wave_manager
        if not state or not wave_mgr:
            return

        colors = self.ui_theme.get("colors", {})
        layout = self.ui_theme.get("layout", {})
        font = self.font_manager.get_font("body_medium")

        color_gold = colors.get("text_accent", (255, 215, 0))
        color_hp = colors.get("text_error", (220, 20, 60))
        color_wave = colors.get("text_primary", (0, 191, 255))
        padding = layout.get("padding_medium", 15)
        y_pos = 15

        wave_text = f"Wave: {state.current_wave_number} / {wave_mgr.max_waves}"
        surfaces = [
            font.render(f"Gold: {state.gold}", True, color_gold),
            font.render(f"Base HP: {state.base_hp}", True, color_hp),
            font.render(wave_text, True, color_wave),
        ]
        panel_width = sum(s.get_width() for s in surfaces) + (
            padding * (len(surfaces) + 1)
        )
        panel_height = max(s.get_height() for s in surfaces) + (padding / 2)
        panel_rect = pygame.Rect(5, 5, panel_width, panel_height)

        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        bg_color_list = colors.get("panel_primary", [0, 0, 0])
        panel_surf.fill(tuple(bg_color_list) + (200,))
        self.screen.blit(panel_surf, panel_rect.topleft)

        current_x = panel_rect.left + padding
        for surf in surfaces:
            self.screen.blit(surf, (current_x, y_pos))
            current_x += surf.get_width() + padding
