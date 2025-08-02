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

    # --- MODIFIED: Logic updated to include already-unlocked base towers (Your Plan / Step 2.4) ---
    def get_unlockable_towers(self) -> List[Dict[str, Any]]:
        """
        Gets a list of all towers for the Workshop, including purchasable
        towers and towers the player already owns.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a tower.
        """
        unlockable = []
        player_data = self.get_player_data()

        for tower_id, config in self.all_tower_configs.items():
            if not isinstance(config, dict):
                continue

            is_unlocked = tower_id in player_data.unlocked_towers
            has_unlock_cost = "unlock_cost" in config

            # A tower should appear in the workshop if it's a purchasable unlock,
            # OR if it's a base tower that the player already has. This ensures
            # base towers without an `unlock_cost` are still displayed.
            if has_unlock_cost or is_unlocked:
                unlockable.append(
                    {
                        "id": tower_id,
                        "name": config.get("name", "Unknown"),
                        # Use unlock_cost if it exists; otherwise, it's a base tower
                        # with no cost to display in the Workshop.
                        "cost": config.get("unlock_cost", 0),
                        "unlocked": is_unlocked,
                        "description": config.get("description", ""),
                    }
                )

        # Sort to show locked towers first, then by their cost.
        return sorted(unlockable, key=lambda x: (x["unlocked"], x["cost"]))

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

    def get_global_upgrade_modifiers(self) -> Dict[str, Any]:
        """
        Calculates the total effect of all purchased global upgrades.
        """
        player_data = self.get_player_data()
        logger.info("Calculating global upgrade modifiers from purchased upgrades...")

        modifiers: Dict[str, Any] = {
            "game_state_mods": {"gold": 0, "base_hp": 0},
            "tower_stat_mods": {},
        }

        for upgrade_id in player_data.purchased_upgrades:
            if upgrade_id == "starting_gold_1":
                modifiers["game_state_mods"]["gold"] += 50
            elif upgrade_id == "starting_gold_2":
                modifiers["game_state_mods"]["gold"] += 100
            elif upgrade_id == "base_hp_1":
                modifiers["game_state_mods"]["base_hp"] += 5
            elif upgrade_id == "turret_damage_1":
                if "turret" not in modifiers["tower_stat_mods"]:
                    modifiers["tower_stat_mods"]["turret"] = {}
                current_mod = modifiers["tower_stat_mods"]["turret"].get("damage", 0)
                modifiers["tower_stat_mods"]["turret"]["damage"] = current_mod + 2

        logger.info(f"Global modifiers calculated: {modifiers}")
        return modifiers
