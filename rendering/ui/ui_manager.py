# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING

# --- New, Structured Imports ---
# The UI components are now organized into subdirectories for better project structure.
from .buttons.tower_button import TowerButton
from .panels.upgrade_panel import UpgradePanel

# Use TYPE_CHECKING for type hinting to avoid circular imports at runtime.
if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.game_manager import GameManager
    from game_logic.entities.tower import Tower

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements, including the static build panel and the dynamic
    tower upgrade panel. It acts as a state machine, showing and hiding UI
    components based on the player's selections in the GameState.
    """

    def __init__(
        self, screen_rect: pygame.Rect, game_manager: "GameManager", assets_path: Path
    ):
        """
        Initializes the UIManager.

        Args:
            screen_rect (pygame.Rect): The rectangle of the main game window.
            game_manager (GameManager): A reference to the main game manager,
                                        needed to access configs and process actions.
            assets_path (Path): The root path to the assets directory.
        """
        self.screen_rect = screen_rect
        self.game_manager = game_manager  # Store a reference to the GameManager
        self.assets_path = assets_path

        # --- UI Component Storage ---
        self.build_buttons: List[TowerButton] = []
        self.upgrade_panel: Optional[UpgradePanel] = None

        self._create_tower_build_panel()

    def _create_tower_build_panel(self):
        """
        Creates and positions the tower selection buttons at the bottom of the screen.
        """
        logger.info("Creating tower build UI panel.")
        button_size = 64
        panel_height = 80
        spacing = 10
        tower_types = self.game_manager.configs.get("tower_types", {})

        num_buttons = len(tower_types)
        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)
        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )

        current_x = start_x
        for tower_id, tower_data in tower_types.items():
            button_rect = pygame.Rect(current_x, start_y, button_size, button_size)
            # Pass the tower_id directly now
            button = TowerButton(button_rect, tower_id, tower_data, self.assets_path)
            self.build_buttons.append(button)
            current_x += button_size + spacing

    def handle_event(self, event: pygame.event.Event, game_state: "GameState") -> bool:
        """
        Passes events to UI elements and handles resulting actions.

        This method now implements a hierarchy: it checks the upgrade panel first,
        then the build panel. This ensures that a click on the upgrade panel isn't
        mistakenly handled by the build panel if they overlap.

        Returns:
            True if a UI element handled the event, False otherwise.
        """
        # 1. Prioritize the Upgrade Panel if it's active.
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                self._process_ui_action(action, game_state)
                return True  # Event was consumed by the upgrade panel.

        # 2. Check the bottom build panel buttons.
        mouse_pos = pygame.mouse.get_pos()
        if any(button.rect.collidepoint(mouse_pos) for button in self.build_buttons):
            for button in self.build_buttons:
                action = button.handle_event(event, game_state)
                if action:
                    self._process_ui_action(action, game_state)
            return True  # Event was consumed by the build panel.

        # If no UI element handled the event, return False.
        return False

    def _process_ui_action(self, action: str, game_state: "GameState"):
        """
        Updates the game state based on a string command from a UI element.
        """
        if action.startswith("select_tower_"):
            tower_id = action.replace("select_tower_", "")
            if game_state.selected_tower_to_build == tower_id:
                game_state.clear_selection()
            else:
                game_state.selected_tower_to_build = tower_id
                logger.info(f"Player selected '{tower_id}' for building.")

        elif action.startswith("purchase_upgrade_"):
            # Example action: "purchase_upgrade_turret_a2"
            upgrade_id = action.replace("purchase_upgrade_", "")
            tower_id = game_state.selected_entity_id

            # Extract the path ('a' or 'b') from the upgrade ID.
            # e.g., "turret_a2" -> "_a"
            path_char = upgrade_id.split("_")[-1][0]
            path_id = f"path_{path_char}"

            if tower_id:
                self.game_manager.purchase_tower_upgrade(tower_id, path_id)
            else:
                logger.warning(
                    "Upgrade purchased but no tower was selected in GameState."
                )

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates all UI elements, including the dynamic creation and destruction
        of the upgrade panel based on the currently selected entity.
        """
        # Update the static build buttons
        for button in self.build_buttons:
            button.update(dt, game_state)

        # --- Dynamic Upgrade Panel Management ---
        selected_id = game_state.selected_entity_id

        if selected_id:
            # An entity is selected. Check if it's the one we're displaying.
            if (
                not self.upgrade_panel
                or self.upgrade_panel.tower.entity_id != selected_id
            ):
                # Find the selected tower object from the game's list of towers.
                selected_tower = next(
                    (t for t in self.game_manager.towers if t.entity_id == selected_id),
                    None,
                )
                if selected_tower:
                    # Create a new panel for this tower.
                    panel_rect = pygame.Rect(self.screen_rect.width - 270, 10, 260, 400)
                    self.upgrade_panel = UpgradePanel(
                        rect=panel_rect,
                        tower=selected_tower,
                        upgrade_manager=self.game_manager.upgrade_manager,
                        game_state=game_state,
                    )
        else:
            # No entity is selected, so ensure the panel is closed.
            if self.upgrade_panel:
                self.upgrade_panel = None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws all managed UI elements."""
        # --- Draw Build Panel Background ---
        panel_rect = pygame.Rect(
            0, self.screen_rect.bottom - 80, self.screen_rect.width, 80
        )
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 25, 30, 200))
        screen.blit(panel_surf, panel_rect.topleft)

        # Draw the build buttons
        for button in self.build_buttons:
            button.draw(screen, game_state)

        # --- Draw Upgrade Panel ---
        # If the upgrade panel exists, draw it on top of everything else.
        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
