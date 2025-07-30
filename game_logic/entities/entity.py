# game_logic/entities/entity.py
import pygame
import uuid
import logging
from typing import TYPE_CHECKING, List

# --- NEW: Import the EffectHandler component and StatusEffect for type hinting ---
from ..effects.effect_handler import EffectHandler
from ..effects.status_effect import StatusEffect

if TYPE_CHECKING:
    from ..game_state import GameState

logger = logging.getLogger(__name__)


class Entity:
    """
    The base class for all game objects that exist on the map.

    REFACTORED: This class now owns an EffectHandler component, making it the
    universal foundation for the buff and debuff system. Any class that
    inherits from Entity automatically gains the ability to have status
    effects applied to it.
    """

    def __init__(self, x: float, y: float, max_hp: int, sprite: pygame.Surface = None):
        """
        Initializes a new Entity.
        """
        self.pos = pygame.Vector2(x, y)
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.is_alive = True
        self.entity_id = uuid.uuid4()

        # --- NEW: Every entity now owns an EffectHandler ---
        # This component manages all status effect logic for this entity.
        self.effect_handler = EffectHandler(self)

        if sprite:
            self.sprite = sprite
        else:
            self.sprite = pygame.Surface((32, 32))
            self.sprite.fill((255, 0, 255))
            self.sprite.set_colorkey((0, 0, 0))

        self.rect = self.sprite.get_rect(center=self.pos)
        logger.debug(
            f"Entity {self.__class__.__name__} created with ID {self.entity_id} at {self.pos}"
        )

    def update(
        self,
        dt: float,
        game_state: "GameState",
        all_enemies: List["Entity"] = [],
        all_towers: List["Entity"] = [],
    ):
        """
        Updates the entity's logic, now including its status effects.
        The signature is expanded to allow subclasses to have battlefield awareness.
        """
        # --- NEW: Delegate effect updates to the handler ---
        # The handler will tick down durations, apply DoTs, and recalculate stats.
        self.effect_handler.update(dt)

        self.rect.center = self.pos

    def draw(self, screen: pygame.Surface, camera_offset: pygame.Vector2, zoom: float):
        """
        Draws the entity on the screen, applying camera transformations.
        """
        if not self.is_alive:
            return

        scaled_pos = self.pos * zoom
        screen_pos = scaled_pos + camera_offset

        if zoom != 1.0:
            new_size = (int(self.rect.width * zoom), int(self.rect.height * zoom))
            scaled_sprite = pygame.transform.scale(self.sprite, new_size)
            scaled_rect = scaled_sprite.get_rect(center=screen_pos)
            screen.blit(scaled_sprite, scaled_rect)
        else:
            self.rect.center = screen_pos
            screen.blit(self.sprite, self.rect)

    # --- NEW: Public API for applying effects ---
    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to this entity by passing it to the handler.
        """
        self.effect_handler.apply_status_effect(new_effect)

    def take_damage(self, amount: int, ignores_armor: bool = False):
        """
        Reduces the entity's current HP by a given amount.
        The signature is updated to be compatible with the EffectHandler's
        damage-over-time calls.
        """
        if not self.is_alive:
            return

        # The base entity has no armor, so the 'ignores_armor' flag is not used here,
        # but it is required for compatibility with child classes like Enemy.
        self.current_hp -= amount
        if self.current_hp <= 0:
            self.current_hp = 0
            self.kill()

    def kill(self):
        """
        Marks the entity as no longer alive.
        """
        self.is_alive = False
        logger.info(f"Entity {self.entity_id} has been killed.")

    def get_distance_to(self, other_entity: "Entity") -> float:
        """
        Calculates the distance to another entity.
        """
        return self.pos.distance_to(other_entity.pos)
