# rendering/menu/menu_manager.py
import pygame
import logging
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from enum import Enum, auto

from ..common.ui.ui_element import UIElement
from .screens.level_selection_screen import LevelSelectionScreen
from .screens.workshop_screen import WorkshopScreen

if TYPE_CHECKING:
    from game_logic.progression.progression_manager import ProgressionManager
    from rendering.text.font_manager import FontManager

MenuAction = Callable[[], None]
logger = logging.getLogger(__name__)


class MenuState(Enum):
    MAIN = auto()
    LEVEL_SELECT = auto()
    WORKSHOP = auto()


class MenuButton(UIElement):
    """
    A simple, reusable button class for the main menu system.
    REFACTORED: Now fully theme-driven for consistent styling.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        action: MenuAction,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.text = text
        self.action = action
        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font = font_manager.get_font("button_large")

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles mouse events for the button. If clicked, it executes its action."""
        # --- FIX (Step 1.1): Prevent crash on non-mouse events & fix stale hover state ---
        # This handler now robustly processes only mouse events by checking the event type.
        # This prevents crashes when keyboard events are passed to this handler.
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False  # A hover event is never "handled" in a way that stops propagation

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # We check the position directly on click, which is the most reliable way.
            if self.rect.collidepoint(event.pos):
                self.action()
                return True  # The click was handled by this button.

        return False

    def draw(self, screen: pygame.Surface):
        """Draws the button to the screen using theme styles."""
        bg_color = (
            self.colors.get("panel_interactive_hover")
            if self.is_hovered
            else self.colors.get("panel_secondary")
        )
        border_color = (
            self.colors.get("border_interactive_selected")
            if self.is_hovered
            else self.colors.get("border_primary")
        )
        border_width = (
            self.layout.get("border_width_selected")
            if self.is_hovered
            else self.layout.get("border_width_standard")
        )

        pygame.draw.rect(
            screen,
            bg_color,
            self.rect,
            border_radius=self.layout.get("border_radius_large"),
        )
        pygame.draw.rect(
            screen,
            border_color,
            self.rect,
            border_width,
            border_radius=self.layout.get("border_radius_large"),
        )

        text_surf = self.font.render(self.text, True, self.colors.get("text_primary"))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


class MenuManager:
    """
    Manages the state and rendering of all out-of-game UI screens.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        progression_manager: "ProgressionManager",
        all_configs: Dict[str, Any],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
        start_level_callback: Callable,
        quit_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.progression_manager = progression_manager
        self.all_configs = all_configs
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.start_level_callback = start_level_callback
        self.quit_callback = quit_callback

        self.state = MenuState.MAIN
        self._load_theme_assets()

        self.main_menu_buttons: List[MenuButton] = []
        self.level_selection_screen: Optional[LevelSelectionScreen] = None
        self.workshop_screen: Optional[WorkshopScreen] = None

        self.rebuild_all_screens()
        logger.info("MenuManager initialized and configured with UI theme.")

    def _load_theme_assets(self):
        """Loads styles and fonts needed for the manager itself."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("title_large")

    def on_resize(self, new_screen_rect: pygame.Rect):
        """Handles window resizing by rebuilding all screens."""
        self.screen_rect = new_screen_rect
        self.rebuild_all_screens()

    def rebuild_all_screens(self):
        """Re-creates all menu buttons and screen instances."""
        self._build_main_menu()
        if self.state == MenuState.LEVEL_SELECT:
            self._show_level_select()
        elif self.state == MenuState.WORKSHOP:
            self._show_workshop()

    def _show_main_menu(self):
        self.state = MenuState.MAIN

    def _show_level_select(self):
        player_data = self.progression_manager.get_player_data()
        self.level_selection_screen = LevelSelectionScreen(
            screen_rect=self.screen_rect,
            level_configs=self.all_configs["level_styles"],
            unlocked_levels=player_data.unlocked_levels,
            ui_theme=self.ui_theme,
            font_manager=self.font_manager,
            start_level_callback=self.start_level_callback,
            back_callback=self._show_main_menu,
        )
        self.state = MenuState.LEVEL_SELECT

    def _show_workshop(self):
        self.workshop_screen = WorkshopScreen(
            screen_rect=self.screen_rect,
            progression_manager=self.progression_manager,
            ui_theme=self.ui_theme,
            font_manager=self.font_manager,
            back_callback=self._show_main_menu,
        )
        self.state = MenuState.WORKSHOP

    def _build_main_menu(self):
        """Creates and positions all buttons for the main menu screen."""
        self.main_menu_buttons.clear()
        button_width, button_height = 300, 60
        button_spacing = self.layout.get("spacing_large", 20)
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
            self.main_menu_buttons.append(
                MenuButton(button_rect, text, action, self.ui_theme, self.font_manager)
            )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Delegates events to the currently active screen."""
        if self.state == MenuState.MAIN:
            for button in self.main_menu_buttons:
                if button.handle_event(event):
                    return True
        elif self.state == MenuState.LEVEL_SELECT and self.level_selection_screen:
            self.level_selection_screen.handle_event(event)
            return True
        elif self.state == MenuState.WORKSHOP and self.workshop_screen:
            self.workshop_screen.handle_event(event)
            return True
        return False

    def update(self, dt: float):
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
        """Draws the main title and buttons using theme styles."""
        title_surf = self.font_title.render(
            "ChaosDefense", True, self.colors.get("text_primary")
        )
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.2
        )
        screen.blit(title_surf, title_rect)

        for button in self.main_menu_buttons:
            button.draw(screen)
