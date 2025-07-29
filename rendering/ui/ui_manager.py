# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from collections import OrderedDict

from .buttons.tower_button import TowerButton
from .buttons.tab_button import TabButton
from .panels.upgrade_panel import UpgradePanel
from .ui_action import UIAction, ActionType

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.game_manager import GameManager

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements, featuring a dynamic, tab-based interface for
    tower selection that is automatically generated and fully navigable
    via keyboard shortcuts.
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
        self.tower_categories: Dict[str, List[Dict[str, Any]]] = OrderedDict()
        self.category_tabs: List[TabButton] = []
        self.build_buttons: List[TowerButton] = []
        self.hotkey_map: List[str] = []
        self.active_category: Optional[str] = None

        self._discover_and_group_towers()
        self._build_dynamic_ui()

    # --- NEW: Public methods for keyboard navigation ---

    def set_active_category_by_index(self, index: int):
        """
        Sets the active tower category tab by its numerical index.
        Called by the Game class in response to F-key or Ctrl+Num hotkeys.
        """
        category_keys = list(self.tower_categories.keys())
        if 0 <= index < len(category_keys):
            new_category = category_keys[index]
            if self.active_category != new_category:
                self.active_category = new_category
                self._update_tabs_and_buttons()
                logger.debug(f"Switched to category '{new_category}' via hotkey.")

    def cycle_category(self):
        """
        Cycles to the next available tower category.
        Called by the Game class in response to Ctrl+Tab.
        """
        if not self.active_category or len(self.tower_categories) < 2:
            return

        category_keys = list(self.tower_categories.keys())
        current_index = category_keys.index(self.active_category)
        next_index = (current_index + 1) % len(category_keys)
        self.active_category = category_keys[next_index]
        self._update_tabs_and_buttons()
        logger.debug(f"Cycled to category '{self.active_category}'.")

    def cycle_tower_selection(self, game_state: "GameState"):
        """
        Cycles the selected tower within the currently active category.
        Called by the Game class in response to Tab.
        """
        if not self.active_category or not self.hotkey_map:
            return

        current_selection = game_state.selected_tower_to_build
        try:
            current_index = self.hotkey_map.index(current_selection)
        except ValueError:
            current_index = -1  # Nothing is selected, so start from the beginning

        next_index = (current_index + 1) % len(self.hotkey_map)
        new_tower_id = self.hotkey_map[next_index]
        game_state.selected_tower_to_build = new_tower_id
        logger.debug(f"Cycled to select tower '{new_tower_id}'.")

    # --- Internal UI building and handling methods ---

    def _update_tabs_and_buttons(self):
        """A helper method to update tab visuals and rebuild tower buttons."""
        for t in self.category_tabs:
            t.is_active = t.category_name == self.active_category
        self._rebuild_tower_buttons()

    def _discover_and_group_towers(self):
        """
        Scans tower configs, discovers unique categories in order, and groups towers.
        """
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
        tab_height = 35
        tab_width = 120
        tab_spacing = 5
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
        # Handle upgrade panel events first, as it's typically on top
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                self._process_ui_action(action, game_state)
                return True  # Event handled by panel, no need to process further

        # --- NEU: MOUSEMOTION für ALLE Elemente verarbeiten, um den Hover-Zustand zu aktualisieren ---
        # Dies muss VOR jeglicher Klick-Logik geschehen, die die Verarbeitung abbrechen könnte.
        if event.type == pygame.MOUSEMOTION:
            for tab in self.category_tabs:
                # `handle_event` in `TabButton` aktualisiert `is_hovered` basierend auf `event.pos`
                tab.handle_event(event, game_state)
            for button in self.build_buttons:
                # `handle_event` in `TowerButton` aktualisiert `is_hovered` basierend auf `event.pos`
                button.handle_event(event, game_state)
            # Hier kein `return True`, da wir wollen, dass alle Elemente ihren Hover-Zustand aktualisieren.

        # --- MOUSEBUTTONDOWN-Ereignisse separat verarbeiten ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Tabs auf Klicks prüfen
            for tab in self.category_tabs:
                # `handle_event` in `TabButton` gibt True zurück, wenn geklickt
                if tab.handle_event(
                    event
                ):  # Kein `collidepoint` hier, da `handle_event` das intern macht
                    if self.active_category != tab.category_name:
                        self.active_category = tab.category_name
                        self._update_tabs_and_buttons()
                    return True  # Ereignis behandelt

            # Bau-Buttons auf Klicks prüfen
            for button in self.build_buttons:
                # `handle_event` in `TowerButton` gibt eine `UIAction` zurück, wenn geklickt
                action = button.handle_event(
                    event, game_state
                )  # Kein `collidepoint` hier
                if action:
                    self._process_ui_action(action, game_state)
                    return True  # Ereignis behandelt

        return False  # Ereignis wurde von keinem UI-Element behandelt

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
                    path_char = upgrade_id.split("_")[-1][0]
                    path_id = f"path_{path_char}"
                    self.game_manager.purchase_tower_upgrade(tower_id, path_id)
                    self.upgrade_panel = None
            case ActionType.CLOSE_PANEL:
                game_state.clear_selection()
            case ActionType.SALVAGE_TOWER:
                if game_state.selected_entity_id:
                    self.game_manager.salvage_tower(game_state.selected_entity_id)

    def update(self, dt: float, game_state: "GameState"):
        """Updates the state of the upgrade panel."""
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
                    salvage_rate = (
                        self.game_manager.wave_manager.difficulty_settings.get(
                            "salvage_refund_percentage", 0.0
                        )
                        if self.game_manager.wave_manager
                        else 0.0
                    )
                    self.upgrade_panel = UpgradePanel(
                        panel_rect,
                        selected_tower,
                        self.game_manager.upgrade_manager,
                        game_state,
                        salvage_rate,
                    )
        elif self.upgrade_panel:
            self.upgrade_panel = None

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
        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
