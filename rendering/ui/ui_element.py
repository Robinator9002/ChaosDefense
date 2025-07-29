# rendering/ui/ui_element.py
import pygame
from typing import Optional, Any

# --- MODIFIED: Import the new UIAction class ---
# By importing our structured action class, we can enforce a more robust
# and type-safe communication protocol between UI elements and the manager.
from .ui_action import UIAction

# Using Any for game_state to avoid circular dependencies
if "GameState" not in globals():
    from typing import Any as GameState


class UIElement:
    """
    A base class for all interactive UI components.

    Provides fundamental properties like position, size, a bounding
    rectangle for event handling, and basic drawing capabilities.
    """

    def __init__(self, rect: pygame.Rect):
        """
        Initializes a new UIElement.

        Args:
            rect (pygame.Rect): The rectangle defining the element's
                                position and dimensions on the screen.
        """
        self.rect = rect
        self.is_hovered = False

    def handle_event(
        self, event: pygame.event.Event, game_state: GameState
    ) -> Optional[UIAction]:  # --- MODIFIED: Return type is now UIAction ---
        """
        Processes a Pygame event and returns an action object if triggered.

        This base implementation handles hover detection. Subclasses should
        extend this to handle clicks and other interactions.

        Args:
            event (pygame.event.Event): The Pygame event to process.
            game_state (GameState): The current state of the game logic.

        Returns:
            An optional UIAction object representing a command to be
            processed by the UIManager. Returning None indicates that the
            event was not handled by this element.
        """
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)

        return None

    def update(self, dt: float, game_state: GameState):
        """
        Updates the element's state over time.

        This can be used for animations or state changes based on game logic.

        Args:
            dt (float): The time elapsed since the last frame.
            game_state (GameState): The current state of the game logic.
        """
        pass

    def draw(self, screen: pygame.Surface):
        """
        Draws the element to the screen.

        This method should be overridden by subclasses to provide a proper
        visual representation.

        Args:
            screen (pygame.Surface): The surface to draw the element on.
        """
        # The base implementation can draw a simple rectangle for debugging
        # and to visualize the element's boundaries.
        if self.is_hovered:
            pygame.draw.rect(screen, (180, 180, 180), self.rect, 1)
        else:
            pygame.draw.rect(screen, (100, 100, 100), self.rect, 1)
