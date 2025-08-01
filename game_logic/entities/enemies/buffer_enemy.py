# game_logic/entities/enemies/buffer_enemy.py
import logging
from typing import List, Tuple, Dict, Any

from .enemy import Enemy

# Get a logger instance for this module.
logger = logging.getLogger(__name__)


class BufferEnemy(Enemy):
    """
    Represents a specialized support-type enemy that applies buffs to nearby
    allies through auras.

    This class inherits nearly all of its functionality from the base Enemy
    and Entity classes. Its primary purpose is to serve as a distinct type
    for the game's logic to identify. The actual aura broadcasting is handled
    by the `_broadcast_auras` method in the base Entity class, which reads
    the 'auras' data loaded from this enemy's configuration file.
    """

    def __init__(
        self,
        enemy_type_data: Dict[str, Any],
        level: int,
        path: List[Tuple[int, int]],
        tile_size: int,
        difficulty_modifier: float,
        status_effects_config: Dict[str, Any],
    ):
        """
        Initializes a new BufferEnemy.

        This constructor simply passes all arguments to the parent Enemy class
        constructor, which handles the setup of all stats, movement, and the
        loading of aura data.
        """
        # Call the parent class's constructor with all the provided parameters.
        # This ensures that the BufferEnemy is set up exactly like a standard
        # Enemy, including health, speed, pathing, and importantly, the
        # processing of the 'auras' key from its data definition.
        super().__init__(
            enemy_type_data=enemy_type_data,
            level=level,
            path=path,
            tile_size=tile_size,
            difficulty_modifier=difficulty_modifier,
            status_effects_config=status_effects_config,
        )

        logger.debug(
            f"Created Buffer Enemy: {self.name} (Level {self.level}, ID: {self.entity_id})"
        )
