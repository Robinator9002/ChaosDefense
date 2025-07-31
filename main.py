# main.py
import json
import logging
import sys
from pathlib import Path
from typing import Dict

from rendering.game_window import Game
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
        # --- MODIFIED: Automated Upgrade Discovery ---
        # We now point our loader to the root 'upgrades' directory.
        # The loader's recursive search will automatically find all upgrade
        # files in any subdirectories (e.g., 'military', 'support'), making
        # the system plug-and-play for new tower categories.
        upgrade_root_dir = CONFIG_PATH / "upgrades"
        all_upgrade_defs = load_all_upgrades([upgrade_root_dir])

        all_configs: Dict[str, Dict] = {
            "game_settings": load_config(CONFIG_PATH / "gameplay/game_settings.json"),
            "level_styles": load_config(CONFIG_PATH / "levels/level_styles.json"),
            "enemy_types": load_config(
                CONFIG_PATH / "entities/enemies/enemy_types.json"
            ),
            "boss_types": load_config(CONFIG_PATH / "entities/enemies/boss_types.json"),
            "tower_types": load_config(CONFIG_PATH / "entities/tower_types.json"),
            # --- BUGFIX: Add the missing targeting_ai.json to the main config ---
            "targeting_ai": load_config(CONFIG_PATH / "targeting/targeting_ai.json"),
            # Use the dynamically loaded definitions from our loader.
            "upgrade_definitions": all_upgrade_defs,
            "difficulty_scaling": load_config(
                CONFIG_PATH / "scaling/difficulty_scaling.json"
            ),
            "wave_scaling": load_config(CONFIG_PATH / "scaling/wave_scaling.json"),
            "status_effects": load_config(CONFIG_PATH / "gameplay/status_effects.json"),
        }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.critical(
            f"A required configuration file was missing or corrupt. Error: {e}",
            exc_info=True,
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
