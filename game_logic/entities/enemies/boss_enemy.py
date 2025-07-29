# game_logic/entities/enemies/boss_enemy.py
import pygame
import logging
from typing import List, Tuple, Dict, Any

# Import the parent class from the sibling module 'enemy.py'.
from .enemy import Enemy

logger = logging.getLogger(__name__)


class BossEnemy(Enemy):
    """
    Represents a unique and powerful Boss enemy.

    This class inherits from the standard Enemy class but is initialized with
    data from the boss_types.json configuration. It serves as a distinct entity
    type, allowing for the future implementation of unique boss-specific
    mechanics, such as special attacks, phase changes, or unique visual cues,
    without altering the behavior of regular enemies.
    """

    def __init__(
        self,
        boss_type_data: Dict[str, Any],
        path: List[Tuple[int, int]],
        tile_size: int,
    ):
        """
        Initializes a new BossEnemy.

        Args:
            boss_type_data (Dict[str, Any]): The full data dictionary for this
                                           specific boss from boss_types.json.
            path (List[Tuple[int, int]]): The grid coordinate path for the boss
                                          to follow.
            tile_size (int): The size of each tile in pixels.
        """
        # Boss stats are absolute and defined directly in their configuration.
        # We pass level=1 and difficulty_modifier=1.0 to the parent constructor
        # to prevent any unwanted scaling that applies to regular enemies.
        # The boss_type_data dictionary has the same structure as enemy_type_data,
        # so it can be passed directly to the parent initializer.
        super().__init__(
            enemy_type_data=boss_type_data,
            level=1,
            path=path,
            tile_size=tile_size,
            difficulty_modifier=1.0,
        )

        self.is_boss = True  # A simple flag to identify this entity as a boss.
        logger.info(f"A fearsome Boss has been spawned: {self.name} ({self.entity_id})")
