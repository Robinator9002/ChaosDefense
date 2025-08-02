# rendering/hud/buttons/upgrade_button.py
import pygame
import logging
from typing import Optional, TYPE_CHECKING, Dict, Any

from rendering.common.ui.ui_element import UIElement
from rendering.common.ui.ui_action import UIAction, ActionType

# --- MODIFIED: Corrected import path ---
from rendering.text.text_renderer import render_text_wrapped

if TYPE_CHECKING:
    from game_logic.upgrades.upgrade import Upgrade
    from game_logic.game_state import GameState
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class UpgradeButton(UIElement):
    """
    A UI element for a clickable tower upgrade.
    REFACTORED: Now fully theme-driven and dynamically sized.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        upgrade: "Upgrade",
        can_afford: bool,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes a new UpgradeButton, calculating its required height.
        """
        super().__init__(rect)
        self.upgrade = upgrade
        self.can_afford = can_afford
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self._load_theme_assets()
        self._pre_render_text()
        self._calculate_and_set_dynamic_height()

        if self.rect.collidepoint(pygame.mouse.get_pos()):
            self.is_hovered = True

    def _load_theme_assets(self):
        """Initializes font and color constants from the theme."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_name = self.font_manager.get_font("body_medium", bold=True)
        self.font_cost = self.font_manager.get_font("body_small", bold=True)
        self.font_desc = self.font_manager.get_font("body_tiny")

    def _pre_render_text(self):
        """Renders text surfaces to calculate height and for later blitting."""
        padding = self.layout.get("padding_small", 8)
        self.name_surf = self.font_name.render(
            self.upgrade.name, True, self.colors.get("text_primary")
        )

        cost_color = (
            self.colors.get("text_accent")
            if self.can_afford
            else self.colors.get("text_error")
        )
        self.cost_surf = self.font_cost.render(
            f"{self.upgrade.cost}G", True, cost_color
        )

        desc_max_width = self.rect.width - (padding * 2)
        self.wrapped_desc_surfaces = render_text_wrapped(
            self.upgrade.description,
            self.font_desc,
            self.colors.get("text_secondary"),
            desc_max_width,
        )

    def _calculate_and_set_dynamic_height(self):
        """Calculates the total required height and resizes the button's rect."""
        padding = self.layout.get("padding_small", 8)
        top_section_height = self.name_surf.get_height()
        desc_section_height = sum(
            surf.get_height() for surf in self.wrapped_desc_surfaces
        )
        total_content_height = top_section_height + desc_section_height + (padding * 2)
        self.rect.height = total_content_height

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        """Handles mouse clicks on the button."""
        self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.can_afford:
                logger.info(f"Player clicked to purchase upgrade: {self.upgrade.id}")
                return UIAction(
                    type=ActionType.PURCHASE_UPGRADE, entity_id=self.upgrade.id
                )
        return None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws the dynamically sized upgrade button using theme styles."""
        self.can_afford = game_state.gold >= self.upgrade.cost
        border_radius = self.layout.get("border_radius_small", 5)

        bg_color = (
            self.colors.get("panel_interactive_hover")
            if self.is_hovered and self.can_afford
            else self.colors.get("panel_secondary")
        )
        border_color = (
            self.colors.get("border_interactive_selected")
            if self.is_hovered and self.can_afford
            else self.colors.get("border_primary")
        )

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)
        pygame.draw.rect(
            screen, border_color, self.rect, 2, border_radius=border_radius
        )

        padding = self.layout.get("padding_small", 8)
        screen.blit(self.name_surf, (self.rect.x + padding, self.rect.y + padding))

        # Re-render cost surface in case affordability changed
        cost_color = (
            self.colors.get("text_accent")
            if self.can_afford
            else self.colors.get("text_error")
        )
        self.cost_surf = self.font_cost.render(
            f"{self.upgrade.cost}G", True, cost_color
        )
        cost_rect = self.cost_surf.get_rect(
            topright=(self.rect.right - padding, self.rect.y + padding)
        )
        screen.blit(self.cost_surf, cost_rect)

        current_y = self.rect.y + self.name_surf.get_height() + padding
        for line_surf in self.wrapped_desc_surfaces:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += line_surf.get_height()

        if not self.can_afford:
            overlay_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            # --- FIX: Convert the list-based color to a tuple before concatenation ---
            overlay_color = self.colors.get("background_primary", [0, 0, 0])
            overlay_surf.fill(tuple(overlay_color) + (100,))
            screen.blit(overlay_surf, self.rect.topleft)
