# rendering/hud/ui_manager.py
import pygame
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from rendering.common.ui.ui_action import UIAction, ActionType
from .buttons.tower_button import TowerButton
from .buttons.upgrade_button import UpgradeButton
from .panels.upgrade_panel import UpgradePanel
from .panels.tower_info_panel import TowerInfoPanel
from .panels.persona_selection_panel import PersonaSelectionPanel
from .buttons.tab_button import TabButton

if TYPE_CHECKING:
    from game_logic.game_manager import GameManager
    from game_logic.progression.progression_manager import ProgressionManager
    from game_logic.game_state import GameState
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all in-game Heads-Up Display (HUD) and interactive UI elements.
    It acts as a central hub for event handling, drawing, and state
    management for the UI.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        game_manager: "GameManager",
        progression_manager: "ProgressionManager",
        assets_path: Path,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        self.screen_rect = screen_rect
        self.game_manager = game_manager
        self.progression_manager = progression_manager
        self.assets_path = assets_path
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.hud_panel_height = self.layout.get("hud_panel_height", 80)

        self.tower_buttons: List[TowerButton] = []
        self.tab_buttons: List[TabButton] = []
        self.active_tab: str = "basic"

        self.info_panel: Optional[TowerInfoPanel] = None
        self.upgrade_panel: Optional[UpgradePanel] = None
        self.persona_panel: Optional[PersonaSelectionPanel] = None

        self._build_static_ui()
        self._build_dynamic_ui()

    def _build_static_ui(self):
        """Builds UI elements that don't change during gameplay."""
        # This can include the bottom panel, etc.
        pass

    def _build_dynamic_ui(self):
        """Builds UI elements that depend on game state, like tower buttons."""
        self._rebuild_tower_buttons()

    def _rebuild_tower_buttons(self):
        """
        Rebuilds the tower buttons based on available tower types.
        This method is now correctly placed to ensure that the buttons
        are created and styled before they are drawn.
        """
        self.tower_buttons.clear()
        self.tab_buttons.clear()

        # Get all tower types that can be built
        buildable_tower_ids = self.game_manager.get_buildable_towers()
        # --- FIX: Use self.game_manager.configs instead of .all_configs ---
        all_tower_configs = self.game_manager.configs.get("tower_types", {})
        targeting_ai_config = self.game_manager.configs.get("targeting_ai", {})

        # Categorize towers for tabs
        categories = sorted(
            list(
                set(
                    all_tower_configs.get(t_id, {}).get("category", "basic")
                    for t_id in buildable_tower_ids
                )
            )
        )
        categories.insert(0, "all")
        logger.info(f"Final buildable categories: {categories}")

        # Create tab buttons
        tab_button_width = 80
        tab_button_height = 30
        tab_x_start = (
            self.screen_rect.centerx - (len(categories) * tab_button_width) // 2
        )
        for i, category in enumerate(categories):
            rect = pygame.Rect(
                tab_x_start + i * tab_button_width,
                self.screen_rect.bottom - self.hud_panel_height - tab_button_height - 5,
                tab_button_width,
                tab_button_height,
            )
            is_active = category == self.active_tab
            self.tab_buttons.append(
                TabButton(rect, category, is_active, self.ui_theme, self.font_manager)
            )

        # Filter towers based on active tab
        filtered_tower_ids = [
            t_id
            for t_id in buildable_tower_ids
            if self.active_tab == "all"
            or all_tower_configs.get(t_id, {}).get("category") == self.active_tab
        ]

        # Create tower buttons for the filtered list
        button_size = 64
        button_spacing = 15
        num_buttons_per_row = (self.screen_rect.width - 2 * button_spacing) // (
            button_size + button_spacing
        )

        start_x = (
            self.screen_rect.centerx
            - (num_buttons_per_row * (button_size + button_spacing) - button_spacing)
            // 2
        )

        for i, tower_id in enumerate(filtered_tower_ids):
            tower_data = all_tower_configs.get(tower_id, {})
            row = i // num_buttons_per_row
            col = i % num_buttons_per_row
            x = start_x + col * (button_size + button_spacing)
            y = (
                self.screen_rect.bottom
                - self.hud_panel_height
                + button_spacing
                + row * (button_size + button_spacing)
            )

            button = TowerButton(
                pygame.Rect(x, y, button_size, button_size),
                tower_id,
                tower_data,
                self.assets_path,
                i + 1,  # Hotkey number
                self.ui_theme,
                self.font_manager,
            )
            self.tower_buttons.append(button)

    def _open_upgrade_panel(self, tower_id: str):
        """Opens the upgrade panel for a selected tower."""
        tower = self.game_manager.towers.get(tower_id)
        if tower:
            panel_width = self.screen_rect.width * 0.25
            panel_rect = pygame.Rect(
                self.screen_rect.right
                - panel_width
                - self.layout.get("padding_medium", 15),
                self.screen_rect.y + self.layout.get("padding_medium", 15),
                panel_width,
                self.screen_rect.height * 0.9,
            )
            self.upgrade_panel = UpgradePanel(
                panel_rect,
                tower,
                self.game_manager.configs["tower_types"].get(tower.tower_type_id),
                self.game_manager.upgrade_manager,
                self.game_manager.game_state,
                self.game_manager.game_settings.get("salvage_refund_percentage", 0.5),
                self.game_manager.configs.get("targeting_ai", {}),
                self.ui_theme,
                self.font_manager,
            )

    def _close_panel(self):
        """Closes the currently active panel (upgrade or info)."""
        self.info_panel = None
        self.upgrade_panel = None

    def _open_persona_panel(self):
        """Opens the persona selection modal."""
        if self.upgrade_panel and self.upgrade_panel.tower:
            tower = self.upgrade_panel.tower
            all_personas = self.game_manager.configs.get("targeting_ai", {})
            eligible_personas = tower.get_eligible_personas(all_personas)
            active_persona = tower.current_persona
            self.persona_panel = PersonaSelectionPanel(
                self.screen_rect,
                all_personas,
                eligible_personas,
                active_persona,
                self.ui_theme,
                self.font_manager,
            )

    def _close_persona_panel(self):
        """Closes the persona selection modal."""
        self.persona_panel = None

    def _change_persona(self, persona_id: str):
        """Changes the persona for the selected tower."""
        if self.upgrade_panel and self.upgrade_panel.tower:
            self.game_manager.change_tower_persona(
                self.upgrade_panel.tower.entity_id, persona_id
            )
            self._close_persona_panel()

    def on_resize(self, new_screen_rect: pygame.Rect):
        """Handles screen resize events."""
        self.screen_rect = new_screen_rect
        self.hud_panel_height = self.layout.get("hud_panel_height", 80)
        self._rebuild_tower_buttons()
        if self.info_panel:
            self.info_panel.on_resize(new_screen_rect)
        if self.upgrade_panel:
            self.upgrade_panel.on_resize(new_screen_rect)
        if self.persona_panel:
            self.persona_panel.on_resize(new_screen_rect)

    def handle_event(self, event: pygame.event.Event, game_state: "GameState") -> bool:
        """Processes Pygame events for the UI."""
        # Prioritize modal panels and overlays
        if self.persona_panel:
            action = self.persona_panel.handle_event(event, game_state)
            if action:
                if action.type == ActionType.CLOSE_PERSONA_PANEL:
                    self._close_persona_panel()
                elif action.type == ActionType.CHANGE_TARGETING_PERSONA:
                    self._change_persona(action.entity_id)
                return True
            return self.persona_panel.rect.collidepoint(pygame.mouse.get_pos())

        # Then, handle the upgrade panel
        if self.upgrade_panel:
            action = self.upgrade_panel.handle_event(event, game_state)
            if action:
                if action.type == ActionType.CLOSE_PANEL:
                    self._close_panel()
                elif action.type == ActionType.SALVAGE_TOWER:
                    self.game_manager.salvage_tower(self.upgrade_panel.tower.entity_id)
                    self._close_panel()
                elif action.type == ActionType.PURCHASE_UPGRADE:
                    self.game_manager.purchase_tower_upgrade(
                        self.upgrade_panel.tower.entity_id, action.entity_id
                    )
                    self.upgrade_panel.rebuild_layout()
                elif action.type == ActionType.OPEN_PERSONA_PANEL:
                    self._open_persona_panel()
                return True
            return self.upgrade_panel.rect.collidepoint(pygame.mouse.get_pos())

        # Then, handle the info panel
        if self.info_panel:
            # We don't have a handle_event for info_panel as it is passive, but we check if it is clicked on
            # to prevent events from propagating to the background.
            if self.info_panel.rect.collidepoint(pygame.mouse.get_pos()):
                return True
            self.info_panel = None

        # Finally, handle main HUD elements
        for button in self.tab_buttons:
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and button.rect.collidepoint(event.pos)
            ):
                self.active_tab = button.category_name.lower()
                self._rebuild_tower_buttons()
                return True
            button.is_hovered = button.rect.collidepoint(pygame.mouse.get_pos())

        for button in self.tower_buttons:
            action = button.handle_event(event, game_state)
            if action:
                if action.type == ActionType.SELECT_TOWER:
                    game_state.selected_tower_to_build = action.entity_id
                    tower_data = self.game_manager.configs["tower_types"].get(
                        action.entity_id
                    )
                    # Open the info panel for the selected tower type
                    panel_width = self.screen_rect.width * 0.25
                    panel_rect = pygame.Rect(
                        self.screen_rect.right
                        - panel_width
                        - self.layout.get("padding_medium", 15),
                        self.screen_rect.y + self.layout.get("padding_medium", 15),
                        panel_width,
                        self.screen_rect.height * 0.9,
                    )
                    self.info_panel = TowerInfoPanel(
                        panel_rect,
                        tower_data,
                        self.game_manager.configs.get("targeting_ai", {}),
                        self.ui_theme,
                        self.font_manager,
                    )
                return True

        return False

    def update(self, dt: float, game_state: "GameState"):
        """Updates the state of all managed UI elements."""
        if self.persona_panel:
            self.persona_panel.update(dt, game_state)
        elif self.upgrade_panel:
            self.upgrade_panel.update(dt, game_state)
        for button in self.tower_buttons:
            button.update(dt, game_state)

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws all UI elements to the screen."""
        # Draw main HUD panel background
        panel_rect = pygame.Rect(
            0,
            self.screen_rect.height - self.hud_panel_height,
            self.screen_rect.width,
            self.hud_panel_height,
        )
        panel_color = self.colors.get("panel_primary", [25, 30, 40])
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        # --- FIX: Convert list to tuple before adding alpha ---
        panel_surf.fill(tuple(panel_color) + (200,))
        screen.blit(panel_surf, panel_rect.topleft)

        # Draw buttons and other elements on the main panel
        for button in self.tower_buttons:
            button.draw(screen, game_state)
        for button in self.tab_buttons:
            button.draw(screen)

        # Draw panels, with upgrade panel having priority over info panel
        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
        elif self.info_panel:
            self.info_panel.draw(screen)

        # Persona panel is a modal and should be drawn last
        if self.persona_panel:
            self.persona_panel.draw(screen)
