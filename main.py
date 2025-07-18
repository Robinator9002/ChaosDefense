# =================================================================================
# ChaosDefense/main.py
# =================================================================================
import arcade
import json
import logging
from pathlib import Path

# Because we are consolidating files, we need to adjust imports.
# In a real multi-file project, this would be:
# from rendering.game_window import GameWindow
# from game_logic.game_state import GameState
# For now, the classes are defined in this same file below.

# --- Constants ---
# Using pathlib for robust path handling. In a real scenario, you'd create
# these directories. For this single-file setup, we assume they exist conceptually.
PROJECT_ROOT = Path(__file__).parent if "__file__" in locals() else Path.cwd()
CONFIG_PATH = PROJECT_ROOT / "config"
ASSETS_PATH = PROJECT_ROOT / "assets"

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# NOTE: In this consolidated file, we can't truly load from external JSON.
# The `load_config` function is a placeholder for the real project structure.
# We will define the configs directly in the `main` function for now.


def load_config_placeholder(config_name: str, configs: dict) -> dict:
    """A placeholder to simulate loading from our JSON block."""
    if config_name in configs:
        logger.info(f"Successfully loaded configuration: {config_name}")
        return configs[config_name]
    else:
        logger.error(f"Configuration not found: {config_name}")
        raise KeyError(f"Config '{config_name}' not found in provided configurations.")


# =================================================================================
# ChaosDefense/game_logic/game_state.py
# =================================================================================
from dataclasses import dataclass, field


@dataclass
class GameState:
    """
    A simple data class to hold the core state of the game.
    This object will be passed around to different systems.
    """

    gold: int = 100
    base_hp: int = 20
    current_wave_number: int = 0
    game_over: bool = False

    flags: dict = field(default_factory=dict)

    def __post_init__(self):
        """Called after the object is created."""
        logger.info(f"GameState initialized: HP={self.base_hp}, Gold={self.gold}")

    def end_game(self):
        """Sets the game over flag."""
        if not self.game_over:
            self.game_over = True
            logger.warning("GAME OVER condition triggered.")

    def add_gold(self, amount: int):
        """Adds gold to the player's total."""
        if amount > 0:
            self.gold += amount

    def spend_gold(self, amount: int) -> bool:
        """
        Spends gold if the player has enough.
        Returns True on success, False otherwise.
        """
        if self.gold >= amount:
            self.gold -= amount
            return True
        logger.info(f"Not enough gold. Have: {self.gold}, Need: {amount}")
        return False


# =================================================================================
# ChaosDefense/rendering/game_window.py
# =================================================================================
# Note: arcade is already imported at the top of the file.


class GameWindow(arcade.Window):
    """
    The main window for the ChaosDefense game.
    It handles drawing and user input, delegating game logic updates.
    """

    def __init__(self, width: int, height: int, title: str):
        super().__init__(width, height, title, resizable=True)

        arcade.set_background_color(arcade.color.DARK_SLATE_GRAY)

        # This will be an instance of the GameState class defined above.
        self.game_state = None
        logger.info("GameWindow initialized.")

    def setup(self):
        """
        Set up game resources. This method will be called once when the game starts.
        """
        logger.info("GameWindow setup() called.")
        self.game_state = GameState()

    def on_draw(self):
        """
        Render the screen.
        """
        self.clear()

        arcade.draw_text(
            "ChaosDefense - Phase 1 Complete",
            self.width / 2,
            self.height / 2,
            arcade.color.WHITE_SMOKE,
            font_size=30,
            anchor_x="center",
            anchor_y="center",
        )

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
        logger.info(f"Key pressed: {arcade.key.reverse_lookup(key)}")
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


# =================================================================================
# Main Execution Block
# =================================================================================
def main():
    """Main function to set up and run the game."""

    # In this consolidated setup, we define the configs as a dictionary.
    # In the real project, the `load_config` function would read these from
    # the actual JSON files.
    all_configs = {
        "game_settings.json": {
            "screen_width": 1280,
            "screen_height": 720,
            "screen_title": "ChaosDefense",
        },
        "enemy_types.json": {},
        "tower_types.json": {},
        "upgrade_definitions.json": {},
        "level_styles.json": {},
    }

    logger.info("--- Loading Game Configurations (Placeholder) ---")
    game_settings = load_config_placeholder("game_settings.json", all_configs)

    screen_width = game_settings.get("screen_width", 1280)
    screen_height = game_settings.get("screen_height", 720)
    screen_title = game_settings.get("screen_title", "ChaosDefense - Init")

    logger.info("--- Initializing Game Window ---")
    window = GameWindow(screen_width, screen_height, screen_title)
    window.setup()

    arcade.run()
    logger.info("--- Game Closed ---")


if __name__ == "__main__":
    main()

# =================================================================================
# Empty __init__.py files (for package structure reference)
# =================================================================================
# In a real file system, the following empty files would exist:
# - ChaosDefense/game_ai/__init__.py
# - ChaosDefense/game_logic/__init__.py
# - ChaosDefense/game_logic/entities/__init__.py
# - ChaosDefense/game_logic/pathfinding/__init__.py
# - ChaosDefense/level_generation/__init__.py
# - ChaosDefense/rendering/__init__.py
