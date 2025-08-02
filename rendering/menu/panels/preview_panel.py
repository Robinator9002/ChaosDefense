# rendering/menu/panels/preview_panel.py
import pygame
import logging
from typing import Dict, Any, Optional, Callable

from ...common.ui.ui_element import UIElement
from ...common.text.text_renderer import render_text_wrapped

logger = logging.getLogger(__name__)


class PreviewPanel(UIElement):
    """
    A reusable UI panel for displaying detailed information about a selected
    item, such as a level or a tower blueprint. It includes a title, a
    description, and an action button.
    """

    def __init__(self, rect: pygame.Rect):
        """
        Initializes the PreviewPanel.

        Args:
            rect (pygame.Rect): The rectangle defining the panel's position and size.
        """
        super().__init__(rect)
        self.active_item_data: Optional[Dict[str, Any]] = None
        self.action_button: Optional[UIElement] = None
        self.action_callback: Optional[Callable] = None

        self._setup_fonts_and_colors()

    def _setup_fonts_and_colors(self):
        """Initializes font and color constants for drawing."""
        self.font_title = pygame.font.SysFont("segoeui", 28, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 16)
        self.font_button = pygame.font.SysFont("segoeui", 24, bold=True)
        self.colors = {
            "bg": (25, 30, 40, 230),
            "border": (80, 90, 100),
            "title": (240, 240, 240),
            "desc": (180, 180, 190),
            "button_bg_default": (40, 80, 50),
            "button_bg_hover": (60, 110, 75),
            "button_bg_disabled": (40, 45, 50),
            "button_text": (220, 240, 220),
            "button_text_disabled": (100, 100, 110),
        }

    def set_item(
        self,
        item_data: Optional[Dict[str, Any]],
        button_text: str,
        button_action: Callable,
        is_button_enabled: bool = True,
    ):
        """
        Updates the panel to display information for a new item.

        Args:
            item_data (Optional[Dict[str, Any]]): A dictionary containing the
                'name' and 'description' of the item to display. If None,
                the panel will be cleared.
            button_text (str): The text to display on the action button.
            button_action (Callable): The function to call when the button is clicked.
            is_button_enabled (bool): Whether the action button should be clickable.
        """
        self.active_item_data = item_data
        self.action_callback = button_action

        if item_data:
            button_width = self.rect.width * 0.8
            button_height = 50
            button_rect = pygame.Rect(
                self.rect.centerx - button_width / 2,
                self.rect.bottom - button_height - 30,
                button_width,
                button_height,
            )
            self.action_button = UIElement(button_rect)
            self.action_button.text = button_text
            self.action_button.is_enabled = is_button_enabled
        else:
            self.action_button = None

    def handle_event(self, event: pygame.event.Event):
        """Handles events for the action button."""
        if not self.action_button or not self.action_button.is_enabled:
            return

        self.action_button.handle_event(event, game_state=None)
        if (
            self.action_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if self.action_callback:
                # Pass the item's ID to the callback if it exists
                item_id = (
                    self.active_item_data.get("id") if self.active_item_data else None
                )
                if item_id:
                    self.action_callback(item_id)
                else:
                    self.action_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the panel and its contents."""
        # Draw panel background and border
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors["bg"])
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=8)

        if not self.active_item_data:
            return  # Draw nothing further if no item is selected

        padding = 20
        current_y = self.rect.y + padding

        # Draw Title
        title_surf = self.font_title.render(
            self.active_item_data.get("name", ""), True, self.colors["title"]
        )
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        current_y += title_surf.get_height() + 15

        # Draw Description
        desc = self.active_item_data.get("description", "")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            desc, self.font_desc, self.colors["desc"], desc_max_width
        )
        for line_surf in wrapped_desc:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += line_surf.get_height()

        # Draw Action Button
        if self.action_button:
            if not self.action_button.is_enabled:
                bg_color = self.colors["button_bg_disabled"]
                text_color = self.colors["button_text_disabled"]
            elif self.action_button.is_hovered:
                bg_color = self.colors["button_bg_hover"]
                text_color = self.colors["button_text"]
            else:
                bg_color = self.colors["button_bg_default"]
                text_color = self.colors["button_text"]

            pygame.draw.rect(screen, bg_color, self.action_button.rect, border_radius=8)
            button_text_surf = self.font_button.render(
                self.action_button.text, True, text_color
            )
            button_text_rect = button_text_surf.get_rect(
                center=self.action_button.rect.center
            )
            screen.blit(button_text_surf, button_text_rect)
