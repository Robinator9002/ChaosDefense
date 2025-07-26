# rendering/game_window.py
from __future__ import annotations
import arcade
import logging
from pathlib import Path

# Correctly import only the necessary classes from arcade.
from arcade.camera import Camera2D
from arcade.math import Vec2

# Project-specific imports for core components.
# This structure maintains a clean separation of concerns.
from game_logic.game_state import GameState
from level_generation.grid import Grid
from level_generation.generator import LevelGenerator
from rendering.sprite_renderer import SpriteRenderer

logger = logging.getLogger(__name__)

# --- Control Constants ---
SCROLL_SPEED = 1.0
MIN_ZOOM = 0.3
MAX_ZOOM = 2.5
ZOOM_INCREMENT = 0.1


class GameWindow(arcade.Window):
    """
    The main window for the game. This class serves as the central hub for
    rendering, handling user input, and orchestrating the primary game components.
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
        """
        Initializes the window and prepares the game's subsystems.

        Args:
            width (int): The width of the window.
            height (int): The height of the window.
            title (str): The title of the window.
            game_settings (dict): Loaded configuration from game_settings.json.
            level_styles (dict): Loaded configuration from level_styles.json.
            assets_path (Path): The path to the 'assets' directory.
        """
        super().__init__(width, height, title, resizable=True)

        # Store configurations and paths for later use.
        self.game_settings = game_settings
        self.level_styles = level_styles
        self.assets_path = assets_path

        # Initialize core game components. These will be populated in the setup() method.
        self.game_state: GameState | None = None
        self.grid: Grid | None = None
        self.sprite_renderer: SpriteRenderer | None = None

        # --- Camera Setup ---
        # A camera for the game world (map, towers, enemies). This is moved and zoomed.
        self.scene_camera = Camera2D()
        # A static camera for the user interface (HUD). This remains stationary.
        self.gui_camera = Camera2D()

        # Set the camera viewports immediately after creation.
        # The .viewport property setter correctly handles the (left, bottom, width, height) tuple.
        self.scene_camera.viewport = (0, 0, width, height)
        self.gui_camera.viewport = (0, 0, width, height)

        # --- Input Control State ---
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        # Stores the camera's position at the start of a pan operation.
        self.camera_start_pos: Vec2 = Vec2(0, 0)

    def setup(self):
        """
        Sets up the game. Called once at the beginning to create and initialize
        all necessary game objects.
        """
        logger.info("--- Starting Game Setup ---")

        # 1. Initialize the game state.
        self.game_state = GameState(gold=150, base_hp=20)

        # 2. Create the logical grid for the map.
        grid_width = self.game_settings.get("grid_width", 40)
        grid_height = self.game_settings.get("grid_height", 22)
        self.grid = Grid(grid_width, grid_height)

        # 3. Procedurally generate the level layout.
        # The LevelGenerator modifies the Grid object in-place.
        LevelGenerator.generate(self.grid)
        self.game_state.level_grid = self.grid

        # 4. Select the level style and set the background color.
        # The style is hardcoded to "Forest" for now but could be made dynamic.
        current_style = self.level_styles.get("Forest", {})
        style_definitions = current_style.get("tile_definitions", {})
        bg_color = current_style.get("background_color", (0, 0, 0))
        self.background_color = bg_color

        # 5. Create the SpriteRenderer to turn the logical grid into visible sprites.
        tile_size = self.game_settings.get("tile_size", 32)
        self.sprite_renderer = SpriteRenderer(
            grid=self.grid,
            tile_size=tile_size,
            style_definitions=style_definitions,
            assets_path=self.assets_path,
        )

        # Initially center the camera on the middle of the map.
        map_center_x = self.grid.width * tile_size / 2
        map_center_y = self.grid.height * tile_size / 2
        self.center_camera_on_point(map_center_x, map_center_y)

        logger.info("--- Game Setup Complete ---")

    def on_draw(self):
        """
        The main drawing routine. Called continuously by Arcade.
        """
        self.clear()

        # --- Draw Game World ---
        # Activate the scene camera. All subsequent drawing commands will be
        # transformed (panned, zoomed) by this camera.
        self.scene_camera.use()
        if self.sprite_renderer:
            self.sprite_renderer.draw()
        # Future entities like towers, enemies, and projectiles will be drawn here.

        # --- Draw GUI / HUD ---
        # Activate the GUI camera. This camera is static.
        self.gui_camera.use()
        self.draw_gui()

    def draw_gui(self):
        """Draws all elements of the user interface."""
        if not self.game_state:
            return

        # Draw a semi-transparent box as a background for the text to ensure readability.
        arcade.draw_rectangle_filled(
            center_x=120,
            center_y=self.height - 40,
            width=220,
            height=70,
            color=(0, 0, 0, 150),  # Black with 150/255 opacity
        )

        # Fetch the latest values from the GameState and display them.
        gold_text = f"Gold: {self.game_state.gold}"
        hp_text = f"Base HP: {self.game_state.base_hp}"
        wave_text = f"Wave: {self.game_state.current_wave_number}"

        arcade.draw_text(gold_text, 15, self.height - 30, arcade.color.GOLD, 16)
        arcade.draw_text(hp_text, 15, self.height - 55, arcade.color.RED, 16)
        arcade.draw_text(wave_text, 15, self.height - 80, arcade.color.CYAN, 16)

    def center_camera_on_point(self, x: float, y: float):
        """Centers the scene_camera on a specific point in the game world."""
        # move_to() sets the bottom-left corner of the camera's view.
        # To center, we subtract half of the viewport size from the target point.
        pos_x = x - self.scene_camera.viewport_width / 2
        pos_y = y - self.scene_camera.viewport_height / 2
        self.scene_camera.move_to(Vec2(pos_x, pos_y))

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """Called when a mouse button is pressed."""
        # Middle mouse button is used for panning the map.
        if button == arcade.MOUSE_BUTTON_MIDDLE:
            self.is_panning = True
            self.pan_start_x = x
            self.pan_start_y = y
            self.camera_start_pos = self.scene_camera.position

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        """Called when a mouse button is released."""
        if button == arcade.MOUSE_BUTTON_MIDDLE:
            self.is_panning = False

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        """Called when the mouse is moved."""
        if self.is_panning:
            # Calculate the mouse's displacement since the pan started.
            delta_x = x - self.pan_start_x
            delta_y = y - self.pan_start_y

            # The displacement must be scaled by the zoom factor for a natural feel.
            # The camera moves in the opposite direction of the mouse drag.
            cam_x = self.camera_start_pos.x - delta_x / self.scene_camera.zoom
            cam_y = self.camera_start_pos.y - delta_y / self.scene_camera.zoom

            self.scene_camera.move_to(Vec2(cam_x, cam_y))

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int):
        """Called when the mouse wheel is scrolled, used for zooming."""
        # Calculate the new zoom factor.
        zoom_amount = 1 + (scroll_y * ZOOM_INCREMENT)
        new_zoom = self.scene_camera.zoom * zoom_amount

        # Clamp the zoom to the defined min/max values.
        self.scene_camera.zoom = max(MIN_ZOOM, min(new_zoom, MAX_ZOOM))

    def on_update(self, delta_time: float):
        """
        Called for every frame. Game logic, such as moving enemies or tower
        actions, will be handled here.
        """
        pass

    def on_resize(self, width: int, height: int):
        """Called when the window is resized."""
        super().on_resize(width, height)
        # The viewport property setter correctly handles a tuple.
        self.scene_camera.viewport = (0, 0, width, height)
        self.gui_camera.viewport = (0, 0, width, height)
        logger.info(f"Window resized to: {width}x{height}")
