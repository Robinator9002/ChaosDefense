# game_logic/entities/enemies/boss_enemy.py
import pygame
import logging
from typing import List, Tuple, Dict, Any

# Import the parent class from the sibling module 'enemy.py'.
from .enemy import Enemy

logger = logging.getLogger(__name__)


class BossEnemy(Enemy):
    """
    Represents a unique and powerful Boss enemy that can now scale its stats
    based on its spawn level and the game's difficulty modifier.

    This class inherits from the standard Enemy class but is initialized with
    data from the boss_types.json configuration. By accepting level and
    difficulty, it can now function as both a fixed-difficulty scripted
    encounter and a scaling late-game random threat.
    """

    # --- REFACTORED: The constructor now accepts scaling parameters ---
    # This is the key change that enables the entire boss scaling system.
    # Instead of hardcoding level=1, we now pass these values through to the
    # parent Enemy's constructor, allowing its stats to be calculated dynamically.
    def __init__(
        self,
        boss_type_data: Dict[str, Any],
        path: List[Tuple[int, int]],
        tile_size: int,
        level: int,
        difficulty_modifier: float,
    ):
        """
        Initializes a new, scalable BossEnemy.

        Args:
            boss_type_data (Dict[str, Any]): The data for this boss from config.
            path (List[Tuple[int, int]]): The grid path for the boss to follow.
            tile_size (int): The size of each tile in pixels.
            level (int): The level of this boss instance, used for scaling stats.
            difficulty_modifier (float): The game's stat modifier.
        """
        # The boss_type_data dictionary has the same structure as enemy_type_data,
        # so it can be passed directly to the parent initializer along with the
        # new scaling parameters.
        super().__init__(
            enemy_type_data=boss_type_data,
            level=level,
            path=path,
            tile_size=tile_size,
            difficulty_modifier=difficulty_modifier,
        )

        self.is_boss = True  # A simple flag to identify this entity as a boss.
        logger.info(
            f"A fearsome Boss has been spawned: {self.name} (Level {self.level}, ID: {self.entity_id})"
        )
