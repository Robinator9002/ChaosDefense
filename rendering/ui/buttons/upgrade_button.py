# rendering/ui/buttons/upgrade_button.py
import pygame
import logging
from typing import Optional, TYPE_CHECKING

from ..ui_element import UIElement
from ..ui_action import UIAction, ActionType
# --- NEW: Import the text wrapping utility ---
# We now import our reusable function to handle multi-line text.
from ..text.text_renderer import render_text_wrapped

if TYPE_CHECKING:
    from game_logic.upgrades.upgrade import Upgrade
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class UpgradeButton(UIElement):
    """
    A specific UI element representing a clickable button for a tower upgrade.

    This button displays the upgrade's name, cost, and a potentially multi-line
    description. It visually changes based on affordability and handles click
    events by emitting a structured UIAction.
    """

    def __init__(self, rect: pygame.Rect, upgrade: "Upgrade", can_afford: bool):
        """
        Initializes a new UpgradeButton.
        """
        super().__init__(rect)
        self.upgrade = upgrade
        self.can_afford = can_afford

        self._setup_fonts_and_colors()

        # --- BUG FIX: Proactive Hover Check ---
        # This ensures the button's hover state is correct upon creation,
        # in case the mouse is already over its position.
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

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        """
        Handles mouse clicks on the button.
        """
        super().handle_event(event, game_state)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.can_afford:
                logger.info(f"Player clicked to purchase upgrade: {self.upgrade.id}")
                return UIAction(
                    type=ActionType.PURCHASE_UPGRADE, entity_id=self.upgrade.id
                )
        return None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """
        Draws the upgrade button with its text and dynamic colors.
        Now uses the text wrapping utility for the description.
        """
        self.can_afford = game_state.gold >= self.upgrade.cost

        # --- Draw Background and Border ---
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

        # --- Render and Blit Static Text (Name and Cost) ---
        padding = 8
        name_surf = self.font_name.render(
            self.upgrade.name, True, self.colors["text_name"]
        )
        screen.blit(name_surf, (self.rect.x + padding, self.rect.y + padding))

        cost_color = (
            self.colors["cost_can_afford"]
            if self.can_afford
            else self.colors["cost_cant_afford"]
        )
        cost_surf = self.font_cost.render(f"{self.upgrade.cost}G", True, cost_color)
        cost_rect = cost_surf.get_rect(
            topright=(self.rect.right - padding, self.rect.y + padding)
        )
        screen.blit(cost_surf, cost_rect)

        # --- REFACTORED: Use the text wrapper for the description ---
        desc_max_width = self.rect.width - (padding * 2)
        wrapped_desc_surfaces = render_text_wrapped(
            self.upgrade.description,
            self.font_desc,
            self.colors["text_desc"],
            desc_max_width,
        )

        # Blit each line of the wrapped description
        current_y = self.rect.y + padding + 24
        for line_surf in wrapped_desc_surfaces:
            screen.blit(line_surf, (self.rect.x + padding, current_y))
            current_y += self.font_desc.get_height()

        # --- Draw Disabled Overlay ---
        if not self.can_afford:
            overlay_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay_surf.fill(self.colors["disabled_overlay"])
            screen.blit(overlay_surf, self.rect.topleft)
