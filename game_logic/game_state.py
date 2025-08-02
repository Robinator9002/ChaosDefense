# game_logic/game_state.py
from dataclasses import dataclass, field
import logging
import uuid
from typing import Optional, Any

# Using TYPE_CHECKING to avoid circular import with Grid, which is good practice.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .level_generation.grid import Grid

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """
    A data class holding the core state of the game, including player
    resources, progress, and current player intent (what is selected).

    This object acts as a centralized "source of truth" that is passed to
    various game systems. This design prevents state conflicts and makes the
    flow of data explicit and easy to trace.
    """

    # --- Core Game Resources and Progress ---
    gold: int = 100
    base_hp: int = 20
    current_wave_number: int = 0
    game_over: bool = False
    # --- NEW: Victory flag ---
    # This flag is set to True when the player successfully clears all waves.
    victory: bool = False

    # --- Player Intent and Selection State ---
    selected_tower_to_build: Optional[str] = None
    selected_entity_id: Optional[uuid.UUID] = None

    # --- Level Data ---
    level_grid: Optional["Grid"] = None

    # --- Miscellaneous State ---
    flags: dict = field(default_factory=dict)

    def __post_init__(self):
        """Called by the dataclass constructor after the instance is created."""
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
        """
        Resets all player selections to their default state. This is important
        to ensure the player isn't trying to both build a new tower and inspect
        an existing one at the same time.
        """
        self.selected_tower_to_build = None
        self.selected_entity_id = None
        logger.debug("Player selections cleared.")
