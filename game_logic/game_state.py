# game_logic/game_state.py
from dataclasses import dataclass, field
import logging
import uuid
from typing import Optional, Any

# We can get the logger from the root to keep logging consistent.
logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """
    A data class holding the core state of the game, including player
    resources, progress, and current intent (selections).

    This object is passed around to different systems, providing a single,
    consistent source of truth for the game's status.
    """

    # --- Core Game Resources and Progress ---
    gold: int = 100
    base_hp: int = 20
    current_wave_number: int = 0
    game_over: bool = False

    # --- Player Intent and Selection State ---
    # Stores the ID of the tower type selected from the UI for building.
    # e.g., "turret"
    selected_tower_to_build: Optional[str] = None

    # Stores the unique ID of an entity (e.g., a placed tower) that the
    # player has selected on the map, typically to view stats or upgrades.
    selected_entity_id: Optional[uuid.UUID] = None

    # --- Level Data ---
    # This will hold the generated level grid object.
    level_grid: Optional[Any] = None  # Using Any to avoid circular import with Grid

    # --- Miscellaneous State ---
    # A general-purpose dictionary for flags or other dynamic state.
    flags: dict = field(default_factory=dict)

    def __post_init__(self):
        """Called after the dataclass is instantiated."""
        logger.info(f"GameState initialized: HP={self.base_hp}, Gold={self.gold}")

    def end_game(self):
        """Sets the game over flag, ensuring it only triggers once."""
        if not self.game_over:
            self.game_over = True
            logger.warning("GAME OVER condition triggered.")

    def add_gold(self, amount: int):
        """Adds a specified amount of gold to the player's total."""
        if amount > 0:
            self.gold += amount

    def spend_gold(self, amount: int) -> bool:
        """
        Spends gold if the player has enough.

        Returns:
            True if the transaction was successful, False otherwise.
        """
        if self.gold >= amount:
            self.gold -= amount
            return True
        logger.info(f"Not enough gold. Have: {self.gold}, Need: {amount}")
        return False

    def clear_selection(self):
        """Resets all player selections to their default state."""
        self.selected_tower_to_build = None
        self.selected_entity_id = None
        logger.debug("Player selections cleared.")
