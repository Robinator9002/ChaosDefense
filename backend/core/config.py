# backend/core/config.py
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# --- Path Setup ---
# This is a crucial step to ensure that the backend application can find and
# import modules from the 'game_logic' directory. We add the project's root
# directory to Python's system path.
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# --- Project-Specific Imports ---
# Now that the path is set up, we can import the upgrade loader.
from game_logic.upgrades.upgrade_loader import load_all_upgrades

logger = logging.getLogger(__name__)


def _load_single_config(path: Path) -> dict:
    """
    Private helper to load a single JSON configuration file with robust error handling.
    """
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {path}")
        raise


def load_all_game_configs() -> Dict[str, Any]:
    """
    Loads all necessary game configurations from the disk and aggregates them
    into a single dictionary. This function is the single source of truth for
    all game data.
    """
    logger.info("--- Loading All Game Configurations for Backend ---")
    config_path = PROJECT_ROOT / "configs"
    tower_upgrade_dir = config_path / "upgrades" / "towers"

    try:
        all_configs = {
            "game_settings": _load_single_config(
                config_path / "gameplay/game_settings.json"
            ),
            "level_styles": _load_single_config(
                config_path / "levels/level_styles.json"
            ),
            "enemy_types": _load_single_config(
                config_path / "entities/enemies/enemy_types.json"
            ),
            "boss_types": _load_single_config(
                config_path / "entities/enemies/boss_types.json"
            ),
            "buffer_types": _load_single_config(
                config_path / "entities/enemies/buffer_types.json"
            ),
            "tower_types": _load_single_config(
                config_path / "entities/tower_types.json"
            ),
            "targeting_ai": _load_single_config(
                config_path / "targeting/targeting_ai.json"
            ),
            "formations": _load_single_config(config_path / "ai/formations.json"),
            "upgrade_definitions": load_all_upgrades([tower_upgrade_dir]),
            "difficulty_scaling": _load_single_config(
                config_path / "scaling/difficulty_scaling.json"
            ),
            "wave_scaling": _load_single_config(
                config_path / "scaling/wave_scaling.json"
            ),
            "status_effects": _load_single_config(
                config_path / "gameplay/status_effects.json"
            ),
            "global_upgrades": _load_single_config(
                config_path / "upgrades/global_upgrades.json"
            ),
        }
        logger.info("--- All configurations loaded successfully. ---")
        return all_configs
    except Exception as e:
        logger.critical(
            f"A fatal error occurred during configuration loading: {e}", exc_info=True
        )
        # In a real application, you might exit here or return a default config.
        # For now, we re-raise to halt execution on a critical error.
        raise
