# game_logic/game_state.py
from dataclasses import dataclass, field
import logging

# We can get the logger from the root to keep logging consistent.
logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """
    A simple data class to hold the core state of the game.
    This object will be passed around to different systems.
    """

    gold: int = 100
    base_hp: int = 20
    current_wave_number: int = 0
    game_over: bool = False

    # This will eventually hold our generated level grid
    level_grid = None

    flags: dict = field(default_factory=dict)

    def __post_init__(self):
        """Called after the object is created."""
        logger.info(f"GameState initialized: HP={self.base_hp}, Gold={self.gold}")

    def end_game(self):
        """Sets the game over flag."""
        if not self.game_over:
            self.game_over = True
            logger.warning("GAME OVER condition triggered.")

    def add_gold(self, amount: int):
        """Adds gold to the player's total."""
        if amount > 0:
            self.gold += amount

    def spend_gold(self, amount: int) -> bool:
        """
        Spends gold if the player has enough.
        Returns True on success, False otherwise.
        """
        if self.gold >= amount:
            self.gold -= amount
            return True
        logger.info(f"Not enough gold. Have: {self.gold}, Need: {amount}")
        return False
