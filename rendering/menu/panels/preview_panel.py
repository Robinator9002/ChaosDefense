# rendering/menu/panels/preview_panel.py
import pygame
import logging
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING, List

from rendering.common.ui.ui_element import UIElement
from rendering.text.text_renderer import render_text_wrapped
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class PreviewPanel(UIElement):
    """
    A reusable UI panel for displaying detailed information about a selected
    item. It is now fully theme-driven and can dynamically render a list of
    statistics in addition to a title, description, and action button.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes the PreviewPanel.

        Args:
            rect (pygame.Rect): The rectangle defining the panel's position and size.
            ui_theme (Dict[str, Any]): The UI theme dictionary.
            font_manager (FontManager): The centralized font manager.
        """
        super().__init__(rect)
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self.active_item_data: Optional[Dict[str, Any]] = None
        self.action_button: Optional[UIElement] = None
        self.action_callback: Optional[Callable] = None
        self.is_button_enabled = False

        # Pre-load fonts and styles from the theme
        self._load_theme_assets()

    def _load_theme_assets(self):
        """Loads all necessary fonts and style values from the theme config."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})

        self.font_title = self.font_manager.get_font("title_small")
        self.font_desc = self.font_manager.get_font("body_small")
        self.font_stat_header = self.font_manager.get_font("body_medium", bold=True)
        self.font_stat_label = self.font_manager.get_font("body_tiny")
        self.font_stat_value = self.font_manager.get_font("body_tiny", bold=True)
        self.font_button = self.font_manager.get_font("button_large")

    def set_item(
        self,
        item_data: Optional[Dict[str, Any]],
        button_text: str,
        button_action: Callable,
        is_button_enabled: bool = True,
    ):
        """
        Updates the panel to display information for a new item and resizes
        the panel dynamically based on the new content.
        """
        self.active_item_data = item_data
        self.action_callback = button_action
        self.is_button_enabled = is_button_enabled

        if item_data:
            self._calculate_dynamic_height()  # Recalculate height for new item
            button_width = self.rect.width * 0.8
            button_height = 50
            button_rect = pygame.Rect(
                self.rect.centerx - button_width / 2,
                self.rect.bottom - button_height - self.layout.get("padding_large", 20),
                button_width,
                button_height,
            )
            self.action_button = UIElement(button_rect)
            self.action_button.text = button_text
        else:
            self.action_button = None
            self.rect.height = 0  # Collapse panel if no item

    def _calculate_dynamic_height(self):
        """Calculates the panel's total height based on its content."""
        if not self.active_item_data:
            self.rect.height = 0
            return

        padding = self.layout.get("padding_large", 20)
        spacing = self.layout.get("spacing_medium", 10)
        current_y = padding

        # Title
        current_y += self.font_title.get_height() + spacing

        # Description
        desc = self.active_item_data.get("description", "")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            desc, self.font_desc, self.colors.get("text_secondary"), desc_max_width
        )
        current_y += sum(line.get_height() for line in wrapped_desc) + padding

        # Stats
        stats_to_display = self.active_item_data.get("info_panel_stats", [])
        if stats_to_display:
            current_y += self.font_stat_header.get_height() + spacing
            current_y += len(stats_to_display) * 22  # Approx height per stat line
            current_y += padding

        # Action Button
        current_y += 50 + padding  # Height of button + bottom padding

        self.rect.height = current_y

    def handle_event(self, event: pygame.event.Event):
        """Handles events for the action button."""
        if not self.action_button or not self.is_button_enabled:
            return

        self.action_button.is_hovered = self.action_button.rect.collidepoint(event.pos)
        if (
            self.action_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if self.action_callback:
                item_id = (
                    self.active_item_data.get("id") if self.active_item_data else None
                )
                if item_id:
                    self.action_callback(item_id)
                else:
                    logger.warning("PreviewPanel action called without an item ID.")
                    # Fallback for actions that don't need an ID
                    try:
                        self.action_callback()
                    except TypeError:
                        logger.error(
                            f"Action callback {self.action_callback} requires an ID but none was provided."
                        )

    def draw(self, screen: pygame.Surface):
        """Draws the panel and its contents using styles from the theme."""
        if not self.active_item_data:
            return

        # Draw panel background and border
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors.get("panel_primary", (25, 30, 40)) + (230,))
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(
            screen,
            self.colors.get("border_primary", (80, 90, 100)),
            self.rect,
            self.layout.get("border_width_standard", 2),
            border_radius=self.layout.get("border_radius_large", 8),
        )

        padding = self.layout.get("padding_large", 20)
        spacing = self.layout.get("spacing_medium", 10)
        current_y = self.rect.y + padding

        # Draw Title
        title_surf = self.font_title.render(
            self.active_item_data.get("name", "No Item Selected"),
            True,
            self.colors.get("text_primary", (240, 240, 240)),
        )
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        current_y += title_surf.get_height() + spacing

        # Draw Description
        desc = self.active_item_data.get("description", "")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            desc,
            self.font_desc,
            self.colors.get("text_secondary", (180, 180, 190)),
            desc_max_width,
        )
        for line_surf in wrapped_desc:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += line_surf.get_height()
        current_y += padding

        # --- NEW: Draw Stats Section ---
        stats_to_display = self.active_item_data.get("info_panel_stats", [])
        if stats_to_display:
            header_surf = self.font_stat_header.render(
                "Statistics", True, self.colors.get("text_primary")
            )
            screen.blit(header_surf, (self.rect.x + padding, current_y))
            current_y += header_surf.get_height() + spacing

            for stat_info in stats_to_display:
                label = stat_info.get("label", "N/A")
                value_path = stat_info.get("value_path")
                value = (
                    get_nested_value(self.active_item_data, value_path)
                    if value_path
                    else "N/A"
                )

                if value is None:
                    continue

                value_str = format_stat_value(value, stat_info.get("format"))
                label_surf = self.font_stat_label.render(
                    f"{label}:", True, self.colors.get("text_secondary")
                )
                value_surf = self.font_stat_value.render(
                    value_str, True, self.colors.get("text_primary")
                )

                screen.blit(label_surf, (self.rect.x + padding, current_y))
                value_rect = value_surf.get_rect(
                    topright=(self.rect.right - padding, current_y)
                )
                screen.blit(value_surf, value_rect)
                current_y += 22  # Custom spacing for stats

        # Draw Action Button
        if self.action_button:
            if not self.is_button_enabled:
                bg_color = self.colors.get("button_disabled_bg")
                text_color = self.colors.get("text_disabled")
            elif self.action_button.is_hovered:
                bg_color = self.colors.get("button_primary_hover")
                text_color = self.colors.get("text_primary")
            else:
                bg_color = self.colors.get("button_primary_bg")
                text_color = self.colors.get("text_primary")

            pygame.draw.rect(
                screen,
                bg_color,
                self.action_button.rect,
                border_radius=self.layout.get("border_radius_large", 8),
            )
            button_text_surf = self.font_button.render(
                self.action_button.text, True, text_color
            )
            button_text_rect = button_text_surf.get_rect(
                center=self.action_button.rect.center
            )
            screen.blit(button_text_surf, button_text_rect)
