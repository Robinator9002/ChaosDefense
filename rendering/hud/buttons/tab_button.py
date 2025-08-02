# rendering/hud/buttons/tab_button.py
import pygame
import logging
from typing import Dict, Any, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class TabButton(UIElement):
    """
    A UI element for a tower category tab.
    REFACTORED: Now fully theme-driven for consistent styling.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        category_name: str,
        is_active: bool,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes a new TabButton.

        Args:
            rect (pygame.Rect): The button's position and dimensions.
            category_name (str): The name of the category this tab represents.
            is_active (bool): Whether this tab is currently selected.
            ui_theme (Dict[str, Any]): The UI theme dictionary.
            font_manager (FontManager): The centralized font manager.
        """
        super().__init__(rect)
        self.category_name = category_name
        self.is_active = is_active

        # --- NEW: Load styles from theme ---
        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font = font_manager.get_font("body_medium")

    def handle_event(self, event: pygame.event.Event, game_state=None) -> bool:
        """
        Handles mouse clicks on the tab.
        """
        self.is_hovered = self.rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                logger.debug(f"Tab button '{self.category_name}' clicked.")
                return True
        return False

    def draw(self, screen: pygame.Surface):
        """Draws the tab button using theme-defined styles."""
        # Determine colors based on state
        if self.is_active:
            bg_color = self.colors.get("panel_secondary")
            text_color = self.colors.get("text_primary")
            border_color = self.colors.get("border_interactive_selected")
        elif self.is_hovered:
            bg_color = self.colors.get("panel_interactive_hover")
            text_color = self.colors.get("text_primary")
            border_color = self.colors.get("border_primary")
        else:
            bg_color = self.colors.get("panel_primary")
            text_color = self.colors.get("text_secondary")
            border_color = self.colors.get("border_primary")

        border_radius = self.layout.get("border_radius_small", 5)

        # Draw the button shape (a rectangle with only top corners rounded)
        pygame.draw.rect(
            screen,
            bg_color,
            self.rect,
            border_top_left_radius=border_radius,
            border_top_right_radius=border_radius,
        )
        pygame.draw.rect(
            screen,
            border_color,
            self.rect,
            self.layout.get("border_width_standard", 2),
            border_top_left_radius=border_radius,
            border_top_right_radius=border_radius,
        )

        # Render and position the text
        text_surf = self.font.render(self.category_name.capitalize(), True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
