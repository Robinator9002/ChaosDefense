# rendering/menu/level_selection_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set

from ..common.ui.ui_element import UIElement
from ..common.text.text_renderer import render_text_wrapped

logger = logging.getLogger(__name__)


class LevelButton(UIElement):
    """
    A UI element representing a single, clickable level in the selection screen.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        level_id: str,
        level_data: Dict[str, Any],
        is_locked: bool,
        action: Callable,
    ):
        super().__init__(rect)
        self.level_id = level_id
        self.name = level_id.replace("_", " ").title()
        self.description = level_data.get("generation_params", {}).get(
            "description", "No description available."
        )
        self.is_locked = is_locked
        self.action = action

        self.font_name = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 14)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_locked": (30, 35, 40),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "border_locked": (50, 55, 60),
            "text_name": (210, 210, 220),
            "text_desc": (160, 160, 170),
            "text_locked": (100, 100, 110),
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles mouse clicks. If not locked, it executes its action."""
        super().handle_event(event, game_state=None)
        if (
            not self.is_locked
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if self.is_hovered:
                self.action(self.level_id)
                return True
        return False

    def draw(self, screen: pygame.Surface):
        """Draws the level button to the screen."""
        if self.is_locked:
            bg_color = self.colors["bg_locked"]
            border_color = self.colors["border_locked"]
            name_color = self.colors["text_locked"]
            desc_color = self.colors["text_locked"]
        else:
            bg_color = (
                self.colors["bg_hover"]
                if self.is_hovered
                else self.colors["bg_default"]
            )
            border_color = (
                self.colors["border_hover"]
                if self.is_hovered
                else self.colors["border_default"]
            )
            name_color = self.colors["text_name"]
            desc_color = self.colors["text_desc"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        # Draw Level Name
        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 10))

        # Draw Description
        desc_surfaces = render_text_wrapped(
            self.description, self.font_desc, desc_color, self.rect.width - 30
        )
        current_y = self.rect.y + 45
        for line in desc_surfaces:
            screen.blit(line, (self.rect.x + 15, current_y))
            current_y += line.get_height()


class LevelSelectionScreen:
    """
    Manages and renders the level selection UI, allowing the player to choose
    which map to play on.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        level_configs: Dict[str, Any],
        unlocked_levels: Set[str],
        start_level_callback: Callable,
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.level_configs = level_configs
        self.unlocked_levels = unlocked_levels
        self.start_level_callback = start_level_callback
        self.back_callback = back_callback

        self.buttons: List[LevelButton] = []
        self.back_button: UIElement = None
        self._build_layout()

    def _build_layout(self):
        """Creates and positions all UI elements for the screen."""
        self.buttons.clear()

        title_font = pygame.font.SysFont("segoeui", 52, bold=True)
        self.title_surf = title_font.render("Select Mission", True, (220, 220, 230))
        self.title_rect = self.title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.1
        )

        button_width, button_height, button_spacing = 350, 100, 20
        num_buttons = len(self.level_configs)

        # Simple vertical list layout for now
        start_y = self.title_rect.bottom + 50

        for i, (level_id, level_data) in enumerate(self.level_configs.items()):
            is_locked = level_id not in self.unlocked_levels
            button_rect = pygame.Rect(
                self.screen_rect.centerx - button_width / 2,
                start_y + i * (button_height + button_spacing),
                button_width,
                button_height,
            )
            self.buttons.append(
                LevelButton(
                    button_rect,
                    level_id,
                    level_data,
                    is_locked,
                    self.start_level_callback,
                )
            )

        # Back Button
        back_button_rect = pygame.Rect(30, self.screen_rect.bottom - 80, 150, 50)
        # Using a generic UIElement for the back button for simplicity
        self.back_button = UIElement(back_button_rect)
        self.back_font = pygame.font.SysFont("segoeui", 24, bold=True)

    def handle_event(self, event: pygame.event.Event):
        """Delegates events to the level buttons and the back button."""
        for button in self.buttons:
            if button.handle_event(event):
                return

        self.back_button.handle_event(event, game_state=None)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the entire level selection screen."""
        screen.blit(self.title_surf, self.title_rect)

        for button in self.buttons:
            button.draw(screen)

        # Draw Back Button
        back_bg_color = (60, 75, 90) if self.back_button.is_hovered else (40, 50, 60)
        pygame.draw.rect(screen, back_bg_color, self.back_button.rect, border_radius=8)
        back_text_surf = self.back_font.render("Back", True, (210, 210, 220))
        back_text_rect = back_text_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_text_surf, back_text_rect)
