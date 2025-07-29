# game_logic/upgrades/upgrade_loader.py
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def load_all_upgrades(upgrade_dirs: List[Path]) -> Dict[str, Any]:
    """
    Scans specified directories for tower upgrade JSON files, loads them,
    and merges them into a single comprehensive dictionary.

    This function is the cornerstone of the modular upgrade definition system.
    It allows upgrade paths to be defined in separate files, which are then
    dynamically discovered and loaded at runtime. This is highly extensible,
    as adding new towers with new upgrades only requires adding a new JSON file
    to one of the scanned directories.

    Args:
        upgrade_dirs (List[Path]): A list of Path objects, each pointing to a
                                   directory containing upgrade definition files.
                                   The loader will search all of these directories.

    Returns:
        Dict[str, Any]: A dictionary containing all loaded upgrade definitions,
                        keyed by the tower type (derived from the filename).
                        Returns an empty dictionary if no files are found or an
                        error occurs.
    """
    all_upgrade_definitions = {}
    logger.info(f"Scanning for upgrade definitions in: {upgrade_dirs}")

    for directory in upgrade_dirs:
        if not directory.is_dir():
            logger.warning(f"Upgrade directory not found, skipping: {directory}")
            continue

        # Using rglob('*.json') to find all .json files recursively. This
        # automatically supports future subdirectory structures like
        # 'soldiers/' or 'supporters/' without any code changes.
        for file_path in directory.rglob("*.json"):
            tower_type_id = file_path.stem  # e.g., "turret" from "turret.json"

            if tower_type_id in all_upgrade_definitions:
                logger.warning(
                    f"Duplicate upgrade definition found for '{tower_type_id}'. "
                    f"Overwriting previous definition with content from {file_path}."
                )

            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    all_upgrade_definitions[tower_type_id] = data
                    logger.debug(
                        f"Successfully loaded and merged upgrade file: {file_path.name}"
                    )
            except FileNotFoundError:
                logger.error(f"File not found during loading: {file_path}")
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from file: {file_path}")
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while loading {file_path}: {e}"
                )

    logger.info(
        f"Finished loading. Found definitions for {len(all_upgrade_definitions)} tower types."
    )
    return all_upgrade_definitions
