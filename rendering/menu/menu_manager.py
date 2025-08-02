# rendering/menu/menu_manager.py
import pygame
import logging
from typing import Optional, List, Dict, Any, Callable

from ..common.ui.ui_element import UIElement
from ..common.ui.ui_action import UIAction, ActionType

# A simple type alias for menu actions
MenuAction = Callable[[], None]

logger = logging.getLogger(__name__)


class MenuButton(UIElement):
    """
    A simple, reusable button class for the main menu system.
    """

    def __init__(self, rect: pygame.Rect, text: str, action: MenuAction):
        super().__init__(rect)
        self.text = text
        self.action = action
        self.font = pygame.font.SysFont("segoeui", 32, bold=True)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "text": (230, 230, 240),
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handles mouse events for the button. If clicked, it executes its action.

        Args:
            event (pygame.event.Event): The Pygame event to process.

        Returns:
            bool: True if the button was clicked, False otherwise.
        """
        super().handle_event(event, game_state=None)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.action()
                return True
        return False

    def draw(self, screen: pygame.Surface):
        """Draws the button to the screen."""
        bg_color = (
            self.colors["bg_hover"] if self.is_hovered else self.colors["bg_default"]
        )
        border_color = (
            self.colors["border_hover"]
            if self.is_hovered
            else self.colors["border_default"]
        )

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 3, border_radius=8)

        text_surf = self.font.render(self.text, True, self.colors["text"])
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


class MenuManager:
    """
    Manages the state, rendering, and interactions of the main menu and other
    out-of-game UI screens.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        new_game_callback: Callable,
        quit_callback: Callable,
    ):
        """
        Initializes the MenuManager.

        Args:
            screen_rect (pygame.Rect): The rectangle of the main game window.
            new_game_callback (Callable): The function to call when the "New Game" button is clicked.
            quit_callback (Callable): The function to call when the "Quit" button is clicked.
        """
        self.screen_rect = screen_rect
        self.buttons: List[MenuButton] = []

        # --- Title Font ---
        self.title_font = pygame.font.SysFont("segoeui", 72, bold=True)
        self.title_color = (220, 220, 230)

        # --- Callbacks from the main Game class ---
        self.new_game_callback = new_game_callback
        self.quit_callback = quit_callback

        self._build_main_menu()
        logger.info("MenuManager initialized.")

    def _build_main_menu(self):
        """
        Creates and positions all the buttons for the main menu screen.
        """
        self.buttons.clear()
        button_width, button_height, button_spacing = 300, 60, 20

        # Calculate starting Y position to center the block of buttons vertically
        total_button_height = (button_height * 3) + (button_spacing * 2)
        start_y = (
            self.screen_rect.centery - (total_button_height / 2) + 50
        )  # Offset down slightly

        # --- Button Definitions ---
        button_actions = {
            "New Game": self.new_game_callback,
            "Upgrades": lambda: logger.info(
                "Upgrades button clicked (not implemented)."
            ),
            "Quit": self.quit_callback,
        }

        for i, (text, action) in enumerate(button_actions.items()):
            button_rect = pygame.Rect(
                self.screen_rect.centerx - button_width / 2,
                start_y + i * (button_height + button_spacing),
                button_width,
                button_height,
            )
            self.buttons.append(MenuButton(button_rect, text, action))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Processes a Pygame event and delegates it to the menu buttons.

        Args:
            event (pygame.event.Event): The event to process.

        Returns:
            bool: True if an event was handled by a UI element, False otherwise.
        """
        for button in self.buttons:
            if button.handle_event(event):
                return True
        return False

    def update(self, dt: float):
        """
        Updates any animations or time-based logic for the menu.
        (Currently unused but here for future expansion).

        Args:
            dt (float): The time elapsed since the last frame.
        """
        pass

    def draw(self, screen: pygame.Surface):
        """
        Draws the main menu to the screen.

        Args:
            screen (pygame.Surface): The main display surface.
        """
        # Draw the main title
        title_surf = self.title_font.render("ChaosDefense", True, self.title_color)
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.2
        )
        screen.blit(title_surf, title_rect)

        # Draw all buttons
        for button in self.buttons:
            button.draw(screen)
