# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING

# --- New, Structured Imports ---
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
    tower upgrade panel. It now also assigns and tracks hotkeys for the
    tower build buttons.
    """

    def __init__(
        self, screen_rect: pygame.Rect, game_manager: "GameManager", assets_path: Path
    ):
        """
        Initializes the UIManager.
        """
        self.screen_rect = screen_rect
        self.game_manager = game_manager
        self.assets_path = assets_path

        # --- UI Component Storage ---
        self.build_buttons: List[TowerButton] = []
        self.upgrade_panel: Optional[UpgradePanel] = None

        # An ordered list to map hotkey numbers (index + 1) to tower_type_ids.
        self.hotkey_map: List[str] = []

        self._create_tower_build_panel()

    def _create_tower_build_panel(self):
        """
        Creates and positions the tower selection buttons, assigning them
        numeric hotkeys based on their order in the config file.
        """
        logger.info("Creating tower build UI panel with hotkeys.")
        button_size = 64
        panel_height = 80
        spacing = 10
        tower_types = self.game_manager.configs.get("tower_types", {})

        # --- Create a filtered list of actual tower data first ---
        valid_tower_items = []
        for tower_id, tower_data in tower_types.items():
            # --- BUG FIX: VALIDATION STEP ---
            # Ensure we only process entries that are dictionaries, skipping
            # any comments or other non-dict data in the JSON.
            if isinstance(tower_data, dict):
                valid_tower_items.append((tower_id, tower_data))

        num_buttons = len(valid_tower_items)
        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)
        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )

        current_x = start_x
        # Use enumerate to get an index for the hotkey number.
        for index, (tower_id, tower_data) in enumerate(valid_tower_items):
            hotkey = index + 1
            self.hotkey_map.append(tower_id)  # Add the ID to our ordered map.

            button_rect = pygame.Rect(current_x, start_y, button_size, button_size)
            button = TowerButton(
                rect=button_rect,
                tower_type_id=tower_id,
                tower_data=tower_data,
                assets_path=self.assets_path,
                hotkey_number=hotkey,  # Pass the number to the button.
            )
            self.build_buttons.append(button)
            current_x += button_size + spacing

    def handle_event(self, event: pygame.event.Event, game_state: "GameState") -> bool:
        """
        Passes events to UI elements and handles resulting actions.
        """
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                self._process_ui_action(action, game_state)
                return True

        mouse_pos = pygame.mouse.get_pos()
        if any(button.rect.collidepoint(mouse_pos) for button in self.build_buttons):
            for button in self.build_buttons:
                action = button.handle_event(event, game_state)
                if action:
                    self._process_ui_action(action, game_state)
            return True

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
            upgrade_id = action.replace("purchase_upgrade_", "")
            tower_id = game_state.selected_entity_id
            path_char = upgrade_id.split("_")[-1][0]
            path_id = f"path_{path_char}"

            if tower_id:
                self.game_manager.purchase_tower_upgrade(tower_id, path_id)
                if self.upgrade_panel:
                    self.upgrade_panel._create_layout()
            else:
                logger.warning(
                    "Upgrade purchased but no tower was selected in GameState."
                )

    def update(self, dt: float, game_state: "GameState"):
        """
        Updates all UI elements, including the dynamic creation and destruction
        of the upgrade panel based on the currently selected entity.
        """
        for button in self.build_buttons:
            button.update(dt, game_state)

        selected_id = game_state.selected_entity_id
        if selected_id:
            if (
                not self.upgrade_panel
                or self.upgrade_panel.tower.entity_id != selected_id
            ):
                selected_tower = next(
                    (t for t in self.game_manager.towers if t.entity_id == selected_id),
                    None,
                )
                if selected_tower:
                    panel_rect = pygame.Rect(self.screen_rect.width - 270, 10, 260, 400)
                    self.upgrade_panel = UpgradePanel(
                        rect=panel_rect,
                        tower=selected_tower,
                        upgrade_manager=self.game_manager.upgrade_manager,
                        game_state=game_state,
                    )
        else:
            if self.upgrade_panel:
                self.upgrade_panel = None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws all managed UI elements."""
        panel_rect = pygame.Rect(
            0, self.screen_rect.bottom - 80, self.screen_rect.width, 80
        )
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 25, 30, 200))
        screen.blit(panel_surf, panel_rect.topleft)

        for button in self.build_buttons:
            button.draw(screen, game_state)

        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
