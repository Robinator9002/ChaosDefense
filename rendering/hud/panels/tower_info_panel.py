# rendering/hud/panels/tower_info_panel.py
import pygame
import logging
from typing import Dict, Any, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from rendering.text.text_renderer import render_text_wrapped

# --- NEW: Import shared utility functions ---
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class TowerInfoPanel(UIElement):
    """
    A UI panel that displays detailed information about a tower type
    selected from the build menu, before it is placed.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower_data: Dict[str, Any],
        targeting_ai_config: Dict[str, Any],
    ):
        """
        Initializes the TowerInfoPanel.
        """
        super().__init__(rect)
        self.tower_data = tower_data
        self.targeting_ai_config = targeting_ai_config
        self._setup_fonts_and_colors()
        self._calculate_and_set_dynamic_height()

    def _setup_fonts_and_colors(self):
        """Initializes font and color constants for drawing."""
        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_header = pygame.font.SysFont("segoeui", 18, bold=True)
        self.font_stat = pygame.font.SysFont("segoeui", 16)
        self.font_desc = pygame.font.SysFont("segoeui", 15)
        self.colors = {
            "bg": (25, 30, 40, 230),
            "bg_hover": (25, 30, 40, 60),
            "border": (80, 90, 100),
            "title": (240, 240, 240),
            "header": (200, 200, 210),
            "stat_label": (160, 160, 170),
            "stat_value": (220, 220, 230),
            "desc": (180, 180, 190),
        }

    def _calculate_and_set_dynamic_height(self):
        """Calculates the total required height for all content and resizes the panel."""
        padding = 15
        total_height = padding
        total_height += self.font_title.get_height() + 10

        description = self.tower_data.get("description", "No description available.")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            description, self.font_desc, self.colors["desc"], desc_max_width
        )
        total_height += sum(s.get_height() for s in wrapped_desc) + 15

        stats_to_display = self.tower_data.get("info_panel_stats", [])
        if stats_to_display:
            total_height += self.font_header.get_height() + 5
            total_height += len(stats_to_display) * 24
            total_height += 15

        personas = self.tower_data.get("ai_config", {}).get("available_personas", [])
        if personas:
            total_height += self.font_header.get_height() + 5
            total_height += len(personas) * self.font_desc.get_height()

        total_height += padding
        self.rect.height = total_height

    def draw(self, screen: pygame.Surface):
        """Draws the panel and all its components."""
        bg_color = self.colors["bg_hover"] if self.is_hovered else self.colors["bg"]
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(bg_color)
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=5)
        self._draw_text_content(screen)

    def _draw_text_content(self, screen: pygame.Surface):
        """Renders and positions all text within the panel."""
        padding = 15
        current_y = self.rect.y + padding

        title_surf = self.font_title.render(
            self.tower_data.get("name", "N/A"), True, self.colors["title"]
        )
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        cost_text = f"{self.tower_data.get('cost', 0)}G"
        cost_surf = self.font_title.render(cost_text, True, (255, 215, 0))
        cost_rect = cost_surf.get_rect(topright=(self.rect.right - padding, current_y))
        screen.blit(cost_surf, cost_rect)
        current_y += title_surf.get_height() + 10

        description = self.tower_data.get("description", "No description available.")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc = render_text_wrapped(
            description, self.font_desc, self.colors["desc"], desc_max_width
        )
        for line_surf in wrapped_desc:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += line_surf.get_height()
        current_y += 15

        stats_to_display = self.tower_data.get("info_panel_stats", [])
        if stats_to_display:
            header_surf = self.font_header.render(
                "Statistics", True, self.colors["header"]
            )
            screen.blit(header_surf, (self.rect.x + padding, current_y))
            current_y += header_surf.get_height() + 5

            for stat_info in stats_to_display:
                label = stat_info.get("label", "N/A")
                value_path = stat_info.get("value_path")
                # --- REFACTORED: Use shared utility function ---
                value = (
                    get_nested_value(self.tower_data, value_path)
                    if value_path
                    else "N/A"
                )

                if value is None:
                    continue

                # --- REFACTORED: Use shared utility function ---
                value_str = format_stat_value(value, stat_info.get("format"))

                label_surf = self.font_stat.render(
                    f"{label}:", True, self.colors["stat_label"]
                )
                value_surf = self.font_stat.render(
                    value_str, True, self.colors["stat_value"]
                )

                screen.blit(label_surf, (self.rect.x + padding, current_y))
                value_rect = value_surf.get_rect(
                    topright=(self.rect.right - padding, current_y)
                )
                screen.blit(value_surf, value_rect)
                current_y += 24
            current_y += 15

        personas = self.tower_data.get("ai_config", {}).get("available_personas", [])
        if personas:
            header_surf = self.font_header.render(
                "Targeting Modes", True, self.colors["header"]
            )
            screen.blit(header_surf, (self.rect.x + padding, current_y))
            current_y += header_surf.get_height() + 5

            for persona_id in personas:
                persona_name = self.targeting_ai_config.get(persona_id, {}).get(
                    "name", persona_id
                )
                line_text = f"• {persona_name}"
                line_surf = self.font_desc.render(line_text, True, self.colors["desc"])
                screen.blit(line_surf, (self.rect.x + padding, current_y))
                current_y += self.font_desc.get_height()
