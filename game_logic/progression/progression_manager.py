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
        self,
        player_data_manager: PlayerDataManager,
        all_tower_configs: Dict[str, Any],
        global_upgrades_config: Dict[
            str, Any
        ],  # --- NEW: Accept global upgrades config ---
    ):
        """
        Initializes the ProgressionManager.

        Args:
            player_data_manager (PlayerDataManager): The manager for save file I/O.
            all_tower_configs (Dict[str, Any]): The full tower_types.json config.
            global_upgrades_config (Dict[str, Any]): The loaded global_upgrades.json config.
        """
        self.player_data_manager = player_data_manager
        self.all_tower_configs = all_tower_configs
        # --- REFACTORED: Load global upgrades from config instead of hardcoding (Issue #6) ---
        self.global_upgrades = global_upgrades_config

    def get_player_data(self) -> PlayerData:
        """Convenience method to get the current player data."""
        return self.player_data_manager.get_data()

    def get_unlockable_towers(self) -> List[Dict[str, Any]]:
        """
        Gets a list of all towers for the Workshop, including purchasable
        towers and towers the player already owns.
        """
        unlockable = []
        player_data = self.get_player_data()

        for tower_id, config in self.all_tower_configs.items():
            if not isinstance(config, dict):
                continue

            is_unlocked = tower_id in player_data.unlocked_towers
            has_unlock_cost = "unlock_cost" in config

            if has_unlock_cost or is_unlocked:
                unlockable.append(
                    {
                        "id": tower_id,
                        "name": config.get("name", "Unknown"),
                        "cost": config.get("unlock_cost", 0),
                        "unlocked": is_unlocked,
                        "description": config.get("description", ""),
                    }
                )

        return sorted(unlockable, key=lambda x: (x["unlocked"], x["cost"]))

    def purchase_tower(self, tower_id: str) -> bool:
        """
        Attempts to purchase and unlock a tower.
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
        Calculates the total effect of all purchased global upgrades by reading
        their definitions from the loaded configuration.
        """
        player_data = self.get_player_data()
        logger.info("Calculating global upgrade modifiers from purchased upgrades...")

        modifiers: Dict[str, Any] = {
            "game_state_mods": {"gold": 0, "base_hp": 0},
            "tower_stat_mods": {},
        }

        # --- REFACTORED: Data-driven modifier calculation (Issue #6) ---
        # This loop replaces the large, hardcoded if/elif block. It processes
        # any purchased upgrade by looking up its definition and applying its
        # effects, making the system entirely data-driven and easy to extend.
        for upgrade_id in player_data.purchased_upgrades:
            upgrade_data = self.global_upgrades.get(upgrade_id)
            if not upgrade_data or not isinstance(upgrade_data, dict):
                continue

            for effect in upgrade_data.get("effects", []):
                effect_type = effect.get("type")
                effect_value = effect.get("value")
                if not effect_type or not isinstance(effect_value, dict):
                    continue

                if effect_type == "modify_game_state":
                    stat = effect_value.get("stat")
                    amount = effect_value.get("amount", 0)
                    if stat in modifiers["game_state_mods"]:
                        modifiers["game_state_mods"][stat] += amount

                elif effect_type == "modify_tower_stat":
                    tower_id = effect_value.get("tower_id")
                    stat = effect_value.get("stat")
                    amount = effect_value.get("amount", 0)
                    if not tower_id or not stat:
                        continue

                    if tower_id not in modifiers["tower_stat_mods"]:
                        modifiers["tower_stat_mods"][tower_id] = {}

                    current_mod = modifiers["tower_stat_mods"][tower_id].get(stat, 0)
                    modifiers["tower_stat_mods"][tower_id][stat] = current_mod + amount

        logger.info(f"Global modifiers calculated: {modifiers}")
        return modifiers
