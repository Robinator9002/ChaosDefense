# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from collections import OrderedDict

from .buttons.tower_button import TowerButton
from .panels.upgrade_panel import UpgradePanel
from .ui_action import UIAction, ActionType

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.game_manager import GameManager

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements. This version has been refactored to dynamically
    discover and group towers by category, preparing for a tab-based UI.
    """

    def __init__(
        self, screen_rect: pygame.Rect, game_manager: "GameManager", assets_path: Path
    ):
        """
        Initializes the UIManager, discovering tower categories automatically.
        """
        self.screen_rect = screen_rect
        self.game_manager = game_manager
        self.assets_path = assets_path

        # --- UI Component Storage ---
        self.build_buttons: List[TowerButton] = []
        self.upgrade_panel: Optional[UpgradePanel] = None
        self.hotkey_map: List[str] = []

        # --- NEW: Automated Category Discovery and Storage ---
        # This dictionary will store towers grouped by their category.
        # e.g., {"military": [turret_data, cannon_data], "support": [...]}
        self.tower_categories: Dict[str, List[Dict[str, Any]]] = OrderedDict()
        self._discover_and_group_towers()

        # The active category determines which tower buttons are shown.
        self.active_category: Optional[str] = (
            next(iter(self.tower_categories)) if self.tower_categories else None
        )

        # This method will be completely replaced in the next phase, but for
        # now, we call it to maintain existing functionality.
        self._create_tower_build_panel()

    def _discover_and_group_towers(self):
        """
        Scans the loaded tower configurations, discovers all unique categories,
        and groups the tower data accordingly. This is the core of the
        automated UI system.
        """
        logger.info("Discovering tower categories from configuration...")
        tower_types = self.game_manager.configs.get("tower_types", {})

        # First, find all unique categories to establish a consistent order.
        # Using a set handles uniqueness automatically.
        categories = sorted(
            list(
                {
                    data.get("category", "uncategorized")
                    for data in tower_types.values()
                    if isinstance(data, dict)
                }
            )
        )

        # Initialize the ordered dictionary with empty lists for each category.
        for category in categories:
            self.tower_categories[category] = []

        # Now, populate the lists with the corresponding tower data.
        for tower_id, tower_data in tower_types.items():
            if isinstance(tower_data, dict):
                category = tower_data.get("category", "uncategorized")
                # Add the tower's ID to its data dict for easy access.
                tower_data_with_id = {"id": tower_id, **tower_data}
                if category in self.tower_categories:
                    self.tower_categories[category].append(tower_data_with_id)

        logger.info(f"Discovered categories: {list(self.tower_categories.keys())}")

    def _create_tower_build_panel(self):
        """
        Creates and positions the tower selection buttons.
        NOTE: This method will be completely overhauled in the next phase to
        create tabs and dynamically display buttons for the active category.
        For now, it just loads all towers to keep the game running.
        """
        logger.info("Creating temporary tower build UI panel.")
        button_size = 64
        panel_height = 80
        spacing = 10

        # Temporary: Flatten all towers from all categories for display.
        all_towers = [
            tower for towers in self.tower_categories.values() for tower in towers
        ]
        num_buttons = len(all_towers)

        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)
        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )

        current_x = start_x
        for index, tower_data in enumerate(all_towers):
            hotkey = index + 1
            tower_id = tower_data["id"]
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
        """
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
        """
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
                    path_char = upgrade_id.split("_")[-1][0]
                    path_id = f"path_{path_char}"
                    self.game_manager.purchase_tower_upgrade(tower_id, path_id)
                    self.upgrade_panel = None
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
