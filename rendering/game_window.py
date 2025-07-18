# rendering/game_window.py
import arcade
import logging

# Import the GameState class from its new location
from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class GameWindow(arcade.Window):
    """
    The main window for the ChaosDefense game.
    It handles drawing and user input, delegating game logic updates.
    """

    def __init__(self, width: int, height: int, title: str):
        super().__init__(width, height, title, resizable=True)

        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)

        # This will be an instance of the GameState class
        self.game_state = None

        # This will be our new renderer for drawing the level
        self.sprite_renderer = None

        logger.info("GameWindow initialized.")

    def setup(self):
        """
        Set up game resources. This method will be called once when the game starts.
        """
        logger.info("GameWindow setup() called.")
        # Create the game state
        self.game_state = GameState()

        # --- This is where level generation will happen ---
        # self.game_state.level_grid = LevelGenerator.generate("Forest")
        # self.sprite_renderer = SpriteRenderer(self.game_state.level_grid)

        logger.info("Game setup is complete.")

    def on_draw(self):
        """
        Render the screen.
        """
        self.clear()

        # In the future, the renderer will draw the level here
        # self.sprite_renderer.draw()

        # For now, a simple placeholder text
        arcade.draw_text(
            "Level will be drawn here...",
            self.width / 2,
            self.height / 2,
            arcade.color.WHITE_SMOKE,
            font_size=30,
            anchor_x="center",
            anchor_y="center",
        )

        # Draw the UI on top
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
        if self.game_state and self.game_state.game_over:
            # Logic for when the game has ended
            pass

        # In the future: self.game_state.update(delta_time)
        pass

    def on_key_press(self, key: int, modifiers: int):
        """
        Called whenever a key is pressed.
        """
        if key == arcade.key.ESCAPE:
            logger.info("Escape key pressed. Closing window.")
            self.close()

    def on_resize(self, width: int, height: int):
        """
        This function is called when the user resizes the window.
        """
        super().on_resize(width, height)
        arcade.set_viewport(0, self.width, 0, self.height)
        logger.info(f"Window resized to: {width}x{height}")
