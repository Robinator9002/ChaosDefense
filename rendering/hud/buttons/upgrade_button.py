# rendering/ui/buttons/upgrade_button.py
import pygame
import logging
from typing import Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from rendering.common.ui.ui_action import UIAction, ActionType
from rendering.common.text.text_renderer import render_text_wrapped

if TYPE_CHECKING:
    from game_logic.upgrades.upgrade import Upgrade
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class UpgradeButton(UIElement):
    """
    A specific UI element representing a clickable button for a tower upgrade.

    REFACTORED: This button now dynamically calculates its own height based on
    the length of its description text, ensuring that all content fits
    within its bounds without overflowing.
    """

    def __init__(self, rect: pygame.Rect, upgrade: "Upgrade", can_afford: bool):
        """
        Initializes a new UpgradeButton, calculating its required height.
        """
        # Initialize with the provided rect, but we will immediately adjust its height.
        super().__init__(rect)
        self.upgrade = upgrade
        self.can_afford = can_afford

        self._setup_fonts_and_colors()
        # --- NEW: Pre-render the wrapped text to determine the required height ---
        self._pre_render_text()
        # --- NEW: Adjust the button's own rectangle height ---
        self._calculate_and_set_dynamic_height()

        if self.rect.collidepoint(pygame.mouse.get_pos()):
            self.is_hovered = True

    def _setup_fonts_and_colors(self):
        """Initializes font and color constants for drawing."""
        self.font_name = pygame.font.SysFont("segoeui", 16, bold=True)
        self.font_cost = pygame.font.SysFont("segoeui", 14, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 12)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "text_name": (230, 230, 240),
            "text_desc": (180, 180, 190),
            "cost_can_afford": (255, 215, 0),
            "cost_cant_afford": (180, 40, 40),
            "disabled_overlay": (0, 0, 0, 100),
        }

    def _pre_render_text(self):
        """
        Renders all text surfaces ahead of time. This is necessary to calculate
        the required height of the button before the main draw call.
        """
        padding = 8
        # --- Name and Cost (single line) ---
        self.name_surf = self.font_name.render(
            self.upgrade.name, True, self.colors["text_name"]
        )
        cost_color = (
            self.colors["cost_can_afford"]
            if self.can_afford
            else self.colors["cost_cant_afford"]
        )
        self.cost_surf = self.font_cost.render(
            f"{self.upgrade.cost}G", True, cost_color
        )

        # --- Description (potentially multi-line) ---
        desc_max_width = self.rect.width - (padding * 2)
        self.wrapped_desc_surfaces = render_text_wrapped(
            self.upgrade.description,
            self.font_desc,
            self.colors["text_desc"],
            desc_max_width,
        )

    def _calculate_and_set_dynamic_height(self):
        """
        Calculates the total required height for all text content plus padding
        and resizes the button's rect.
        """
        padding = 8
        # Height of the top section (name/cost)
        top_section_height = self.name_surf.get_height()
        # Total height of all description lines
        desc_section_height = sum(
            surf.get_height() for surf in self.wrapped_desc_surfaces
        )
        # Total height is top section + description + top/bottom padding
        total_content_height = top_section_height + desc_section_height + (padding * 2)
        # Set the button's final height
        self.rect.height = total_content_height

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        """Handles mouse clicks on the button."""
        super().handle_event(event, game_state)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.can_afford:
                logger.info(f"Player clicked to purchase upgrade: {self.upgrade.id}")
                return UIAction(
                    type=ActionType.PURCHASE_UPGRADE, entity_id=self.upgrade.id
                )
        return None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws the dynamically sized upgrade button."""
        self.can_afford = game_state.gold >= self.upgrade.cost

        # --- Draw Background and Border (using the now-correct self.rect.height) ---
        bg_color = (
            self.colors["bg_hover"]
            if self.is_hovered and self.can_afford
            else self.colors["bg_default"]
        )
        border_color = (
            self.colors["border_hover"]
            if self.is_hovered and self.can_afford
            else self.colors["border_default"]
        )
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)

        # --- Blit the pre-rendered text surfaces ---
        padding = 8
        screen.blit(self.name_surf, (self.rect.x + padding, self.rect.y + padding))
        cost_rect = self.cost_surf.get_rect(
            topright=(self.rect.right - padding, self.rect.y + padding)
        )
        screen.blit(self.cost_surf, cost_rect)

        current_y = self.rect.y + self.name_surf.get_height() + padding
        for line_surf in self.wrapped_desc_surfaces:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += line_surf.get_height()

        # --- Draw Disabled Overlay ---
        if not self.can_afford:
            overlay_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay_surf.fill(self.colors["disabled_overlay"])
            screen.blit(overlay_surf, self.rect.topleft)
