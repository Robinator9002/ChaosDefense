# rendering/hud/panels/tower_info_panel.py
import pygame
import logging
from typing import Dict, Any, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from rendering.text.text_renderer import render_text_wrapped
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class TowerInfoPanel(UIElement):
    """
    A UI panel that displays detailed information about a tower type
    selected from the build menu, before it is placed.
    REFACTORED: Now fully theme-driven for consistent styling.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower_data: Dict[str, Any],
        targeting_ai_config: Dict[str, Any],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes the TowerInfoPanel.
        """
        super().__init__(rect)
        self.tower_data = tower_data
        self.targeting_ai_config = targeting_ai_config
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self._load_theme_assets()
        self._calculate_and_set_dynamic_height()

    def _load_theme_assets(self):
        """Loads all necessary fonts and style values from the theme config."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("body_large")
        self.font_header = self.font_manager.get_font("body_medium", bold=True)
        self.font_stat = self.font_manager.get_font("body_small")
        self.font_desc = self.font_manager.get_font("body_tiny")

    def _calculate_and_set_dynamic_height(self):
        """Calculates the total required height for all content and resizes the panel."""
        padding = self.layout.get("padding_medium", 15)
        spacing = self.layout.get("spacing_medium", 10)

        total_height = padding
        total_height += self.font_title.get_height() + spacing

        description = self.tower_data.get("description", "No description available.")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            description,
            self.font_desc,
            self.colors.get("text_secondary"),
            desc_max_width,
        )
        total_height += sum(s.get_height() for s in wrapped_desc) + spacing

        stats_to_display = self.tower_data.get("info_panel_stats", [])
        if stats_to_display:
            total_height += self.font_header.get_height() + (spacing / 2)
            total_height += len(stats_to_display) * 22  # Approx height per stat line
            total_height += spacing

        # This logic for available personas is now deprecated in favor of dynamic eligibility
        # but we'll leave the space calculation for now in case it's reused.
        personas = self.tower_data.get("ai_config", {}).get("available_personas", [])
        if personas:
            total_height += self.font_header.get_height() + (spacing / 2)
            total_height += len(personas) * self.font_desc.get_height()

        total_height += padding
        self.rect.height = total_height

    def draw(self, screen: pygame.Surface):
        """Draws the panel and all its components using theme styles."""
        bg_color = self.colors.get("panel_primary", (25, 30, 40))
        border_color = self.colors.get("border_primary", (80, 90, 100))
        border_radius = self.layout.get("border_radius_small", 5)
        border_width = self.layout.get("border_width_standard", 2)

        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)

        # --- FIX (Step 1.2): Convert list-based color to tuple before concatenation ---
        # The color is loaded from JSON as a list. We must cast it to a tuple
        # before we can add the alpha tuple `(230,)` to it. This resolves the TypeError.
        panel_surf.fill(tuple(bg_color) + (230,))
        screen.blit(panel_surf, self.rect.topleft)

        pygame.draw.rect(
            screen, border_color, self.rect, border_width, border_radius=border_radius
        )

        self._draw_text_content(screen)

    def _draw_text_content(self, screen: pygame.Surface):
        """Renders and positions all text within the panel using theme styles."""
        padding = self.layout.get("padding_medium", 15)
        spacing = self.layout.get("spacing_medium", 10)
        current_y = self.rect.y + padding

        # Title and Cost
        title_surf = self.font_title.render(
            self.tower_data.get("name", "N/A"), True, self.colors.get("text_primary")
        )
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        cost_text = f"{self.tower_data.get('cost', 0)}G"
        cost_surf = self.font_title.render(
            cost_text, True, self.colors.get("text_accent")
        )
        cost_rect = cost_surf.get_rect(topright=(self.rect.right - padding, current_y))
        screen.blit(cost_surf, cost_rect)
        current_y += title_surf.get_height() + spacing

        # Description
        description = self.tower_data.get("description", "")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            description,
            self.font_desc,
            self.colors.get("text_secondary"),
            desc_max_width,
        )
        for line_surf in wrapped_desc:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += line_surf.get_height()
        current_y += spacing

        # Statistics
        stats_to_display = self.tower_data.get("info_panel_stats", [])
        if stats_to_display:
            header_surf = self.font_header.render(
                "Statistics", True, self.colors.get("text_primary")
            )
            screen.blit(header_surf, (self.rect.x + padding, current_y))
            current_y += header_surf.get_height() + (spacing / 2)

            for stat_info in stats_to_display:
                label = stat_info.get("label", "N/A")
                value_path = stat_info.get("value_path")
                value = (
                    get_nested_value(self.tower_data, value_path)
                    if value_path
                    else "N/A"
                )
                if value is None:
                    continue
                value_str = format_stat_value(value, stat_info.get("format"))

                label_surf = self.font_stat.render(
                    f"{label}:", True, self.colors.get("text_secondary")
                )
                value_surf = self.font_stat.render(
                    value_str, True, self.colors.get("text_primary")
                )

                screen.blit(label_surf, (self.rect.x + padding, current_y))
                value_rect = value_surf.get_rect(
                    topright=(self.rect.right - padding, current_y)
                )
                screen.blit(value_surf, value_rect)
                current_y += 22
