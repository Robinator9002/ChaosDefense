# rendering/ui/buttons/upgrade_button.py
import pygame
import logging
from typing import Optional, TYPE_CHECKING

# Import the base class from the parent directory using '..'
from ..ui_element import UIElement

# Use TYPE_CHECKING to avoid circular imports for type hinting.
if TYPE_CHECKING:
    from game_logic.upgrades.upgrade import Upgrade
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class UpgradeButton(UIElement):
    """
    A specific UI element representing a clickable button for a tower upgrade.

    This button now includes a 'processing' state to prevent misclicks when an
    upgrade is purchased rapidly, providing immediate visual feedback and
    absorbing subsequent inputs until the UI refreshes.
    """

    def __init__(self, rect: pygame.Rect, upgrade: "Upgrade", can_afford: bool):
        """
        Initializes a new UpgradeButton.

        Args:
            rect (pygame.Rect): The rectangle for the button's position and size.
            upgrade (Upgrade): The Upgrade data object this button represents.
            can_afford (bool): Whether the player currently has enough gold for
                               this upgrade.
        """
        super().__init__(rect)
        self.upgrade = upgrade
        self.can_afford = can_afford

        # NEW: State to track if a purchase is in progress.
        self.is_processing = False

        # --- Font and Color Definitions ---
        self.font_name = pygame.font.SysFont("segoeui", 16, bold=True)
        self.font_cost = pygame.font.SysFont("segoeui", 14, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 12)

        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_processing": (20, 25, 30),  # Color for the button while processing
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "text_name": (230, 230, 240),
            "text_desc": (180, 180, 190),
            "cost_can_afford": (255, 215, 0),
            "cost_cant_afford": (180, 40, 40),
            "disabled_overlay": (0, 0, 0, 100),  # Semi-transparent black
        }

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[str]:
        """
        Handles mouse clicks on the button.

        If the button is clicked, it immediately enters a 'processing' state
        to prevent further clicks until the UI is refreshed.
        """
        # NEW: If the button is already processing a click, ignore all new events.
        if self.is_processing:
            return None

        action = super().handle_event(event, game_state)
        if action:
            return action

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.can_afford:
                logger.info(
                    f"Player clicked to purchase upgrade: {self.upgrade.id}. Setting to processing state."
                )
                # NEW: Immediately set the state to processing.
                self.is_processing = True
                return f"purchase_upgrade_{self.upgrade.id}"

        return None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """
        Draws the upgrade button with its text and dynamic colors, now
        including a visual state for when a purchase is processing.
        """
        self.can_afford = game_state.gold >= self.upgrade.cost

        # --- Draw Background and Border based on state ---
        if self.is_processing:
            bg_color = self.colors["bg_processing"]
            border_color = self.colors["border_default"]
        elif self.is_hovered and self.can_afford:
            bg_color = self.colors["bg_hover"]
            border_color = self.colors["border_hover"]
        else:
            bg_color = self.colors["bg_default"]
            border_color = self.colors["border_default"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)

        # --- Render and Blit Text ---
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

        desc_surf = self.font_desc.render(
            self.upgrade.description, True, self.colors["text_desc"]
        )
        screen.blit(desc_surf, (self.rect.x + padding, self.rect.y + padding + 24))

        # --- Draw Disabled/Processing Overlay ---
        if not self.can_afford or self.is_processing:
            overlay_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay_surf.fill(self.colors["disabled_overlay"])
            screen.blit(overlay_surf, self.rect.topleft)
