# rendering/menu/menu_manager.py
import pygame
import logging
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from enum import Enum, auto

from ..common.ui.ui_element import UIElement

# --- NEW: Import the new screen classes ---
from .level_selection_screen import LevelSelectionScreen
from .workshop_screen import WorkshopScreen

if TYPE_CHECKING:
    from game_logic.progression.progression_manager import ProgressionManager

# A simple type alias for menu actions
MenuAction = Callable[[], None]

logger = logging.getLogger(__name__)


# --- NEW: Internal state for the menu system ---
class MenuState(Enum):
    MAIN = auto()
    LEVEL_SELECT = auto()
    WORKSHOP = auto()


class MenuButton(UIElement):
    """A simple, reusable button class for the main menu system."""

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
        """Handles mouse events for the button. If clicked, it executes its action."""
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

    REFACTORED: Now a multi-screen state machine that navigates between the
    main menu, level selection, and the workshop.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        progression_manager: "ProgressionManager",
        all_configs: Dict[str, Any],
        start_level_callback: Callable,
        quit_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.progression_manager = progression_manager
        self.all_configs = all_configs
        self.start_level_callback = start_level_callback
        self.quit_callback = quit_callback

        self.state = MenuState.MAIN

        # --- Screen Instances (lazily initialized) ---
        self.main_menu_buttons: List[MenuButton] = []
        self.level_selection_screen: Optional[LevelSelectionScreen] = None
        self.workshop_screen: Optional[WorkshopScreen] = None

        self.title_font = pygame.font.SysFont("segoeui", 72, bold=True)
        self.title_color = (220, 220, 230)

        self._build_main_menu()
        logger.info("MenuManager initialized as a multi-screen navigator.")

    # --- State Transition Methods ---
    def _show_main_menu(self):
        self.state = MenuState.MAIN

    def _show_level_select(self):
        player_data = self.progression_manager.get_player_data()
        self.level_selection_screen = LevelSelectionScreen(
            screen_rect=self.screen_rect,
            level_configs=self.all_configs["level_styles"],
            unlocked_levels=player_data.unlocked_levels,
            start_level_callback=self.start_level_callback,
            back_callback=self._show_main_menu,
        )
        self.state = MenuState.LEVEL_SELECT

    def _show_workshop(self):
        self.workshop_screen = WorkshopScreen(
            screen_rect=self.screen_rect,
            progression_manager=self.progression_manager,
            back_callback=self._show_main_menu,
        )
        self.state = MenuState.WORKSHOP

    def _build_main_menu(self):
        """Creates and positions all the buttons for the main menu screen."""
        self.main_menu_buttons.clear()
        button_width, button_height, button_spacing = 300, 60, 20
        total_button_height = (button_height * 3) + (button_spacing * 2)
        start_y = self.screen_rect.centery - (total_button_height / 2) + 50

        button_actions = {
            "Play": self._show_level_select,
            "The Workshop": self._show_workshop,
            "Quit": self.quit_callback,
        }

        for i, (text, action) in enumerate(button_actions.items()):
            button_rect = pygame.Rect(
                self.screen_rect.centerx - button_width / 2,
                start_y + i * (button_height + button_spacing),
                button_width,
                button_height,
            )
            self.main_menu_buttons.append(MenuButton(button_rect, text, action))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Delegates events to the currently active screen."""
        if self.state == MenuState.MAIN:
            for button in self.main_menu_buttons:
                if button.handle_event(event):
                    return True
        elif self.state == MenuState.LEVEL_SELECT and self.level_selection_screen:
            self.level_selection_screen.handle_event(event)
            return True  # Absorb all events
        elif self.state == MenuState.WORKSHOP and self.workshop_screen:
            self.workshop_screen.handle_event(event)
            return True  # Absorb all events
        return False

    def update(self, dt: float):
        """Updates the currently active screen."""
        # Currently no updates needed, but structure is here for future animations etc.
        pass

    def draw(self, screen: pygame.Surface):
        """Draws the currently active screen."""
        if self.state == MenuState.MAIN:
            self._draw_main_menu(screen)
        elif self.state == MenuState.LEVEL_SELECT and self.level_selection_screen:
            self.level_selection_screen.draw(screen)
        elif self.state == MenuState.WORKSHOP and self.workshop_screen:
            self.workshop_screen.draw(screen)

    def _draw_main_menu(self, screen: pygame.Surface):
        """Draws the main title and buttons."""
        title_surf = self.title_font.render("ChaosDefense", True, self.title_color)
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.2
        )
        screen.blit(title_surf, title_rect)

        for button in self.main_menu_buttons:
            button.draw(screen)
