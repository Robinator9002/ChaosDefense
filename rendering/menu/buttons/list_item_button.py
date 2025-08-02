# rendering/menu/buttons/list_item_button.py
import pygame
import logging
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class ListItemButton(UIElement):
    """
    A highly dynamic and reusable button for items in a scrollable list,
    such as levels or workshop unlocks. It handles its own complex drawing
    based on its state (locked, selected, hover) and passed-in data.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        item_data: Dict[str, Any],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.is_selected = False

        # --- Data Parsing ---
        self.title: str = item_data.get("title", "N/A")
        self.is_locked: bool = item_data.get("is_locked", False)
        self.can_afford: bool = item_data.get("can_afford", True)
        # Top-right corner text (e.g., cost or "UNLOCKED")
        self.status_text: Optional[str] = item_data.get("status_text")
        # List of (label, value) tuples for stats
        self.stats: List[Tuple[str, str]] = item_data.get("stats", [])

        self._load_theme_assets()

    def _load_theme_assets(self):
        """Loads all necessary fonts and style values from the theme config."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("body_medium_bold")
        self.font_status = self.font_manager.get_font("body_medium_bold")
        self.font_stat_label = self.font_manager.get_font("body_tiny")
        self.font_stat_value = self.font_manager.get_font("body_tiny_bold")
        self.font_locked = self.font_manager.get_font("title_small")

    def draw(self, screen: pygame.Surface):
        """Draws the button with complex styling based on its state."""
        border_radius = self.layout.get("border_radius_large", 8)
        border_width = self.layout.get("border_width_standard", 2)
        padding = self.layout.get("padding_medium", 15)

        # 1. Determine Colors and Styles based on State
        if self.is_locked:
            bg_color = self.colors.get("panel_primary")
            border_color = self.colors.get("border_primary")
            title_color = self.colors.get("text_disabled")
        else:
            title_color = self.colors.get("text_primary")
            if self.is_selected:
                bg_color = self.colors.get("panel_secondary")
                border_color = self.colors.get("border_accent")
                border_width = self.layout.get("border_width_selected", 3)
            elif self.is_hovered:
                bg_color = self.colors.get("panel_interactive_hover")
                border_color = self.colors.get("border_interactive_selected")
            else:
                bg_color = self.colors.get("panel_primary")
                border_color = self.colors.get("border_primary")

        # 2. Draw Background and Border
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)
        pygame.draw.rect(
            screen, border_color, self.rect, border_width, border_radius=border_radius
        )

        # 3. Draw Content
        # Title
        title_surf = self.font_title.render(self.title, True, title_color)
        screen.blit(title_surf, (self.rect.x + padding, self.rect.y + 10))

        # Status Text (top-right)
        if self.status_text:
            status_color = (
                self.colors.get("text_accent")
                if self.can_afford
                else self.colors.get("text_error")
            )
            if "UNLOCKED" in self.status_text:
                status_color = self.colors.get("text_success")

            status_surf = self.font_status.render(self.status_text, True, status_color)
            status_rect = status_surf.get_rect(
                topright=(self.rect.right - padding, self.rect.y + 12)
            )
            screen.blit(status_surf, status_rect)

        # Lock Icon (if locked)
        if self.is_locked:
            lock_surf = self.font_locked.render(
                "🔒", True, self.colors.get("text_disabled")
            )
            lock_rect = lock_surf.get_rect(
                centery=self.rect.centery, right=self.rect.right - padding
            )
            screen.blit(lock_surf, lock_rect)

        # Stats
        current_y = self.rect.y + 40
        for label, value in self.stats:
            label_surf = self.font_stat_label.render(
                f"{label}:", True, self.colors.get("text_secondary")
            )
            value_surf = self.font_stat_value.render(
                value, True, self.colors.get("text_primary")
            )

            # --- FIX: Label on the left, value right-aligned ---
            screen.blit(label_surf, (self.rect.x + padding, current_y))
            value_rect = value_surf.get_rect(
                topright=(self.rect.right - padding, current_y)
            )
            screen.blit(value_surf, value_rect)
            current_y += 18
