# rendering/ui/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from collections import OrderedDict

# --- MODIFIED: Import the new TabButton class ---
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
    tower selection that is automatically generated from game configurations.
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

        # --- UI State and Component Storage ---
        self.upgrade_panel: Optional[UpgradePanel] = None
        self.tower_categories: Dict[str, List[Dict[str, Any]]] = OrderedDict()
        self.category_tabs: List[TabButton] = []
        self.build_buttons: List[TowerButton] = []
        self.hotkey_map: List[str] = []
        self.active_category: Optional[str] = None

        # --- Build the UI ---
        self._discover_and_group_towers()
        self._build_dynamic_ui()

    def _discover_and_group_towers(self):
        """
        Scans tower configs, discovers unique categories, and groups towers.
        """
        logger.info("Discovering tower categories from configuration...")
        tower_types = self.game_manager.configs.get("tower_types", {})

        categories = sorted(
            list(
                {
                    data.get("category", "uncategorized")
                    for data in tower_types.values()
                    if isinstance(data, dict)
                }
            )
        )

        for category in categories:
            self.tower_categories[category] = []

        for tower_id, tower_data in tower_types.items():
            if isinstance(tower_data, dict):
                category = tower_data.get("category", "uncategorized")
                tower_data_with_id = {"id": tower_id, **tower_data}
                if category in self.tower_categories:
                    self.tower_categories[category].append(tower_data_with_id)

        self.active_category = categories[0] if categories else None
        logger.info(f"Discovered categories: {list(self.tower_categories.keys())}")

    def _build_dynamic_ui(self):
        """
        Constructs the entire tabbed UI layout, including tabs and tower buttons.
        """
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

        # Initial build of tower buttons for the default active category.
        self._rebuild_tower_buttons()

    def _rebuild_tower_buttons(self):
        """
        Clears and rebuilds the tower buttons based on the active category.
        This is the core of the dynamic UI.
        """
        self.build_buttons.clear()
        self.hotkey_map.clear()

        if not self.active_category or not self.tower_categories.get(
            self.active_category
        ):
            return

        logger.debug(f"Rebuilding tower buttons for category: '{self.active_category}'")
        button_size = 64
        panel_height = 80
        spacing = 10

        towers_in_category = self.tower_categories[self.active_category]
        num_buttons = len(towers_in_category)

        total_width = (num_buttons * button_size) + ((num_buttons - 1) * spacing)
        start_x = self.screen_rect.centerx - (total_width / 2)
        start_y = (
            self.screen_rect.bottom - panel_height + (panel_height - button_size) / 2
        )

        current_x = start_x
        for index, tower_data in enumerate(towers_in_category):
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
        Handles events for all UI elements, prioritizing tabs, then buttons.
        """
        # 1. Handle Upgrade Panel first, as it's an overlay.
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                self._process_ui_action(action, game_state)
                return True

        # --- BUG FIX: Guard against non-mouse events ---
        # Only check for mouse collisions if the event is a mouse event.
        # This prevents the AttributeError when trying to access 'event.pos'
        # on events like KEYDOWN, which have no mouse position.
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            # 2. Handle Tab Buttons.
            for tab in self.category_tabs:
                if tab.rect.collidepoint(event.pos):
                    if tab.handle_event(event):  # handle_event returns True on click
                        if self.active_category != tab.category_name:
                            self.active_category = tab.category_name
                            # Update active state for all tabs
                            for t in self.category_tabs:
                                t.is_active = t.category_name == self.active_category
                            self._rebuild_tower_buttons()
                        return True  # Consume the event

            # 3. Handle Tower Buttons.
            for button in self.build_buttons:
                if button.rect.collidepoint(event.pos):
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
                if game_state.selected_tower_to_build == tower_id:
                    game_state.clear_selection()
                else:
                    game_state.selected_tower_to_build = tower_id
            case ActionType.PURCHASE_UPGRADE:
                upgrade_id = action.entity_id
                tower_id = game_state.selected_entity_id
                if tower_id and upgrade_id:
                    path_char = upgrade_id.split("_")[-1][0]
                    path_id = f"path_{path_char}"
                    self.game_manager.purchase_tower_upgrade(tower_id, path_id)
                    self.upgrade_panel = None
            case ActionType.CLOSE_PANEL:
                game_state.clear_selection()
            case ActionType.SALVAGE_TOWER:
                tower_id = game_state.selected_entity_id
                if tower_id:
                    self.game_manager.salvage_tower(tower_id)

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
        # Draw main panel background
        panel_rect = pygame.Rect(
            0, self.screen_rect.bottom - 80, self.screen_rect.width, 80
        )
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 25, 30, 200))
        screen.blit(panel_surf, panel_rect.topleft)

        # Draw category tabs
        for tab in self.category_tabs:
            tab.draw(screen)

        # Draw tower buttons for the active category
        for button in self.build_buttons:
            button.draw(screen, game_state)

        # Draw upgrade panel if one is active
        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
