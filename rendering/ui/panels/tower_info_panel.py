# rendering/ui/panels/tower_info_panel.py
import pygame
import logging
from typing import Dict, Any, TYPE_CHECKING

from ..ui_element import UIElement
from ..text.text_renderer import render_text_wrapped

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

        Args:
            rect (pygame.Rect): The rectangle defining the panel's position and size.
            tower_data (Dict[str, Any]): The configuration data for the tower type.
            targeting_ai_config (Dict[str, Any]): The global targeting AI config.
        """
        super().__init__(rect)
        self.tower_data = tower_data
        self.targeting_ai_config = targeting_ai_config  # --- NEW ---
        self._setup_fonts_and_colors()

    def _setup_fonts_and_colors(self):
        """Initializes font and color constants for drawing."""
        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_header = pygame.font.SysFont("segoeui", 18, bold=True)
        self.font_stat = pygame.font.SysFont("segoeui", 16)
        self.font_desc = pygame.font.SysFont("segoeui", 14)
        self.colors = {
            "bg": (25, 30, 40, 230),
            "bg_hover": (25, 30, 40, 60),  # --- NEW: Transparent background color ---
            "border": (80, 90, 100),
            "title": (240, 240, 240),
            "header": (200, 200, 210),
            "stat_label": (160, 160, 170),
            "stat_value": (220, 220, 230),
            "desc": (180, 180, 190),
        }

    def draw(self, screen: pygame.Surface):
        """Draws the panel and all its components."""
        # --- NEW: Change background transparency on hover ---
        bg_color = self.colors["bg_hover"] if self.is_hovered else self.colors["bg"]

        # Draw panel background and border
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(bg_color)
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=5)

        # Render and Blit all text content
        self._draw_text_content(screen)

    def _draw_text_content(self, screen: pygame.Surface):
        """A helper method to render and position all text within the panel."""
        padding = 15
        line_height_stat = 24
        current_y = self.rect.y + padding

        # --- Title and Cost ---
        title_surf = self.font_title.render(
            self.tower_data.get("name", "N/A"), True, self.colors["title"]
        )
        screen.blit(title_surf, (self.rect.x + padding, current_y))

        cost_text = f"{self.tower_data.get('cost', 0)}G"
        cost_surf = self.font_title.render(cost_text, True, (255, 215, 0))
        cost_rect = cost_surf.get_rect(topright=(self.rect.right - padding, current_y))
        screen.blit(cost_surf, cost_rect)
        current_y += title_surf.get_height() + 10

        # --- Description ---
        description = self.tower_data.get("description", "No description available.")
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc_surfaces = render_text_wrapped(
            description, self.font_desc, self.colors["desc"], desc_max_width
        )
        for line_surf in wrapped_desc_surfaces:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += self.font_desc.get_height()
        current_y += 15

        # --- Statistics Header ---
        stats_header_surf = self.font_header.render(
            "Base Statistics", True, self.colors["header"]
        )
        screen.blit(stats_header_surf, (self.rect.x + padding, current_y))
        current_y += stats_header_surf.get_height() + 5

        # --- Key Statistics ---
        attack_data = self.tower_data.get("attack", {}).get("data", {})
        stats_to_display = {
            "Damage": attack_data.get("damage"),
            "Range": attack_data.get("range"),
            "Fire Rate": f"{attack_data.get('fire_rate', 0.0):.2f}/s",
            "DPS": attack_data.get("dps"),
            "Blast Radius": attack_data.get("blast_radius"),
        }

        for label, value in stats_to_display.items():
            if value is None or value == 0 or value == "0.00/s":
                continue

            label_surf = self.font_stat.render(
                f"{label}:", True, self.colors["stat_label"]
            )
            value_surf = self.font_stat.render(
                str(value), True, self.colors["stat_value"]
            )

            screen.blit(label_surf, (self.rect.x + padding, current_y))
            screen.blit(value_surf, (self.rect.x + self.rect.width / 2, current_y))
            current_y += line_height_stat

        current_y += 15

        # --- NEW: Targeting Modes Section ---
        ai_config = self.tower_data.get("ai_config", {})
        personas = ai_config.get("available_personas", [])
        if personas:
            header_surf = self.font_header.render(
                "Targeting Modes", True, self.colors["header"]
            )
            screen.blit(header_surf, (self.rect.x + padding, current_y))
            current_y += header_surf.get_height() + 5

            persona_names = [
                self.targeting_ai_config.get(p, {}).get("name", p) for p in personas
            ]

            persona_text = ", ".join(persona_names)
            wrapped_personas = render_text_wrapped(
                persona_text, self.font_desc, self.colors["desc"], desc_max_width
            )
            for line_surf in wrapped_personas:
                screen.blit(line_surf, (self.rect.x + padding, current_y))
                current_y += self.font_desc.get_height()
