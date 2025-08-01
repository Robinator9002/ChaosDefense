# game_logic/entities/entity.py
import pygame
import uuid
import logging
from typing import TYPE_CHECKING, List, Dict

from ..effects.effect_handler import EffectHandler
from ..effects.status_effect import StatusEffect

if TYPE_CHECKING:
    from ..game_state import GameState
    from ..game_ai.targeting.targeting_manager import TargetingManager


logger = logging.getLogger(__name__)


class Entity:
    """
    The base class for all game objects that exist on the map.

    REFACTORED: Now includes a sprite caching system to prevent expensive
    on-the-fly scaling operations every frame, improving rendering performance
    when the camera is zoomed.
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

        if sprite:
            self.sprite = sprite
        else:
            # Create a default placeholder sprite if none is provided
            self.sprite = pygame.Surface((32, 32))
            self.sprite.fill((255, 0, 255))
            self.sprite.set_colorkey((0, 0, 0))

        self.rect = self.sprite.get_rect(center=self.pos)

        # --- NEW: Sprite cache for rendering optimization ---
        # The key will be the zoom level (float), the value will be the pre-scaled sprite surface.
        self._sprite_cache: Dict[float, pygame.Surface] = {}

        # The EffectHandler must be initialized *after* all stats on the subclass
        # have been set, so it can take an accurate snapshot.
        self.effect_handler = EffectHandler(self)

        self.auras: List[dict] = []
        self.status_effects_config: dict = {}

        logger.debug(
            f"Entity {self.__class__.__name__} created with ID {self.entity_id} at {self.pos}"
        )

    def update(
        self, dt: float, game_state: "GameState", targeting_manager: "TargetingManager"
    ):
        """
        Updates the entity's logic, including effects and aura broadcasting.
        """
        self.effect_handler.update(dt)
        self._broadcast_auras(targeting_manager)
        self.rect.center = self.pos

    def _broadcast_auras(self, targeting_manager: "TargetingManager"):
        """
        Finds nearby allies and applies this entity's aura effects to them.
        """
        if not self.auras:
            return

        for aura_data in self.auras:
            aura_range = aura_data.get("range", 0)
            target_type = aura_data.get("target_type")
            effects_to_apply = aura_data.get("effects", {})

            if not all([aura_range > 0, target_type, effects_to_apply]):
                continue

            allies_in_range = []
            if target_type == "TOWER":
                allies_in_range = targeting_manager.get_nearby_towers(
                    self.pos, aura_range
                )
            elif target_type == "ENEMY":
                allies_in_range = targeting_manager.get_nearby_enemies(
                    self.pos, aura_range
                )

            for ally in allies_in_range:
                if ally is self:
                    continue

                for effect_id, params in effects_to_apply.items():
                    if effect_id in self.status_effects_config:
                        effect_def = self.status_effects_config[effect_id]
                        effect = StatusEffect(
                            effect_id=effect_id,
                            effect_data=effect_def,
                            duration=params.get("duration", 1.0),
                            potency=params.get("potency", 1.0),
                            source_entity_id=self.entity_id,
                        )
                        ally.apply_status_effect(effect)

    def draw(self, screen: pygame.Surface, camera_offset: pygame.Vector2, zoom: float):
        """
        Draws the entity on the screen, applying camera transformations and
        using a cache for scaled sprites to optimize performance.
        """
        if not self.is_alive:
            return

        screen_pos = (self.pos * zoom) + camera_offset

        if zoom == 1.0:
            # If no zoom, draw directly with no scaling.
            self.rect.center = screen_pos
            screen.blit(self.sprite, self.rect)
        else:
            # --- OPTIMIZED: Use the sprite cache ---
            # Check if a pre-scaled sprite for this zoom level already exists.
            if zoom not in self._sprite_cache:
                # If not, create it once and store it in the cache.
                new_size = (int(self.rect.width * zoom), int(self.rect.height * zoom))
                # Use scale for performance; smoothscale is too slow for many entities.
                self._sprite_cache[zoom] = pygame.transform.scale(self.sprite, new_size)

            # Retrieve the pre-scaled sprite from the cache.
            scaled_sprite = self._sprite_cache[zoom]
            scaled_rect = scaled_sprite.get_rect(center=screen_pos)
            screen.blit(scaled_sprite, scaled_rect)

    def apply_status_effect(self, new_effect: "StatusEffect"):
        """
        Applies a new status effect to this entity by passing it to the handler.
        """
        self.effect_handler.apply_status_effect(new_effect)

    def take_damage(self, amount: int, ignores_armor: bool = False):
        """
        Reduces the entity's current HP by a given amount.
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
        """
        self.is_alive = False
        # Clear the cache to free up memory when the entity is no longer needed.
        self._sprite_cache.clear()
        logger.debug(f"Entity {self.entity_id} has been killed.")

    def get_distance_to(self, other_entity: "Entity") -> float:
        """
        Calculates the distance to another entity.
        """
        return self.pos.distance_to(other_entity.pos)
