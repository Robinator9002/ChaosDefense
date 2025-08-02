# game_logic/progression/player_data_manager.py
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Set

logger = logging.getLogger(__name__)


# Define the structure of the player's save data using a dataclass.
# This provides a clear, type-safe "schema" for the save file.
@dataclass
class PlayerData:
    """
    A data class that holds all persistent player progression data.
    """

    meta_currency: int = 0
    unlocked_towers: Set[str] = field(default_factory=lambda: {"turret", "freezer"})
    purchased_upgrades: Set[str] = field(default_factory=set)
    highest_wave_reached: int = 0
    # Add any other stats to track here, e.g., total_enemies_defeated, etc.


class PlayerDataManager:
    """
    Manages the loading from and saving to the player's persistent data file.
    This class handles all file I/O operations for player progression.
    """

    def __init__(self, save_path: Path):
        """
        Initializes the PlayerDataManager.

        Args:
            save_path (Path): The full path to the player_data.json save file.
        """
        self.save_path = save_path
        self.data: PlayerData = self._load_or_create_data()

    def _load_or_create_data(self) -> PlayerData:
        """
        Loads player data from the save file. If the file doesn't exist or is
        corrupt, it creates a new default save file.

        Returns:
            PlayerData: An instance of the PlayerData class.
        """
        if self.save_path.exists() and self.save_path.is_file():
            try:
                with open(self.save_path, "r") as f:
                    data = json.load(f)
                    # Convert lists from JSON back to sets for efficient lookups
                    data["unlocked_towers"] = set(data.get("unlocked_towers", []))
                    data["purchased_upgrades"] = set(data.get("purchased_upgrades", []))

                    logger.info(
                        f"Player data loaded successfully from {self.save_path}"
                    )
                    return PlayerData(**data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(
                    f"Failed to load or parse player data from {self.save_path}: {e}. "
                    "Creating a new default save file."
                )
                # If loading fails, fall through to create a new file

        # If we reach here, either the file didn't exist or it was corrupt.
        return self._create_default_data()

    def _create_default_data(self) -> PlayerData:
        """
        Creates a new PlayerData object with default values and saves it to disk.

        Returns:
            PlayerData: A new instance of PlayerData with default starting values.
        """
        logger.warning(
            f"No valid save file found. Creating new player data at {self.save_path}"
        )
        default_data = PlayerData()
        self.save_data(default_data)
        return default_data

    def save_data(self, player_data: PlayerData):
        """
        Saves the provided PlayerData object to the JSON file.

        Args:
            player_data (PlayerData): The data object to save.
        """
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a serializable version of the data
        save_dict = {
            "meta_currency": player_data.meta_currency,
            "unlocked_towers": list(
                player_data.unlocked_towers
            ),  # Convert sets to lists for JSON
            "purchased_upgrades": list(player_data.purchased_upgrades),
            "highest_wave_reached": player_data.highest_wave_reached,
        }

        try:
            with open(self.save_path, "w") as f:
                json.dump(save_dict, f, indent=2)
            logger.info(f"Player data saved successfully to {self.save_path}")
        except IOError as e:
            logger.critical(
                f"CRITICAL: Could not write player data to {self.save_path}: {e}"
            )

    def get_data(self) -> PlayerData:
        """
        Provides access to the currently loaded player data.

        Returns:
            PlayerData: The active PlayerData object.
        """
        return self.data
