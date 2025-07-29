# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING

# --- New, Structured Imports ---
from .buttons.tower_button import TowerButton
from .panels.upgrade_panel import UpgradePanel

# --- MODIFIED: Import the new structured action classes ---
# We now import our action vocabulary to process the structured commands
# received from all other UI elements.
from .ui_action import UIAction, ActionType

# Use TYPE_CHECKING for type hinting to avoid circular imports at runtime.
if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.game_manager import GameManager
    from game_logic.entities.tower import Tower

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements, including the static build panel and the dynamic
    tower upgrade panel. It processes structured UIAction objects to modify
    the game state, providing a robust and decoupled event system.
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

        self.build_buttons: List[TowerButton] = []
        self.upgrade_panel: Optional[UpgradePanel] = None
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

        valid_tower_items = [
            (tower_id, tower_data)
            for tower_id, tower_data in tower_types.items()
            if isinstance(tower_data, dict)
        ]

        num_buttons = len(valid_tower_items)
        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)
        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )

        current_x = start_x
        for index, (tower_id, tower_data) in enumerate(valid_tower_items):
            hotkey = index + 1
            self.hotkey_map.append(tower_id)

            button_rect = pygame.Rect(current_x, start_y, button_size, button_size)
            button = TowerButton(
                rect=button_rect,
                tower_type_id=tower_id,
                tower_data=tower_data,
                assets_path=self.assets_path,
                hotkey_number=hotkey,
            )
            self.build_buttons.append(button)
            current_x += button_size + spacing

    def handle_event(self, event: pygame.event.Event, game_state: "GameState") -> bool:
        """
        Passes events to UI elements and handles resulting actions.
        The UI has priority; if it handles an event, it returns True to stop
        further processing by the main game window.
        """
        # --- MODIFIED: Event handling now expects UIAction objects ---
        # The logic remains the same, but the 'action' variable is now a
        # structured UIAction object, not a string.
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                self._process_ui_action(action, game_state)
                return True

        mouse_pos = pygame.mouse.get_pos()
        if (
            self.build_buttons
            and self.build_buttons[0].rect.y
            <= mouse_pos[1]
            <= self.build_buttons[0].rect.bottom
        ):
            for button in self.build_buttons:
                if button.rect.collidepoint(mouse_pos):
                    action = button.handle_event(event, game_state)
                    if action:
                        self._process_ui_action(action, game_state)
                        return True

        return False

    def _process_ui_action(self, action: UIAction, game_state: "GameState"):
        """
        Updates the game state based on a structured UIAction command.
        This method is now much cleaner and more robust than its string-based
        predecessor, using pattern matching on the action type.
        """
        # --- MODIFIED: Replaced string parsing with a match statement ---
        match action.type:
            case ActionType.SELECT_TOWER:
                tower_id = action.entity_id
                if game_state.selected_tower_to_build == tower_id:
                    game_state.clear_selection()
                else:
                    game_state.selected_tower_to_build = tower_id
                    logger.info(f"Player selected '{tower_id}' for building.")

            case ActionType.PURCHASE_UPGRADE:
                upgrade_id = action.entity_id
                tower_id = game_state.selected_entity_id

                if tower_id and upgrade_id:
                    # Note: Game logic is untouched as per the rules.
                    path_char = upgrade_id.split("_")[-1][0]
                    path_id = f"path_{path_char}"
                    self.game_manager.purchase_tower_upgrade(tower_id, path_id)
                    self.upgrade_panel = None  # Close panel after upgrade
                else:
                    logger.warning(
                        "Upgrade action received but missing tower or upgrade ID."
                    )

            case ActionType.CLOSE_PANEL:
                game_state.clear_selection()

            case ActionType.SALVAGE_TOWER:
                tower_id = game_state.selected_entity_id
                if tower_id:
                    self.game_manager.salvage_tower(tower_id)
                else:
                    logger.warning("Salvage action received but no tower was selected.")

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

                    salvage_rate = 0.0
                    if self.game_manager.wave_manager:
                        salvage_rate = (
                            self.game_manager.wave_manager.difficulty_settings.get(
                                "salvage_refund_percentage", 0.0
                            )
                        )

                    self.upgrade_panel = UpgradePanel(
                        rect=panel_rect,
                        tower=selected_tower,
                        upgrade_manager=self.game_manager.upgrade_manager,
                        game_state=game_state,
                        salvage_refund_percentage=salvage_rate,
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
