# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from rendering.ui.tower_button import TowerButton

# Using Any for game_state to avoid circular dependencies
if "GameState" not in globals():
    from typing import Any as GameState

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements, including their creation, updates, and drawing.
    """

    def __init__(
        self, screen_rect: pygame.Rect, all_configs: Dict[str, Any], assets_path: Path
    ):
        """
        Initializes the UIManager.

        Args:
            screen_rect (pygame.Rect): The rectangle of the main game window.
            all_configs (Dict[str, Any]): A dictionary of all loaded game configs.
            assets_path (Path): The root path to the assets directory.
        """
        self.screen_rect = screen_rect
        self.tower_types = all_configs.get("tower_types", {})
        self.assets_path = assets_path

        self.buttons: List[TowerButton] = []
        self._create_tower_selection_panel()

    def _create_tower_selection_panel(self):
        """
        Creates and positions the tower selection buttons at the bottom of the screen.
        """
        logger.info("Creating tower selection UI panel.")
        button_size = 64
        panel_height = 80
        spacing = 10

        num_buttons = len(self.tower_types)
        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)

        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )

        current_x = start_x
        for tower_id, tower_data in self.tower_types.items():
            button_rect = pygame.Rect(current_x, start_y, button_size, button_size)
            button = TowerButton(button_rect, tower_id, tower_data, self.assets_path)
            self.buttons.append(button)
            current_x += button_size + spacing

    def handle_event(self, event: pygame.event.Event, game_state: GameState) -> bool:
        """
        Passes events to UI elements and handles resulting actions.

        Args:
            event (pygame.event.Event): The Pygame event to process.
            game_state (GameState): The current state of the game logic.

        Returns:
            True if a UI element handled the event, False otherwise.
        """
        # Check if the mouse is over any button first, to prevent map interaction
        # when clicking on the UI panel.
        mouse_pos = pygame.mouse.get_pos()
        if any(button.rect.collidepoint(mouse_pos) for button in self.buttons):
            # If the mouse is over the panel, we handle the event.
            for button in self.buttons:
                action = button.handle_event(event, game_state)
                if action:
                    self._process_ui_action(action, game_state)
            return True  # Event was consumed by the UI

        # If the click was not on the UI, clear any build selection.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state.selected_tower_to_build:
                logger.debug("Clicked off UI, clearing build selection.")
                game_state.clear_selection()

        return False  # Event was not handled by the UI

    def _process_ui_action(self, action: str, game_state: GameState):
        """
        Updates the game state based on a string command from a UI element.
        """
        if action.startswith("select_tower_"):
            tower_id = action.replace("select_tower_", "")

            # Toggle selection
            if game_state.selected_tower_to_build == tower_id:
                game_state.clear_selection()
            else:
                game_state.selected_tower_to_build = tower_id
                logger.info(f"Player selected '{tower_id}' for building.")

    def update(self, dt: float, game_state: GameState):
        """Updates all UI elements."""
        for button in self.buttons:
            button.update(dt, game_state)

    def draw(self, screen: pygame.Surface, game_state: GameState):
        """Draws all UI elements."""
        # Draw a semi-transparent panel background
        panel_rect = pygame.Rect(
            0, self.screen_rect.bottom - 80, self.screen_rect.width, 80
        )
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 25, 30, 200))
        screen.blit(panel_surf, panel_rect.topleft)

        # Draw the buttons on top of the panel
        for button in self.buttons:
            button.draw(screen, game_state)
