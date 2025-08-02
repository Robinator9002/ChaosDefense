# rendering/hud/panels/tower_info_panel.py
import pygame
import logging
from typing import Dict, Any, TYPE_CHECKING, List, Optional

from rendering.common.ui.ui_element import UIElement
from rendering.text.text_renderer import render_text_wrapped
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from rendering.text.font_manager import FontManager
    from rendering.common.tooltips import TooltipManager

logger = logging.getLogger(__name__)


class _StatLine(UIElement):
    """A helper UIElement to manage a single line of text in the stats display."""

    def __init__(
        self, rect: pygame.Rect, label: str, value_str: str, tooltip_text: Optional[str]
    ):
        super().__init__(rect)
        self.label = label
        self.value_str = value_str
        self.tooltip_text = tooltip_text


class TowerInfoPanel(UIElement):
    """
    A UI panel that displays detailed information about a tower type
    selected from the build menu, before it is placed.
    MODIFIED: Now integrated with the TooltipManager.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower_data: Dict[str, Any],
        targeting_ai_config: Dict[str, Any],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
        tooltip_manager: "TooltipManager",
    ):
        """
        Initializes the TowerInfoPanel.
        """
        super().__init__(rect)
        self.tower_data = tower_data
        self.targeting_ai_config = targeting_ai_config
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.tooltip_manager = tooltip_manager

        self.stat_lines: List[_StatLine] = []

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
        self.stat_lines.clear()
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
            stat_line_y = total_height + self.rect.y
            for stat_info in stats_to_display:
                line_rect = pygame.Rect(
                    self.rect.x + padding,
                    stat_line_y,
                    self.rect.width - padding * 2,
                    22,
                )
                label = stat_info.get("label", "N/A")
                value_path = stat_info.get("value_path")
                value = (
                    get_nested_value(self.tower_data, value_path)
                    if value_path
                    else "N/A"
                )
                value_str = format_stat_value(value, stat_info.get("format"))
                description = stat_info.get("description")
                self.stat_lines.append(
                    _StatLine(line_rect, f"{label}:", value_str, description)
                )
                stat_line_y += 22
                total_height += 22
            total_height += spacing

        personas = self.tower_data.get("ai_config", {}).get("available_personas", [])
        if personas:
            total_height += self.font_header.get_height() + (spacing / 2)
            total_height += len(personas) * self.font_desc.get_height()

        total_height += padding
        self.rect.height = total_height

    def update(self, dt: float, game_state: "GameState"):
        """Updates hover states and requests tooltips for stats."""
        mouse_pos = pygame.mouse.get_pos()
        hovered_item = False
        for stat_line in self.stat_lines:
            stat_line.is_hovered = stat_line.rect.collidepoint(mouse_pos)
            if stat_line.is_hovered and stat_line.tooltip_text:
                self.tooltip_manager.request_tooltip(
                    stat_line.tooltip_text, stat_line.rect
                )
                hovered_item = True
                break

        if not hovered_item:
            self.tooltip_manager.cancel_tooltip()

    def draw(self, screen: pygame.Surface):
        """Draws the panel and all its components using theme styles."""
        bg_color = self.colors.get("panel_primary", (25, 30, 40))
        border_color = self.colors.get("border_primary", (80, 90, 100))
        border_radius = self.layout.get("border_radius_small", 5)
        border_width = self.layout.get("border_width_standard", 2)

        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
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

        if self.stat_lines:
            header_surf = self.font_header.render(
                "Statistics", True, self.colors.get("text_primary")
            )
            screen.blit(header_surf, (self.rect.x + padding, current_y))
            current_y += header_surf.get_height() + (spacing / 2)

            for stat_line in self.stat_lines:
                label_color = self.colors.get("text_secondary")
                value_color = self.colors.get("text_primary")
                if stat_line.is_hovered and stat_line.tooltip_text:
                    label_color = self.colors.get("text_accent")
                    value_color = self.colors.get("text_accent")

                label_surf = self.font_stat.render(stat_line.label, True, label_color)
                value_surf = self.font_stat.render(
                    stat_line.value_str, True, value_color
                )

                screen.blit(label_surf, stat_line.rect.topleft)
                value_rect = value_surf.get_rect(topright=stat_line.rect.topright)
                screen.blit(value_surf, value_rect)
