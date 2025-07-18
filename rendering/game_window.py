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

# Constants for camera movement
CAMERA_SPEED = 10


class GameWindow(arcade.Window):
    """
    The main window for the ChaosDefense game.
    It handles drawing, user input, and camera controls, delegating
    game logic updates.
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

        # --- Camera and World Dimensions ---
        self.tile_size = self.game_settings.get("tile_size", 32)
        self.grid_width = self.game_settings.get("grid_width", 50)
        self.grid_height = self.game_settings.get("grid_height", 50)

        self.world_width = self.grid_width * self.tile_size
        self.world_height = self.grid_height * self.tile_size

        self.camera = arcade.camera.Camera2D()
        self.camera.viewport_width = width
        self.camera.viewport_height = height

        # --- Keyboard State for Camera Movement ---
        self.up_pressed = False
        self.down_pressed = False
        self.left_pressed = False
        self.right_pressed = False

        logger.info("GameWindow initialized and ready for setup.")

    def setup(self):
        """
        Set up all game resources. This is where the world is born.
        """
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

        # --- Correctly position the camera after setup ---
        # We will center the camera on the world by default.
        self.center_camera_on_world()

        logger.info(
            "Game setup is complete. The world has been generated and camera positioned."
        )

    def center_camera_on_world(self):
        """Calculates the correct position to center the camera's view on the world."""
        # Calculate the center of the world
        world_center_x = self.world_width / 2
        world_center_y = self.world_height / 2

        # Calculate the camera's bottom-left position to achieve this centering
        camera_x = world_center_x - (self.camera.viewport_width / 2)
        camera_y = world_center_y - (self.camera.viewport_height / 2)

        self.camera.position = (camera_x, camera_y)
        self._clamp_camera()

    def on_draw(self):
        """
        Render the screen.
        """
        self.clear()
        self.camera.use()

        if self.sprite_renderer:
            self.sprite_renderer.draw()

        arcade.get_window().ctx.projection_2d = 0, self.width, 0, self.height

        if self.game_state:
            ui_text = (
                f"Gold: {self.game_state.gold} | "
                f"Base HP: {self.game_state.base_hp} | "
                f"Wave: {self.game_state.current_wave_number}"
            )
            arcade.draw_text(
                ui_text, 10, self.height - 25, arcade.color.WHITE_SMOKE, font_size=16
            )

    def on_update(self, delta_time: float):
        """
        Game logic and movement calculations.
        """
        self._update_camera_position()

        if self.game_state and self.game_state.game_over:
            pass

    def _update_camera_position(self):
        """Moves the camera based on which keys are currently held down."""
        cam_dx = 0
        cam_dy = 0
        if self.up_pressed and not self.down_pressed:
            cam_dy = 1
        elif self.down_pressed and not self.up_pressed:
            cam_dy = -1
        if self.left_pressed and not self.right_pressed:
            cam_dx = -1
        elif self.right_pressed and not self.left_pressed:
            cam_dx = 1

        if cam_dx != 0 or cam_dy != 0:
            new_pos = (
                self.camera.position[0] + cam_dx * CAMERA_SPEED,
                self.camera.position[1] + cam_dy * CAMERA_SPEED,
            )
            self.camera.position = new_pos
            self._clamp_camera()

    def on_mouse_drag(
        self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int
    ):
        """
        Handle mouse drag events for camera panning.
        """
        if buttons & arcade.MOUSE_BUTTON_MIDDLE:
            self.camera.position = (
                self.camera.position[0] - dx,
                self.camera.position[1] - dy,
            )
            self._clamp_camera()

    def _clamp_camera(self):
        """
        Prevents the camera from scrolling past the edges of the world.
        """
        clamped_x = max(
            0,
            min(self.camera.position[0], self.world_width - self.camera.viewport_width),
        )
        clamped_y = max(
            0,
            min(
                self.camera.position[1], self.world_height - self.camera.viewport_height
            ),
        )
        self.camera.position = (clamped_x, clamped_y)

    def on_key_press(self, key: int, modifiers: int):
        """
        Called whenever a key is pressed.
        """
        if key in (arcade.key.UP, arcade.key.W):
            self.up_pressed = True
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down_pressed = True
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.left_pressed = True
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right_pressed = True
        elif key == arcade.key.ESCAPE:
            logger.info("Escape key pressed. Closing window.")
            self.close()

    def on_key_release(self, key: int, modifiers: int):
        """Called when the user releases a key."""
        if key in (arcade.key.UP, arcade.key.W):
            self.up_pressed = False
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down_pressed = False
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.left_pressed = False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right_pressed = False

    def on_resize(self, width: int, height: int):
        """
        This function is called when the user resizes the window.
        """
        super().on_resize(width, height)
        self.camera.viewport_width = width
        self.camera.viewport_height = height
        self._clamp_camera()
        logger.info(f"Window resized to: {width}x{height}")
