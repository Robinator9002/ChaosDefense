# rendering/ui/buttons/tab_button.py
import pygame
import logging
from typing import Optional

from ..ui_element import UIElement

# We don't need UIAction here, as this button's action is handled directly
# by the UIManager in a special way (changing the active tab).

logger = logging.getLogger(__name__)


class TabButton(UIElement):
    """
    A UI element representing a clickable tab for a tower category.
    Its appearance changes based on whether it is the currently active tab.
    """

    def __init__(self, rect: pygame.Rect, category_name: str, is_active: bool):
        """
        Initializes a new TabButton.

        Args:
            rect (pygame.Rect): The button's position and dimensions.
            category_name (str): The name of the category this tab represents.
            is_active (bool): Whether this tab is currently selected.
        """
        super().__init__(rect)
        self.category_name = category_name
        self.is_active = is_active

        # --- Font and Color Definitions ---
        self.font = pygame.font.SysFont("segoeui", 16, bold=True)
        self.colors = {
            "bg_inactive": (30, 40, 50),
            "bg_active": (60, 75, 90),
            "bg_hover": (45, 60, 75),
            "border_inactive": (80, 90, 100),
            "border_active": (150, 180, 200),
            "text_inactive": (180, 180, 190),
            "text_active": (240, 240, 250),
        }

    def handle_event(self, event: pygame.event.Event, game_state=None) -> bool:
        """
        Handles mouse clicks on the tab.

        Returns:
            True if the button was clicked, False otherwise. The UIManager
            will use this boolean to know when to switch the active category.
        """
        super().handle_event(event, game_state)  # Updates hover state

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                logger.debug(f"Tab button '{self.category_name}' clicked.")
                return True
        return False

    def draw(self, screen: pygame.Surface):
        """Draws the tab button to the screen with dynamic styling."""
        # Determine background color
        if self.is_active:
            bg_color = self.colors["bg_active"]
        elif self.is_hovered:
            bg_color = self.colors["bg_hover"]
        else:
            bg_color = self.colors["bg_inactive"]

        # Determine text and border color
        text_color = (
            self.colors["text_active"]
            if self.is_active
            else self.colors["text_inactive"]
        )
        border_color = (
            self.colors["border_active"]
            if self.is_active
            else self.colors["border_inactive"]
        )

        # Draw the button shape (a rectangle with only top corners rounded)
        pygame.draw.rect(
            screen,
            bg_color,
            self.rect,
            border_top_left_radius=5,
            border_top_right_radius=5,
        )
        pygame.draw.rect(
            screen,
            border_color,
            self.rect,
            2,
            border_top_left_radius=5,
            border_top_right_radius=5,
        )

        # Render and position the text
        text_surf = self.font.render(self.category_name.capitalize(), True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
