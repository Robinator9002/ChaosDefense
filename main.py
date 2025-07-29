# main.py
import json
import logging
import sys
from pathlib import Path
from typing import Dict

from rendering.game_window import Game

# --- MODIFIED: Import the new upgrade loader function ---
# We now import our specialized function for loading the modular upgrade files.
from game_logic.upgrades.upgrade_loader import load_all_upgrades

# --- Constants ---
PROJECT_ROOT = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "configs"
ASSETS_PATH = PROJECT_ROOT / "assets"

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    """Loads a single JSON configuration file."""
    try:
        with open(path, "r") as f:
            config = json.load(f)
            logger.info(f"Successfully loaded configuration: {path.name}")
            return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {path}")
        raise


def main():
    """Main function to set up and run the game."""
    logger.info("--- Loading All Game Configurations ---")
    try:
        # --- MODIFIED: Use the new upgrade loader ---
        # 1. Define the directory (or directories) where upgrade files are located.
        #    This list is easily expandable for future tower categories.
        upgrade_dirs = [CONFIG_PATH / "upgrades"]

        # 2. Call our new loader to scan the directories and build the complete
        #    upgrade definitions dictionary.
        all_upgrade_defs = load_all_upgrades(upgrade_dirs)

        # 3. Assemble the final `all_configs` dictionary.
        all_configs: Dict[str, Dict] = {
            "game_settings": load_config(CONFIG_PATH / "gameplay/game_settings.json"),
            "level_styles": load_config(CONFIG_PATH / "levels/level_styles.json"),
            "enemy_types": load_config(
                CONFIG_PATH / "entities/enemies/enemy_types.json"
            ),
            "boss_types": load_config(CONFIG_PATH / "entities/enemies/boss_types.json"),
            "tower_types": load_config(CONFIG_PATH / "entities/tower_types.json"),
            # The old, single file load is replaced with our fully assembled dictionary.
            "upgrade_definitions": all_upgrade_defs,
            "difficulty_scaling": load_config(
                CONFIG_PATH / "scaling/difficulty_scaling.json"
            ),
            "wave_scaling": load_config(CONFIG_PATH / "scaling/wave_scaling.json"),
            "status_effects": load_config(CONFIG_PATH / "gameplay/status_effects.json"),
        }
    except (FileNotFoundError, json.JSONDecodeError):
        logger.critical(
            "A required configuration file was missing or corrupt. Cannot start."
        )
        return

    logger.info("--- Initializing Game ---")
    try:
        game = Game(
            all_configs=all_configs,
            assets_path=ASSETS_PATH,
        )
        game.run()
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)

    logger.info("--- Game Closed ---")
    sys.exit()


if __name__ == "__main__":
    main()
