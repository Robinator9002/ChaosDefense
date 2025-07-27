# game_logic/entities/entity.py
import pygame
import uuid
import logging
from typing import TYPE_CHECKING

# This prevents circular imports, which can happen if other entity types
# need to know about the game state for their logic.
if TYPE_CHECKING:
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class Entity:
    """
    The base class for all game objects that exist on the map.

    This includes enemies, towers, projectiles, and even the player's base.
    It provides fundamental attributes like position, health, and a unique ID,
    as well as core methods for updating, drawing, and taking damage.

    Attributes:
        pos (pygame.Vector2): The precise pixel position of the entity's center.
        max_hp (int): The maximum health points of the entity.
        current_hp (int): The current health points.
        is_alive (bool): A flag indicating if the entity is active and has HP > 0.
        entity_id (uuid.UUID): A unique identifier for this specific entity instance.
        sprite (pygame.Surface): The visual representation of the entity.
        rect (pygame.Rect): The bounding box for drawing and simple collision.
    """

    def __init__(self, x: float, y: float, max_hp: int, sprite: pygame.Surface = None):
        """
        Initializes a new Entity.

        Args:
            x (float): The initial x-coordinate of the entity's center.
            y (float): The initial y-coordinate of the entity's center.
            max_hp (int): The maximum health of the entity.
            sprite (pygame.Surface, optional): The Pygame surface to use as a sprite.
                                               If None, a placeholder is created.
        """
        self.pos = pygame.Vector2(x, y)
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.is_alive = True
        self.entity_id = uuid.uuid4()

        if sprite:
            self.sprite = sprite
        else:
            # Create a default placeholder sprite if none is provided.
            self.sprite = pygame.Surface((32, 32))
            self.sprite.fill(
                (255, 0, 255)
            )  # Magenta is a classic "missing texture" color
            self.sprite.set_colorkey(
                (0, 0, 0)
            )  # Make black parts of the surface transparent

        self.rect = self.sprite.get_rect(center=self.pos)
        logger.debug(
            f"Entity {self.__class__.__name__} created with ID {self.entity_id} at {self.pos}"
        )

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates the entity's logic. This method is meant to be overridden by subclasses.

        Args:
            dt (float): The time elapsed since the last frame, in seconds.
            game_state (GameState): The current state of the game.
        """
        # Base entity has no logic to update, but subclasses will.
        # We can update the rect position here to ensure it's always in sync.
        self.rect.center = self.pos

    def draw(self, screen: pygame.Surface, camera_offset: pygame.Vector2, zoom: float):
        """
        Draws the entity on the screen, applying camera transformations.

        Args:
            screen (pygame.Surface): The main display surface.
            camera_offset (pygame.Vector2): The camera's offset.
            zoom (float): The current camera zoom level.
        """
        if not self.is_alive:
            return

        # Apply camera transformations to the entity's position
        scaled_pos = self.pos * zoom
        screen_pos = scaled_pos + camera_offset

        # Scale the sprite if needed
        if zoom != 1.0:
            new_size = (int(self.rect.width * zoom), int(self.rect.height * zoom))
            # Using transform.scale for performance; smoothscale is too slow for many entities.
            scaled_sprite = pygame.transform.scale(self.sprite, new_size)
            scaled_rect = scaled_sprite.get_rect(center=screen_pos)
            screen.blit(scaled_sprite, scaled_rect)
        else:
            # No zoom, draw directly
            self.rect.center = screen_pos
            screen.blit(self.sprite, self.rect)

    def take_damage(self, amount: int):
        """
        Reduces the entity's current HP by a given amount.
        Handles the entity's death if HP drops to 0 or below.

        Args:
            amount (int): The amount of damage to inflict.
        """
        if not self.is_alive:
            return

        self.current_hp -= amount
        if self.current_hp <= 0:
            self.current_hp = 0
            self.kill()

    def kill(self):
        """
        Marks the entity as no longer alive.
        This is the primary way to "destroy" an entity. The game's entity
        manager is responsible for cleaning up dead entities.
        """
        self.is_alive = False
        logger.info(f"Entity {self.entity_id} has been killed.")

    def get_distance_to(self, other_entity: "Entity") -> float:
        """
        Calculates the distance to another entity.

        Args:
            other_entity (Entity): The other entity to measure the distance to.

        Returns:
            float: The distance in pixels.
        """
        return self.pos.distance_to(other_entity.pos)
