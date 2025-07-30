# game_logic/entities/enemies/boss_enemy.py
import pygame
import logging
from typing import List, Tuple, Dict, Any

from .enemy import Enemy

logger = logging.getLogger(__name__)


class BossEnemy(Enemy):
    """
    Represents a unique and powerful Boss enemy.
    """

    def __init__(
        self,
        boss_type_data: Dict[str, Any],
        path: List[Tuple[int, int]],
        tile_size: int,
        level: int,
        difficulty_modifier: float,
        status_effects_config: Dict[str, Any],  # --- NEW: Accept the config ---
    ):
        """
        Initializes a new, scalable BossEnemy.
        """
        # Pass all parameters, including the new config, to the parent initializer.
        super().__init__(
            enemy_type_data=boss_type_data,
            level=level,
            path=path,
            tile_size=tile_size,
            difficulty_modifier=difficulty_modifier,
            status_effects_config=status_effects_config,  # --- NEW: Pass it down ---
        )

        self.is_boss = True
        logger.info(
            f"A fearsome Boss has been spawned: {self.name} (Level {self.level}, ID: {self.entity_id})"
        )
