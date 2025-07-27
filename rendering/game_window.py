# rendering/game_window.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# --- Game Logic Imports ---
from game_logic.game_manager import GameManager

# --- Rendering Imports ---
from rendering.sprite_renderer import SpriteRenderer
from rendering.ui_manager import UIManager  # Import the new UIManager

logger = logging.getLogger(__name__)

# --- Control Constants ---
MAX_ZOOM = 3.0
MIN_ZOOM_CLAMP = 0.1
ZOOM_INCREMENT = 0.07


class Game:
    """
    The main window and rendering engine for the game.
    """

    def __init__(self, all_configs: Dict[str, Any], assets_path: Path):
        """
        Initializes Pygame, the window, and all core systems.
        """
        pygame.init()
        pygame.font.init()

        self.game_settings = all_configs["game_settings"]
        self.assets_path = assets_path

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

        # --- Core Logic and UI Managers ---
        self.game_manager = GameManager(all_configs)
        self.ui_manager = UIManager(self.screen.get_rect(), all_configs, assets_path)

        # --- Rendering Components ---
        self.sprite_renderer: Optional[SpriteRenderer] = None
        self.background_color = (0, 0, 0)
        self.tile_size = self.game_settings.get("tile_size", 32)

        # --- Camera & Input State ---
        self.zoom = 1.0
        self.min_zoom = MIN_ZOOM_CLAMP
        self.camera_offset = pygame.Vector2(0, 0)
        self.is_panning = False
        self.pan_start_mouse_pos = pygame.Vector2(0, 0)
        self.pan_start_camera_offset = pygame.Vector2(0, 0)

        self._setup_rendering()

    def _setup_rendering(self):
        """Initializes rendering components based on the game logic's state."""
        logger.info("--- Initializing Rendering Components ---")

        grid = self.game_manager.grid
        if not grid:
            logger.critical(
                "GameManager failed to provide a grid. Cannot setup rendering."
            )
            self.running = False
            return

        style_config = {}
        for style in self.game_manager.level_manager.level_styles.values():
            if style.get("generation_params", {}).get("grid_width") == grid.width:
                style_config = style
                break

        self.background_color = style_config.get("background_color", (10, 10, 10))
        tile_definitions = style_config.get("tile_definitions", {})

        self.sprite_renderer = SpriteRenderer(
            grid=grid,
            tile_size=self.tile_size,
            style_definitions=tile_definitions,
            assets_path=self.assets_path,
        )

        self._calculate_min_zoom()
        self.zoom = self.min_zoom
        self._center_camera()
        logger.info("--- Rendering Setup Complete ---")

    def run(self):
        """The main game loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        """Processes events, delegating first to the UI, then the game world."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # --- 1. Pass event to UIManager first ---
            ui_handled_event = self.ui_manager.handle_event(
                event, self.game_manager.game_state
            )

            # --- 2. If UI did not handle it, process as a game world event ---
            if not ui_handled_event:
                if event.type == pygame.VIDEORESIZE:
                    self._on_resize(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_map_click(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 2 or event.button == 3:
                        self.is_panning = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.is_panning:
                        self._handle_pan(event)

    def _handle_map_click(self, event):
        """Handles mouse clicks that occur on the game map (not the UI)."""
        if event.button == 1:  # Left Click for placing towers
            # Check if a tower is selected for building
            tower_to_build = self.game_manager.game_state.selected_tower_to_build
            if tower_to_build:
                world_pos = self._screen_to_world(pygame.Vector2(event.pos))
                tile_x = int(world_pos.x // self.tile_size)
                tile_y = int(world_pos.y // self.tile_size)

                self.game_manager.place_tower(tower_to_build, tile_x, tile_y)
                # For now, automatically deselect after one placement.
                self.game_manager.game_state.clear_selection()

        elif (
            event.button == 2 or event.button == 3
        ):  # Middle or Right Click for panning
            self.is_panning = True
            self.pan_start_mouse_pos = pygame.Vector2(event.pos)
            self.pan_start_camera_offset = self.camera_offset.copy()
        elif event.button == 4:  # Scroll Up
            self.zoom = min(self.zoom + ZOOM_INCREMENT, MAX_ZOOM)
            self._clamp_camera_offset()
        elif event.button == 5:  # Scroll Down
            self.zoom = max(self.zoom - ZOOM_INCREMENT, self.min_zoom)
            self._clamp_camera_offset()

    def _handle_pan(self, event):
        """Handles camera movement when panning."""
        mouse_delta = pygame.Vector2(event.pos) - self.pan_start_mouse_pos
        self.camera_offset = self.pan_start_camera_offset + mouse_delta
        self._clamp_camera_offset()

    def _on_resize(self, event):
        """Handles the window being resized."""
        self.screen_width, self.screen_height = event.w, event.h
        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        self.ui_manager.screen_rect = (
            self.screen.get_rect()
        )  # Important: update UI Manager
        self._calculate_min_zoom()
        self._clamp_camera_offset()

    def _update(self, dt: float):
        """Updates all game systems."""
        self.game_manager.update(dt)
        self.ui_manager.update(dt, self.game_manager.game_state)

    def _draw(self):
        """Draws the entire game state to the screen."""
        self.screen.fill(self.background_color)

        # Draw the world (map and entities)
        if self.sprite_renderer:
            self.sprite_renderer.draw(self.screen, self.camera_offset, self.zoom)

        all_entities = (
            self.game_manager.enemies
            + self.game_manager.towers
            + self.game_manager.projectiles
        )
        for entity in all_entities:
            entity.draw(self.screen, self.camera_offset, self.zoom)

        # Draw the UI on top of everything
        self.ui_manager.draw(self.screen, self.game_manager.game_state)

        pygame.display.flip()

    def _screen_to_world(self, screen_pos: pygame.Vector2) -> pygame.Vector2:
        return (screen_pos - self.camera_offset) / self.zoom

    def _calculate_min_zoom(self):
        if not self.sprite_renderer:
            return
        map_w = self.sprite_renderer.map_surface.get_width()
        map_h = self.sprite_renderer.map_surface.get_height()
        if map_w > 0 and map_h > 0:
            self.min_zoom = max(
                MIN_ZOOM_CLAMP,
                min(self.screen_width / map_w, self.screen_height / map_h),
            )

    def _center_camera(self):
        if not self.sprite_renderer:
            return
        map_w = self.sprite_renderer.map_surface.get_width() * self.zoom
        map_h = self.sprite_renderer.map_surface.get_height() * self.zoom
        self.camera_offset.x = (self.screen_width - map_w) / 2
        self.camera_offset.y = (self.screen_height - map_h) / 2
        self._clamp_camera_offset()

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
            max(min_x, min(self.camera_offset.x, max_x))
            if map_w > self.screen_width
            else (self.screen_width - map_w) / 2
        )
        self.camera_offset.y = (
            max(min_y, min(self.camera_offset.y, max_y))
            if map_h > self.screen_height
            else (self.screen_height - map_h) / 2
        )
