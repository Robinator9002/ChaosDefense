# main.py
import arcade
import json
import logging
from pathlib import Path

# Now we import our own classes from their respective files
from rendering.game_window import GameWindow

# --- Constants ---
PROJECT_ROOT = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "config"

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(filename: str) -> dict:
    """Loads a JSON configuration file from the config directory."""
    file_path = CONFIG_PATH / filename
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
            logger.info(f"Successfully loaded configuration: {filename}")
            return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {file_path}")
        raise


def main():
    """Main function to set up and run the game."""
    logger.info("--- Loading Game Configurations ---")
    try:
        game_settings = load_config("game_settings.json")
        # We can load the other configs here later if main needs them,
        # or have other modules load them as needed.
    except (FileNotFoundError, json.JSONDecodeError):
        logger.critical(
            "A required configuration file was missing or corrupt. Cannot start."
        )
        return  # Exit the program if essential configs fail

    screen_width = game_settings.get("screen_width", 1280)
    screen_height = game_settings.get("screen_height", 720)
    screen_title = game_settings.get("screen_title", "ChaosDefense - Error")

    logger.info("--- Initializing Game Window ---")
    window = GameWindow(screen_width, screen_height, screen_title)
    window.setup()

    arcade.run()
    logger.info("--- Game Closed ---")


if __name__ == "__main__":
    main()
