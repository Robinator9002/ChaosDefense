# rendering/menu/workshop_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set

from ..common.ui.ui_element import UIElement
from ..common.text.text_renderer import render_text_wrapped
from game_logic.progression.progression_manager import ProgressionManager

logger = logging.getLogger(__name__)


class TowerUnlockButton(UIElement):
    """
    A UI element for unlocking a new tower in The Workshop.
    """

    def __init__(
        self, rect: pygame.Rect, tower_info: Dict[str, Any], purchase_callback: Callable
    ):
        super().__init__(rect)
        self.tower_id = tower_info["id"]
        self.name = tower_info["name"]
        self.description = tower_info["description"]
        self.cost = tower_info["cost"]
        self.is_unlocked = tower_info["unlocked"]
        self.purchase_callback = purchase_callback

        self.font_name = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 14)
        self.font_cost = pygame.font.SysFont("segoeui", 20, bold=True)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_unlocked": (35, 60, 45),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "border_unlocked": (70, 110, 85),
            "text_name": (210, 210, 220),
            "text_desc": (160, 160, 170),
            "text_unlocked": (180, 230, 190),
            "cost_can_afford": (255, 215, 0),
            "cost_cant_afford": (180, 40, 40),
        }

    def handle_event(self, event: pygame.event.Event, can_afford: bool) -> bool:
        """Handles clicks. If affordable and not unlocked, triggers purchase callback."""
        super().handle_event(event, game_state=None)
        if (
            not self.is_unlocked
            and can_afford
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if self.is_hovered:
                self.purchase_callback(self.tower_id)
                # The screen will be rebuilt, so we don't need to update state here
                return True
        return False

    def draw(self, screen: pygame.Surface, can_afford: bool):
        """Draws the button, showing its state (locked, unlocked, affordable)."""
        if self.is_unlocked:
            bg_color = self.colors["bg_unlocked"]
            border_color = self.colors["border_unlocked"]
            name_color = self.colors["text_unlocked"]
        else:
            bg_color = (
                self.colors["bg_hover"]
                if self.is_hovered and can_afford
                else self.colors["bg_default"]
            )
            border_color = (
                self.colors["border_hover"]
                if self.is_hovered and can_afford
                else self.colors["border_default"]
            )
            name_color = self.colors["text_name"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        # Draw Name and Cost/Status
        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 10))

        if self.is_unlocked:
            status_surf = self.font_cost.render(
                "UNLOCKED", True, self.colors["text_unlocked"]
            )
            status_rect = status_surf.get_rect(
                topright=(self.rect.right - 15, self.rect.y + 12)
            )
            screen.blit(status_surf, status_rect)
        else:
            cost_color = (
                self.colors["cost_can_afford"]
                if can_afford
                else self.colors["cost_cant_afford"]
            )
            cost_surf = self.font_cost.render(f"{self.cost} CS", True, cost_color)
            cost_rect = cost_surf.get_rect(
                topright=(self.rect.right - 15, self.rect.y + 12)
            )
            screen.blit(cost_surf, cost_rect)

        # Draw Description
        desc_surfaces = render_text_wrapped(
            self.description,
            self.font_desc,
            self.colors["text_desc"],
            self.rect.width - 30,
        )
        current_y = self.rect.y + 45
        for line in desc_surfaces:
            screen.blit(line, (self.rect.x + 15, current_y))
            current_y += line.get_height()


class WorkshopScreen:
    """
    Manages and renders The Workshop UI, where players can permanently
    unlock towers and purchase global upgrades.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        progression_manager: ProgressionManager,
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.progression_manager = progression_manager
        self.back_callback = back_callback

        self.tower_buttons: List[TowerUnlockButton] = []
        self.back_button: UIElement = None
        self._build_layout()

    def _build_layout(self):
        """Creates and positions all UI elements for the screen."""
        self.tower_buttons.clear()

        # --- Fonts and Title ---
        title_font = pygame.font.SysFont("segoeui", 52, bold=True)
        self.title_surf = title_font.render("The Workshop", True, (220, 220, 230))
        self.title_rect = self.title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.05
        )

        self.currency_font = pygame.font.SysFont("segoeui", 28, bold=True)

        # --- Tower Unlocks Section ---
        tower_unlocks = self.progression_manager.get_unlockable_towers()
        button_width, button_height, button_spacing = 400, 90, 15
        start_y = self.title_rect.bottom + 80

        for i, tower_info in enumerate(tower_unlocks):
            button_rect = pygame.Rect(
                self.screen_rect.width * 0.25 - button_width / 2,  # Left column
                start_y + i * (button_height + button_spacing),
                button_width,
                button_height,
            )
            self.tower_buttons.append(
                TowerUnlockButton(
                    button_rect, tower_info, self.progression_manager.purchase_tower
                )
            )

        # --- Back Button ---
        back_button_rect = pygame.Rect(30, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)
        self.back_font = pygame.font.SysFont("segoeui", 24, bold=True)

    def handle_event(self, event: pygame.event.Event):
        """Delegates events to all interactive elements."""
        current_currency = self.progression_manager.get_player_data().meta_currency
        for button in self.tower_buttons:
            can_afford = current_currency >= button.cost
            if button.handle_event(event, can_afford):
                # If a purchase was made, rebuild the layout to reflect the new state
                self._build_layout()
                return

        self.back_button.handle_event(event, game_state=None)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the entire Workshop screen."""
        screen.blit(self.title_surf, self.title_rect)

        # Draw Currency Display
        currency = self.progression_manager.get_player_data().meta_currency
        currency_text = f"Chaos Shards: {currency}"
        currency_surf = self.currency_font.render(currency_text, True, (255, 215, 0))
        currency_rect = currency_surf.get_rect(
            topright=(self.screen_rect.right - 30, 30)
        )
        screen.blit(currency_surf, currency_rect)

        # Draw Tower Buttons
        current_currency = self.progression_manager.get_player_data().meta_currency
        for button in self.tower_buttons:
            can_afford = current_currency >= button.cost
            button.draw(screen, can_afford)

        # Draw Back Button
        back_bg_color = (60, 75, 90) if self.back_button.is_hovered else (40, 50, 60)
        pygame.draw.rect(screen, back_bg_color, self.back_button.rect, border_radius=8)
        back_text_surf = self.back_font.render("Back", True, (210, 210, 220))
        back_text_rect = back_text_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_text_surf, back_text_rect)
