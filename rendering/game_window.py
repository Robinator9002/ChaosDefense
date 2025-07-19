# rendering/game_window.py
import arcade
import logging
from pathlib import Path

# Import all the necessary components for our world
from game_logic.game_state import GameState
from level_generation.grid import Grid
from level_generation.generator import LevelGenerator
from .sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# --- Constants for Camera Control ---
CAMERA_SPEED = 10
MIN_SCALE = 0.5  # Zoomed out
MAX_SCALE = 3.0  # Zoomed in
SCROLL_INCREMENT = 0.1


class GameWindow(arcade.Window):
    """
    The main window for the ChaosDefense game.
    It handles drawing, user input, and camera controls. This version uses
    SpriteList scaling for zoom, which is more stable with older Arcade APIs.
    """

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        game_settings: dict,
        level_styles: dict,
        assets_path: Path,
    ):
        super().__init__(width, height, title, resizable=True)

        # --- Store configuration and paths ---
        self.game_settings = game_settings
        self.level_styles = level_styles
        self.assets_path = assets_path

        # --- Core Game Components ---
        self.game_state: GameState | None = None
        self.sprite_renderer: SpriteRenderer | None = None

        # --- World Dimensions ---
        self.tile_size = self.game_settings.get("tile_size", 32)
        self.grid_width = self.game_settings.get("grid_width", 50)
        self.grid_height = self.game_settings.get("grid_height", 50)

        self.world_width = self.grid_width * self.tile_size
        self.world_height = self.grid_height * self.tile_size

        # --- Camera and Scaling Setup ---
        # FIX #1: Initialize cameras with NO arguments to prevent the crash.
        self.camera = arcade.camera.Camera2D()
        self.ui_camera = arcade.camera.Camera2D()

        # Now, set the viewport properties manually.
        self.camera.viewport_width = width
        self.camera.viewport_height = height
        self.ui_camera.viewport_width = width
        self.ui_camera.viewport_height = height

        # Zoom is handled by scaling the world sprites.
        self.world_scale = 1.0

        # --- Keyboard State for Camera Movement ---
        self.up_pressed = False
        self.down_pressed = False
        self.left_pressed = False
        self.right_pressed = False

        logger.info("GameWindow initialized and ready for setup.")

    def setup(self):
        """Set up all game resources."""
        logger.info("GameWindow setup() called.")
        self.game_state = GameState()
        current_style_key = "Forest"
        current_style = self.level_styles.get(current_style_key)
        if not current_style:
            raise ValueError(
                f"Level style '{current_style_key}' not found in configuration."
            )
        arcade.set_background_color(current_style.get("background_color", (0, 0, 0)))
        grid = Grid(self.grid_width, self.grid_height)
        self.game_state.level_grid = LevelGenerator.generate(grid)
        self.sprite_renderer = SpriteRenderer(
            grid=self.game_state.level_grid,
            tile_size=self.tile_size,
            style_definitions=current_style.get("tile_definitions", {}),
            assets_path=self.assets_path,
        )
        self._center_camera_on_map()
        logger.info("Game setup is complete. The world has been generated.")

    def _center_camera_on_map(self):
        """Instantly move the camera to the center of the world."""
        scaled_world_width = self.world_width * self.world_scale
        scaled_world_height = self.world_height * self.world_scale

        center_x = (scaled_world_width - self.width) / 2
        center_y = (scaled_world_height - self.height) / 2

        self.camera.position = (center_x, center_y)
        self._clamp_camera()

    def on_draw(self):
        """Render the screen."""
        self.clear()
        self.camera.use()
        if self.sprite_renderer:
            self.sprite_renderer.tile_sprite_list.draw(pixelated=True)

        self.ui_camera.use()
        if self.game_state:
            ui_text = (
                f"Gold: {self.game_state.gold} | Base HP: {self.game_state.base_hp}"
            )
            arcade.draw_text(
                ui_text, 10, self.height - 25, arcade.color.WHITE_SMOKE, font_size=16
            )

    def on_update(self, delta_time: float):
        self._update_camera_position()

    def _update_camera_position(self):
        """Moves the camera based on which keys are currently held down."""
        cam_dx, cam_dy = 0, 0
        if self.up_pressed and not self.down_pressed:
            cam_dy = 1
        elif self.down_pressed and not self.up_pressed:
            cam_dy = -1
        if self.left_pressed and not self.right_pressed:
            cam_dx = -1
        elif self.right_pressed and not self.left_pressed:
            cam_dx = 1

        if cam_dx != 0 or cam_dy != 0:
            self.camera.position = (
                self.camera.position[0] + cam_dx * CAMERA_SPEED,
                self.camera.position[1] + cam_dy * CAMERA_SPEED,
            )
            self._clamp_camera()

    def on_mouse_drag(
        self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int
    ):
        """Handle mouse drag events for camera panning."""
        if buttons & arcade.MOUSE_BUTTON_MIDDLE:
            self.camera.position = (
                self.camera.position[0] - dx,
                self.camera.position[1] - dy,
            )
            self._clamp_camera()

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int):
        """Handle mouse scroll for zooming in and out by scaling the world."""
        # FIX #2: Correct mathematical formula for zooming to the cursor.
        old_scale = self.world_scale

        # Get the world coordinates under the mouse before scaling
        world_x = (self.camera.position[0] + x) / old_scale
        world_y = (self.camera.position[1] + y) / old_scale

        # Determine the new scale and clamp it
        self.world_scale += scroll_y * SCROLL_INCREMENT
        self.world_scale = max(MIN_SCALE, min(self.world_scale, MAX_SCALE))

        # Apply the new scale to the sprite list
        if self.sprite_renderer:
            self.sprite_renderer.tile_sprite_list.scale = self.world_scale

        # Calculate the new camera position to keep the world point under the mouse
        new_cam_x = (world_x * self.world_scale) - x
        new_cam_y = (world_y * self.world_scale) - y

        self.camera.position = (new_cam_x, new_cam_y)
        self._clamp_camera()

    def _clamp_camera(self):
        """Prevents the camera from scrolling past the edges of the scaled world."""
        scaled_world_width = self.world_width * self.world_scale
        scaled_world_height = self.world_height * self.world_scale

        max_x = max(0, scaled_world_width - self.width)
        max_y = max(0, scaled_world_height - self.height)

        clamped_x = max(0, min(self.camera.position[0], max_x))
        clamped_y = max(0, min(self.camera.position[1], max_y))

        self.camera.position = (clamped_x, clamped_y)

    def on_key_press(self, key: int, modifiers: int):
        if key in (arcade.key.UP, arcade.key.W):
            self.up_pressed = True
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down_pressed = True
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.left_pressed = True
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right_pressed = True
        elif key == arcade.key.ESCAPE:
            self.close()

    def on_key_release(self, key: int, modifiers: int):
        if key in (arcade.key.UP, arcade.key.W):
            self.up_pressed = False
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down_pressed = False
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.left_pressed = False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right_pressed = False

    def on_resize(self, width: int, height: int):
        """This is called when the user resizes the window."""
        super().on_resize(width, height)
        # Resize both cameras to match the new window dimensions
        self.camera.viewport_width = width
        self.camera.viewport_height = height
        self.ui_camera.viewport_width = width
        self.ui_camera.viewport_height = height
        self._clamp_camera()
