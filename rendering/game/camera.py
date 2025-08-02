# rendering/game/camera.py
import pygame
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# --- Camera Control Constants ---
MAX_ZOOM = 3.0
MIN_ZOOM_CLAMP = 0.1
ZOOM_INCREMENT = 0.07


class Camera:
    """
    Manages the game's viewport, including zoom, panning, and coordinate
    transformations. This class encapsulates all camera-related logic,
    decoupling it from the main game window.
    """

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initializes the Camera.

        Args:
            screen_width (int): The initial width of the game screen.
            screen_height (int): The initial height of the game screen.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.zoom = 1.0
        self.min_zoom = MIN_ZOOM_CLAMP
        self.offset = pygame.Vector2(0, 0)

        # --- Panning State ---
        self.is_panning = False
        self.pan_start_mouse_pos = pygame.Vector2(0, 0)
        self.pan_start_camera_offset = pygame.Vector2(0, 0)

    def set_map_renderer(self, sprite_renderer: "SpriteRenderer"):
        """
        Provides the camera with a reference to the map renderer, which is
        needed to calculate zoom limits and centering.

        Args:
            sprite_renderer (SpriteRenderer): The main map renderer instance.
        """
        self.sprite_renderer = sprite_renderer
        self._calculate_min_zoom()
        self.zoom = self.min_zoom
        self.center_on_map()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Processes Pygame events specifically related to camera control.

        Args:
            event (pygame.event.Event): The event to process.

        Returns:
            bool: True if the event was handled by the camera, False otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:  # Middle mouse button for panning
                self.is_panning = True
                self.pan_start_mouse_pos = pygame.Vector2(event.pos)
                self.pan_start_camera_offset = self.offset.copy()
                return True
            elif event.button == 4:  # Scroll up to zoom in
                self.zoom = min(self.zoom + ZOOM_INCREMENT, MAX_ZOOM)
                self._clamp_offset()
                return True
            elif event.button == 5:  # Scroll down to zoom out
                self.zoom = max(self.zoom - ZOOM_INCREMENT, self.min_zoom)
                self._clamp_offset()
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                self.is_panning = False
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.is_panning:
                mouse_delta = pygame.Vector2(event.pos) - self.pan_start_mouse_pos
                self.offset = self.pan_start_camera_offset + mouse_delta
                self._clamp_offset()
                return True

        return False

    def on_resize(self, new_width: int, new_height: int):
        """
        Updates the camera's screen dimensions and recalculates zoom/offset
        constraints when the window is resized.

        Args:
            new_width (int): The new screen width.
            new_height (int): The new screen height.
        """
        self.screen_width = new_width
        self.screen_height = new_height
        self._calculate_min_zoom()
        self._clamp_offset()

    def screen_to_world(self, screen_pos: pygame.Vector2) -> pygame.Vector2:
        """Converts screen coordinates to world (map) coordinates."""
        return (screen_pos - self.offset) / self.zoom

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

    def center_on_map(self):
        """Centers the camera on the map."""
        if not self.sprite_renderer:
            return
        map_w = self.sprite_renderer.map_surface.get_width() * self.zoom
        map_h = self.sprite_renderer.map_surface.get_height() * self.zoom
        self.offset.x = (self.screen_width - map_w) / 2
        self.offset.y = (self.screen_height - map_h) / 2
        self._clamp_offset()

    def _clamp_offset(self):
        """Prevents the camera from panning off the edge of the map."""
        if not self.sprite_renderer:
            return
        map_w, map_h = (
            self.sprite_renderer.map_surface.get_width() * self.zoom,
            self.sprite_renderer.map_surface.get_height() * self.zoom,
        )
        # Calculate the maximum and minimum allowed offset values.
        # max_x is typically 0 (can't pan left past the edge).
        # min_x is negative (screen_width - map_width), allowing panning right.
        max_x, min_x = 0, self.screen_width - map_w
        max_y, min_y = 0, self.screen_height - map_h

        # If the map is smaller than the screen, center it instead of clamping.
        self.offset.x = (
            max(min_x, min(self.offset.x, max_x))
            if map_w > self.screen_width
            else (self.screen_width - map_w) / 2
        )
        self.offset.y = (
            max(min_y, min(self.offset.y, max_y))
            if map_h > self.screen_height
            else (self.screen_height - map_h) / 2
        )
