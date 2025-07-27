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

    This button displays the upgrade's name, cost, and description. It visually
    changes based on whether the player can afford the upgrade and handles
    click events to initiate a purchase.
    """

    def __init__(self, rect: pygame.Rect, upgrade: "Upgrade", can_afford: bool):
        """
        Initializes a new UpgradeButton.

        Args:
            rect (pygame.Rect): The rectangle for the button's position and size.
            upgrade (Upgrade): The Upgrade data object this button represents.
            can_afford (bool): Whether the player currently has enough gold for
                               this upgrade. This is passed in to determine the
                               initial visual state.
        """
        super().__init__(rect)
        self.upgrade = upgrade
        self.can_afford = can_afford

        # --- Font and Color Definitions ---
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
            "disabled_overlay": (0, 0, 0, 100),  # Semi-transparent black
        }

        # --- BUG FIX: Proactive Hover Check ---
        # Immediately check if the mouse is already over this button the moment
        # it's created. This solves the race condition where a button appears
        # under a static cursor and doesn't register as 'hovered' until the
        # mouse moves, causing spam-clicks to fail.
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            self.is_hovered = True

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[str]:
        """
        Handles mouse clicks on the button.

        If the button is clicked and the player can afford the upgrade, it
        returns a unique action string to be processed by the UIManager.
        """
        # The base class handle_event updates the hover state on MOUSEMOTION.
        # We must call it to ensure the button de-hovers when the mouse moves away.
        super().handle_event(event, game_state)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.can_afford:
                logger.info(f"Player clicked to purchase upgrade: {self.upgrade.id}")
                return f"purchase_upgrade_{self.upgrade.id}"

        return None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """
        Draws the upgrade button with its text and dynamic colors.
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

        # --- Draw Disabled Overlay ---
        if not self.can_afford:
            overlay_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay_surf.fill(self.colors["disabled_overlay"])
            screen.blit(overlay_surf, self.rect.topleft)
