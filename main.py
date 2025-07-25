# main.py
import json
import logging
import sys
from pathlib import Path

# Import the main Game class.
from rendering.game_window import Game

# --- Constants ---
PROJECT_ROOT = Path(__file__).parent
# Assume a 'config' directory exists at the project root.
CONFIG_PATH = PROJECT_ROOT / "config"
ASSETS_PATH = PROJECT_ROOT / "assets"

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
        level_styles = load_config("level_styles.json")
    except (FileNotFoundError, json.JSONDecodeError):
        logger.critical(
            "A required configuration file was missing or corrupt. Cannot start."
        )
        return  # Exit the program if essential configs fail

    logger.info("--- Initializing Game ---")
    try:
        game = Game(
            game_settings=game_settings,
            level_styles=level_styles,
            assets_path=ASSETS_PATH,
        )
        game.run()
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)

    logger.info("--- Game Closed ---")
    sys.exit()


if __name__ == "__main__":
    main()
