# main.py
import json
import logging
import sys
from pathlib import Path
from typing import Dict
import pygame

from rendering.game_window import Game
from game_logic.upgrades.upgrade_loader import load_all_upgrades
from game_logic.progression.player_data_manager import PlayerDataManager
from game_logic.progression.progression_manager import ProgressionManager
from rendering.text.font_manager import FontManager


# --- Constants ---
PROJECT_ROOT = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "configs"
ASSETS_PATH = PROJECT_ROOT / "assets"
SAVES_PATH = CONFIG_PATH / "saves"


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
    # --- FIX: Initialize Pygame and its font module at the very start ---
    # This ensures that all Pygame modules are ready before any other code
    # that might depend on them (like the FontManager) is executed.
    pygame.init()
    pygame.font.init()

    logger.info("--- Loading All Game Configurations ---")
    try:
        ui_theme = load_config(CONFIG_PATH / "ui" / "ui_theme.json")

        upgrade_root_dir = CONFIG_PATH / "upgrades"
        all_upgrade_defs = load_all_upgrades([upgrade_root_dir])

        all_configs: Dict[str, Dict] = {
            "game_settings": load_config(CONFIG_PATH / "gameplay/game_settings.json"),
            "level_styles": load_config(CONFIG_PATH / "levels/level_styles.json"),
            "enemy_types": load_config(
                CONFIG_PATH / "entities/enemies/enemy_types.json"
            ),
            "boss_types": load_config(CONFIG_PATH / "entities/enemies/boss_types.json"),
            "buffer_types": load_config(
                CONFIG_PATH / "entities/enemies/buffer_types.json"
            ),
            "tower_types": load_config(CONFIG_PATH / "entities/tower_types.json"),
            "targeting_ai": load_config(CONFIG_PATH / "targeting/targeting_ai.json"),
            "formations": load_config(CONFIG_PATH / "ai/formations.json"),
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

    logger.info("--- Initializing Font Manager ---")
    font_manager = FontManager(ui_theme.get("fonts", {}))

    logger.info("--- Initializing Progression Systems ---")
    player_data_manager = PlayerDataManager(SAVES_PATH / "player_data.json")
    progression_manager = ProgressionManager(
        player_data_manager=player_data_manager,
        all_tower_configs=all_configs["tower_types"],
    )

    logger.info("--- Initializing Game ---")
    try:
        game = Game(
            all_configs=all_configs,
            assets_path=ASSETS_PATH,
            progression_manager=progression_manager,
            ui_theme=ui_theme,
            font_manager=font_manager,
        )
        game.run()
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)

    logger.info("--- Game Closed ---")
    sys.exit()


if __name__ == "__main__":
    main()
