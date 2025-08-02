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

    def apply_global_upgrades(self, game_manager: Any):
        """
        Applies the effects of purchased global upgrades to a new game instance.
        This method is called at the start of a new game.

        Args:
            game_manager (GameManager): The main game manager instance.
        """
        player_data = self.get_player_data()
        logger.info("Applying purchased global upgrades...")

        for upgrade_id in player_data.purchased_upgrades:
            if upgrade_id == "starting_gold_1":
                game_manager.game_state.gold += 50
            elif upgrade_id == "starting_gold_2":
                game_manager.game_state.gold += 100
            elif upgrade_id == "base_hp_1":
                game_manager.game_state.base_hp += 5
            # More complex upgrades can modify the base tower configs before towers are built
            elif upgrade_id == "turret_damage_1":
                if "turret" in game_manager.configs["tower_types"]:
                    game_manager.configs["tower_types"]["turret"]["attack"]["data"][
                        "damage"
                    ] += 2

        logger.info(
            f"Global upgrades applied. Starting Gold: {game_manager.game_state.gold}, Base HP: {game_manager.game_state.base_hp}"
        )
