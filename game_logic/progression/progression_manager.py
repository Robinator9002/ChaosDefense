# game_logic/progression/progression_manager.py
import logging
from typing import Dict, Any, List, Optional

from .player_data_manager import PlayerDataManager, PlayerData

logger = logging.getLogger(__name__)


class ProgressionManager:
    """
    Manages the player's meta-progression, including unlocking towers and
    purchasing permanent global upgrades. This class acts as the interface
    between the UI and the player's save data.
    """

    def __init__(
        self, player_data_manager: PlayerDataManager, all_tower_configs: Dict[str, Any]
    ):
        """
        Initializes the ProgressionManager.

        Args:
            player_data_manager (PlayerDataManager): The manager for save file I/O.
            all_tower_configs (Dict[str, Any]): The full tower_types.json config.
        """
        self.player_data_manager = player_data_manager
        self.all_tower_configs = all_tower_configs

        # Define the global upgrades available for purchase.
        # In a larger game, this could also be loaded from a JSON file.
        self.global_upgrades: Dict[str, Dict[str, Any]] = {
            "starting_gold_1": {
                "name": "Bonus Gold I",
                "cost": 100,
                "description": "Start with +50 gold.",
            },
            "starting_gold_2": {
                "name": "Bonus Gold II",
                "cost": 250,
                "description": "Start with +100 gold.",
            },
            "base_hp_1": {
                "name": "Reinforced Base I",
                "cost": 150,
                "description": "Start with +5 base HP.",
            },
            "turret_damage_1": {
                "name": "Turret Specialization",
                "cost": 200,
                "description": "All Turrets deal +2 damage.",
            },
        }

    def get_player_data(self) -> PlayerData:
        """Convenience method to get the current player data."""
        return self.player_data_manager.get_data()

    def get_unlockable_towers(self) -> List[Dict[str, Any]]:
        """
        Gets a list of all towers that can be unlocked, along with their
        status and cost.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a tower.
        """
        unlockable = []
        player_data = self.get_player_data()

        for tower_id, config in self.all_tower_configs.items():
            # --- BUG FIX: Ensure the config value is a dictionary ---
            # This gracefully skips any top-level keys in the JSON that are not
            # tower definitions, such as comments (e.g., "//": "comment text").
            if not isinstance(config, dict):
                continue

            # Towers are considered unlockable if they have a 'unlock_cost' defined.
            if "unlock_cost" in config:
                unlockable.append(
                    {
                        "id": tower_id,
                        "name": config.get("name", "Unknown"),
                        "cost": config.get("unlock_cost", 9999),
                        "unlocked": tower_id in player_data.unlocked_towers,
                        "description": config.get("description", ""),
                    }
                )

        # Sort to show locked towers first
        return sorted(unlockable, key=lambda x: x["unlocked"])

    def purchase_tower(self, tower_id: str) -> bool:
        """
        Attempts to purchase and unlock a tower.

        Args:
            tower_id (str): The ID of the tower to unlock.

        Returns:
            bool: True if the purchase was successful, False otherwise.
        """
        player_data = self.get_player_data()
        tower_info = self.all_tower_configs.get(tower_id)

        if not tower_info or "unlock_cost" not in tower_info:
            logger.warning(f"Attempted to purchase invalid tower: {tower_id}")
            return False

        cost = tower_info["unlock_cost"]
        if (
            player_data.meta_currency >= cost
            and tower_id not in player_data.unlocked_towers
        ):
            player_data.meta_currency -= cost
            player_data.unlocked_towers.add(tower_id)
            self.player_data_manager.save_data(player_data)
            logger.info(f"Player unlocked tower: {tower_id}")
            return True

        logger.info(
            f"Failed to unlock tower {tower_id}. Not enough currency or already unlocked."
        )
        return False

    # --- MODIFIED: Replaced `apply_global_upgrades` with a method that returns modifiers ---
    # This is the first step in fixing the mutable config state bug (Issue #12).
    # This method no longer modifies any game state directly. Instead, it calculates
    # the effects of all purchased global upgrades and returns them in a structured
    # dictionary. The GameManager will then be responsible for applying these modifiers
    # to new game instances, ensuring the original configs are never touched.
    def get_global_upgrade_modifiers(self) -> Dict[str, Any]:
        """
        Calculates the total effect of all purchased global upgrades.

        This method is called at the start of a new game to get a summary
        of modifications to apply, without directly changing any game state.

        Returns:
            Dict[str, Any]: A dictionary of modifiers to be applied by the
                            GameManager. e.g.,
                            {
                                'game_state_mods': {'gold': 50, 'base_hp': 5},
                                'tower_stat_mods': {'turret': {'damage': 2}}
                            }
        """
        player_data = self.get_player_data()
        logger.info("Calculating global upgrade modifiers from purchased upgrades...")

        # Initialize a structure to hold the calculated modifiers.
        modifiers: Dict[str, Any] = {
            "game_state_mods": {"gold": 0, "base_hp": 0},
            "tower_stat_mods": {},
        }

        # Iterate through all upgrades the player has purchased.
        for upgrade_id in player_data.purchased_upgrades:
            if upgrade_id == "starting_gold_1":
                modifiers["game_state_mods"]["gold"] += 50
            elif upgrade_id == "starting_gold_2":
                modifiers["game_state_mods"]["gold"] += 100
            elif upgrade_id == "base_hp_1":
                modifiers["game_state_mods"]["base_hp"] += 5
            elif upgrade_id == "turret_damage_1":
                # For tower-specific mods, ensure the tower's key exists.
                if "turret" not in modifiers["tower_stat_mods"]:
                    modifiers["tower_stat_mods"]["turret"] = {}
                # Add to the existing modifier value, or initialize it.
                current_mod = modifiers["tower_stat_mods"]["turret"].get("damage", 0)
                modifiers["tower_stat_mods"]["turret"]["damage"] = current_mod + 2

        logger.info(f"Global modifiers calculated: {modifiers}")
        return modifiers
