# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from collections import OrderedDict

from .buttons.tower_button import TowerButton
from .buttons.tab_button import TabButton
from .panels.upgrade_panel import UpgradePanel
from .panels.tower_info_panel import TowerInfoPanel
from .ui_action import UIAction, ActionType

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.game_manager import GameManager

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements, featuring a dynamic, tab-based interface for
    tower selection and informational panels for selected towers.
    """

    def __init__(
        self, screen_rect: pygame.Rect, game_manager: "GameManager", assets_path: Path
    ):
        """
        Initializes the UIManager, discovering categories and building the UI.
        """
        self.screen_rect = screen_rect
        self.game_manager = game_manager
        self.assets_path = assets_path

        self.upgrade_panel: Optional[UpgradePanel] = None
        self.tower_info_panel: Optional[TowerInfoPanel] = None

        self.tower_categories: Dict[str, List[Dict[str, Any]]] = OrderedDict()
        self.category_tabs: List[TabButton] = []
        self.build_buttons: List[TowerButton] = []
        self.hotkey_map: List[str] = []
        self.active_category: Optional[str] = None

        self._discover_and_group_towers()
        self._build_dynamic_ui()

    def set_active_category_by_index(self, index: int):
        """Sets the active tower category tab by its numerical index."""
        category_keys = list(self.tower_categories.keys())
        if 0 <= index < len(category_keys):
            new_category = category_keys[index]
            if self.active_category != new_category:
                self.active_category = new_category
                self._update_tabs_and_buttons()
                logger.debug(f"Switched to category '{new_category}' via hotkey.")

    def cycle_category(self):
        """Cycles to the next available tower category."""
        if not self.active_category or len(self.tower_categories) < 2:
            return
        category_keys = list(self.tower_categories.keys())
        current_index = category_keys.index(self.active_category)
        next_index = (current_index + 1) % len(category_keys)
        self.active_category = category_keys[next_index]
        self._update_tabs_and_buttons()
        logger.debug(f"Cycled to category '{self.active_category}'.")

    def cycle_tower_selection(self, game_state: "GameState"):
        """Cycles the selected tower within the currently active category."""
        if not self.active_category or not self.hotkey_map:
            return
        current_selection = game_state.selected_tower_to_build
        try:
            current_index = self.hotkey_map.index(current_selection)
        except ValueError:
            current_index = -1
        next_index = (current_index + 1) % len(self.hotkey_map)
        new_tower_id = self.hotkey_map[next_index]
        game_state.selected_tower_to_build = new_tower_id
        logger.debug(f"Cycled to select tower '{new_tower_id}'.")

    def _update_tabs_and_buttons(self):
        """A helper method to update tab visuals and rebuild tower buttons."""
        for t in self.category_tabs:
            t.is_active = t.category_name == self.active_category
        self._rebuild_tower_buttons()

    def _discover_and_group_towers(self):
        """Scans tower configs, discovers unique categories, and groups towers."""
        logger.info("Discovering tower categories from configuration...")
        tower_types = self.game_manager.configs.get("tower_types", {})
        ordered_categories = []
        if isinstance(tower_types, dict):
            for data in tower_types.values():
                if isinstance(data, dict):
                    category = data.get("category", "uncategorized")
                    if category not in ordered_categories:
                        ordered_categories.append(category)
        for category in ordered_categories:
            self.tower_categories[category] = []
        if isinstance(tower_types, dict):
            for tower_id, tower_data in tower_types.items():
                if isinstance(tower_data, dict):
                    category = tower_data.get("category", "uncategorized")
                    tower_data_with_id = {"id": tower_id, **tower_data}
                    if category in self.tower_categories:
                        self.tower_categories[category].append(tower_data_with_id)
        self.active_category = ordered_categories[0] if ordered_categories else None
        logger.info(
            f"Discovered categories in order: {list(self.tower_categories.keys())}"
        )

    def _build_dynamic_ui(self):
        """Constructs the tabbed UI layout."""
        self.category_tabs.clear()
        tab_height, tab_width, tab_spacing = 35, 120, 5
        start_x = 20
        start_y = self.screen_rect.bottom - 80 - tab_height
        for category_name in self.tower_categories.keys():
            is_active = category_name == self.active_category
            tab_rect = pygame.Rect(start_x, start_y, tab_width, tab_height)
            self.category_tabs.append(TabButton(tab_rect, category_name, is_active))
            start_x += tab_width + tab_spacing
        self._rebuild_tower_buttons()

    def _rebuild_tower_buttons(self):
        """Rebuilds tower buttons based on the active category."""
        self.build_buttons.clear()
        self.hotkey_map.clear()
        if not self.active_category or not self.tower_categories.get(
            self.active_category
        ):
            return
        button_size, panel_height, spacing = 64, 80, 10
        towers_in_category = self.tower_categories[self.active_category]
        num_buttons = len(towers_in_category)
        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)
        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )
        for index, tower_data in enumerate(towers_in_category):
            tower_id = tower_data["id"]
            self.hotkey_map.append(tower_id)
            rect = pygame.Rect(
                start_x + (button_size + spacing) * index,
                start_y,
                button_size,
                button_size,
            )
            button = TowerButton(
                rect, tower_id, tower_data, self.assets_path, index + 1
            )
            self.build_buttons.append(button)

    def handle_event(self, event: pygame.event.Event, game_state: "GameState") -> bool:
        """Handles events for all UI elements."""
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                self._process_ui_action(action, game_state)
                return True

        if self.tower_info_panel:
            self.tower_info_panel.handle_event(event, game_state)

        if event.type == pygame.MOUSEMOTION:
            for tab in self.category_tabs:
                tab.handle_event(event, game_state)
            for button in self.build_buttons:
                button.handle_event(event, game_state)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab in self.category_tabs:
                if tab.handle_event(event, game_state):
                    if self.active_category != tab.category_name:
                        self.active_category = tab.category_name
                        self._update_tabs_and_buttons()
                    return True
            for button in self.build_buttons:
                action = button.handle_event(event, game_state)
                if action:
                    self._process_ui_action(action, game_state)
                    return True
        return False

    def _process_ui_action(self, action: UIAction, game_state: "GameState"):
        """Processes a structured UIAction from any UI element."""
        match action.type:
            case ActionType.SELECT_TOWER:
                tower_id = action.entity_id
                game_state.selected_tower_to_build = (
                    None if game_state.selected_tower_to_build == tower_id else tower_id
                )
            case ActionType.PURCHASE_UPGRADE:
                tower_id = game_state.selected_entity_id
                upgrade_id = action.entity_id
                if tower_id and upgrade_id:
                    self.game_manager.purchase_tower_upgrade(tower_id, upgrade_id)
                    if self.upgrade_panel:
                        self.upgrade_panel.rebuild_layout()
            case ActionType.CLOSE_PANEL:
                game_state.clear_selection()
            case ActionType.SALVAGE_TOWER:
                if game_state.selected_entity_id:
                    self.game_manager.salvage_tower(game_state.selected_entity_id)
            case ActionType.CHANGE_TARGETING_PERSONA:
                tower_id = game_state.selected_entity_id
                persona_id = action.entity_id
                if tower_id and persona_id:
                    self.game_manager.change_tower_persona(tower_id, persona_id)
                    if self.upgrade_panel:
                        self.upgrade_panel.rebuild_layout()

    def update(self, dt: float, game_state: "GameState"):
        """Updates the state of all UI panels based on the game state."""
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
                    panel_rect = pygame.Rect(self.screen_rect.width - 270, 10, 260, 550)
                    salvage_rate = self.game_manager.get_salvage_rate()
                    self.upgrade_panel = UpgradePanel(
                        rect=panel_rect,
                        tower=selected_tower,
                        upgrade_manager=self.game_manager.upgrade_manager,
                        game_state=game_state,
                        salvage_refund_percentage=salvage_rate,
                        targeting_ai_config=self.game_manager.configs.get(
                            "targeting_ai", {}
                        ),
                    )
        elif self.upgrade_panel:
            self.upgrade_panel = None

        selected_build_id = game_state.selected_tower_to_build
        tower_data_to_display = None
        if selected_build_id:
            for category_towers in self.tower_categories.values():
                for t_data in category_towers:
                    if t_data["id"] == selected_build_id:
                        tower_data_to_display = t_data
                        break
                if tower_data_to_display:
                    break
        if tower_data_to_display:
            if (
                not self.tower_info_panel
                or self.tower_info_panel.tower_data.get("id") != selected_build_id
            ):
                # --- MODIFIED: Create panel with placeholder y-value ---
                panel_width = 260
                panel_rect = pygame.Rect(
                    20, 0, panel_width, 0
                )  # y and height are temporary

                self.tower_info_panel = TowerInfoPanel(
                    rect=panel_rect,
                    tower_data=tower_data_to_display,
                    targeting_ai_config=self.game_manager.configs.get(
                        "targeting_ai", {}
                    ),
                )

                # --- MODIFIED: Reposition the panel based on its new dynamic height ---
                self.tower_info_panel.rect.y = (
                    self.screen_rect.bottom
                    - 80
                    - 35
                    - self.tower_info_panel.rect.height
                    - 10
                )

        elif self.tower_info_panel:
            self.tower_info_panel = None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws all UI components in the correct order."""
        panel_rect = pygame.Rect(
            0, self.screen_rect.bottom - 80, self.screen_rect.width, 80
        )
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 25, 30, 200))
        screen.blit(panel_surf, panel_rect.topleft)
        for tab in self.category_tabs:
            tab.draw(screen)
        for button in self.build_buttons:
            button.draw(screen, game_state)
        if self.tower_info_panel:
            self.tower_info_panel.draw(screen)
        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
