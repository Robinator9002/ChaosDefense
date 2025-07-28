# rendering/game_window.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# --- Game Logic Imports ---
from game_logic.game_manager import GameManager

# --- Rendering Imports ---
from rendering.sprite_renderer import SpriteRenderer
from rendering.ui.ui_manager import UIManager

logger = logging.getLogger(__name__)

# --- Control Constants ---
MAX_ZOOM = 3.0
MIN_ZOOM_CLAMP = 0.1
ZOOM_INCREMENT = 0.07


class Game:
    """
    The main window and rendering engine for the game. This class is the
    bridge between player input (mouse, keyboard), the game's logical state
    (GameManager), and what is drawn to the screen.
    """

    def __init__(self, all_configs: Dict[str, Any], assets_path: Path):
        """
        Initializes Pygame, the window, and all core systems.
        """
        pygame.init()
        pygame.font.init()

        self.game_settings = all_configs["game_settings"]
        self.assets_path = assets_path

        # --- Screen and Display Setup ---
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

        # --- Core System Initialization ---
        self.game_manager = GameManager(all_configs)
        self.ui_manager = UIManager(
            self.screen.get_rect(), self.game_manager, assets_path
        )

        # --- Rendering and Camera State ---
        self.sprite_renderer: Optional[SpriteRenderer] = None
        self.background_color = (0, 0, 0)
        self.gui_font = pygame.font.SysFont("segoeui", 22, bold=True)
        self.tile_size = self.game_settings.get("tile_size", 32)

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
            # --- BUG FIX: VALIDATION STEP ---
            # Ensure we only process actual level style dictionaries, skipping
            # any comments or other non-dict data in the JSON file.
            if isinstance(style, dict):
                gen_params = style.get("generation_params", {})
                if gen_params.get("grid_width") == grid.width:
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

            ui_handled_event = self.ui_manager.handle_event(
                event, self.game_manager.game_state
            )

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
                # --- NEW: Handle Keyboard Input for Hotkeys ---
                elif event.type == pygame.KEYDOWN:
                    self._handle_keyboard_input(event.key)

    def _handle_keyboard_input(self, key):
        """Handles keyboard presses for game actions, like tower selection."""
        # Map pygame key constants to numbers 1-9
        key_to_number = {
            pygame.K_1: 1,
            pygame.K_2: 2,
            pygame.K_3: 3,
            pygame.K_4: 4,
            pygame.K_5: 5,
            pygame.K_6: 6,
            pygame.K_7: 7,
            pygame.K_8: 8,
            pygame.K_9: 9,
        }

        if key in key_to_number:
            number_pressed = key_to_number[key]
            hotkey_index = number_pressed - 1

            # Check if the pressed number corresponds to a valid tower hotkey
            if 0 <= hotkey_index < len(self.ui_manager.hotkey_map):
                tower_id = self.ui_manager.hotkey_map[hotkey_index]
                game_state = self.game_manager.game_state

                # Toggle selection logic
                if game_state.selected_tower_to_build == tower_id:
                    game_state.clear_selection()
                else:
                    game_state.selected_tower_to_build = tower_id
                    logger.info(
                        f"Player selected '{tower_id}' for building via hotkey {number_pressed}."
                    )

    def _handle_map_click(self, event):
        """
        Handles mouse clicks that occur on the game map (not the UI).
        """
        if event.button == 1:
            game_state = self.game_manager.game_state

            if game_state.selected_tower_to_build:
                world_pos = self._screen_to_world(pygame.Vector2(event.pos))
                tile_x = int(world_pos.x // self.tile_size)
                tile_y = int(world_pos.y // self.tile_size)
                self.game_manager.place_tower(
                    game_state.selected_tower_to_build, tile_x, tile_y
                )
                game_state.clear_selection()
                return

            world_pos = self._screen_to_world(pygame.Vector2(event.pos))
            clicked_on_tower = False
            for tower in self.game_manager.towers:
                if tower.rect.collidepoint(world_pos):
                    if game_state.selected_entity_id == tower.entity_id:
                        game_state.clear_selection()
                    else:
                        game_state.selected_entity_id = tower.entity_id
                        logger.info(
                            f"Player selected tower {tower.entity_id} for upgrade."
                        )
                    clicked_on_tower = True
                    break

            if not clicked_on_tower:
                game_state.clear_selection()

        elif event.button == 2 or event.button == 3:
            self.is_panning = True
            self.pan_start_mouse_pos = pygame.Vector2(event.pos)
            self.pan_start_camera_offset = self.camera_offset.copy()

        elif event.button == 4:
            self.zoom = min(self.zoom + ZOOM_INCREMENT, MAX_ZOOM)
            self._clamp_camera_offset()
        elif event.button == 5:
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
        self.ui_manager.screen_rect = self.screen.get_rect()
        self._calculate_min_zoom()
        self._clamp_camera_offset()

    def _update(self, dt: float):
        """Updates all game systems."""
        self.game_manager.update(dt)
        self.ui_manager.update(dt, self.game_manager.game_state)

    def _draw(self):
        """Draws the entire game state to the screen."""
        self.screen.fill(self.background_color)

        if self.sprite_renderer:
            self.sprite_renderer.draw(self.screen, self.camera_offset, self.zoom)

        all_entities = (
            self.game_manager.enemies
            + self.game_manager.towers
            + self.game_manager.projectiles
        )
        for entity in all_entities:
            entity.draw(self.screen, self.camera_offset, self.zoom)

        self._draw_top_gui()
        self.ui_manager.draw(self.screen, self.game_manager.game_state)

        pygame.display.flip()

    def _draw_top_gui(self):
        """Draws the static user interface elements like gold, hp, and wave count."""
        state = self.game_manager.game_state
        wave_mgr = self.game_manager.wave_manager
        if not state or not wave_mgr:
            return

        colors = {"gold": (255, 215, 0), "hp": (220, 20, 60), "wave": (0, 191, 255)}
        padding, y_pos = 20, 15
        wave_text = f"Wave: {state.current_wave_number} / {wave_mgr.max_waves}"

        surfaces = [
            self.gui_font.render(f"Gold: {state.gold}", True, colors["gold"]),
            self.gui_font.render(f"Base HP: {state.base_hp}", True, colors["hp"]),
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

    def _screen_to_world(self, screen_pos: pygame.Vector2) -> pygame.Vector2:
        """Converts screen coordinates to world (map) coordinates."""
        return (screen_pos - self.camera_offset) / self.zoom

    def _calculate_min_zoom(self):
        """Calculates the minimum zoom level to fit the whole map on screen."""
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
        """Centers the camera on the map."""
        if not self.sprite_renderer:
            return
        map_w = self.sprite_renderer.map_surface.get_width() * self.zoom
        map_h = self.sprite_renderer.map_surface.get_height() * self.zoom
        self.camera_offset.x = (self.screen_width - map_w) / 2
        self.camera_offset.y = (self.screen_height - map_h) / 2
        self._clamp_camera_offset()

    def _clamp_camera_offset(self):
        """Prevents the camera from panning off the edge of the map."""
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
