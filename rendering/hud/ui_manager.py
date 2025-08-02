# rendering/hud/ui_manager.py
import pygame
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from collections import OrderedDict

from .buttons.tower_button import TowerButton
from .buttons.tab_button import TabButton
from .panels.upgrade_panel import UpgradePanel
from .panels.tower_info_panel import TowerInfoPanel
from .panels.persona_selection_panel import PersonaSelectionPanel
from rendering.common.ui.ui_action import UIAction, ActionType

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from game_logic.game_manager import GameManager
    from game_logic.progression.progression_manager import ProgressionManager
    from rendering.text.font_manager import FontManager
    from rendering.common.tooltips import TooltipManager

logger = logging.getLogger(__name__)


class UIManager:
    """
    Manages all UI elements, featuring a dynamic, tab-based interface for
    tower selection and informational panels for selected towers.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        game_manager: "GameManager",
        progression_manager: "ProgressionManager",
        tooltip_manager: "TooltipManager",
        assets_path: Path,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        self.screen_rect = screen_rect
        self.game_manager = game_manager
        self.progression_manager = progression_manager
        self.tooltip_manager = tooltip_manager
        self.assets_path = assets_path
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.hud_panel_height = self.layout.get("hud_panel_height", 80)

        self.tower_buttons: List[TowerButton] = []
        self.tab_buttons: List[TabButton] = []
        self.active_tab: str = "all"
        self.hotkey_map: List[str] = []

        self.info_panel: Optional[TowerInfoPanel] = None
        self.upgrade_panel: Optional[UpgradePanel] = None
        self.persona_panel: Optional[PersonaSelectionPanel] = None
        self.hovered_tower_button: Optional[TowerButton] = None

        self._build_static_ui()
        self._build_dynamic_ui()

    def _build_static_ui(self):
        pass

    def _build_dynamic_ui(self):
        self._rebuild_tower_buttons()

    def _rebuild_tower_buttons(self):
        self.tower_buttons.clear()
        self.tab_buttons.clear()
        self.hotkey_map.clear()

        buildable_tower_ids = self.game_manager.get_buildable_towers()
        all_tower_configs = self.game_manager.configs.get("tower_types", {})

        canonical_category_order = []
        for tower_id, config in all_tower_configs.items():
            if isinstance(config, dict):
                category = config.get("category")
                if category and category not in canonical_category_order:
                    canonical_category_order.append(category)

        available_categories_set = set()
        for t_id in buildable_tower_ids:
            if isinstance(tower_data := all_tower_configs.get(t_id), dict):
                available_categories_set.add(tower_data.get("category", "basic"))

        sorted_available_categories = sorted(
            list(available_categories_set),
            key=lambda cat: (
                canonical_category_order.index(cat)
                if cat in canonical_category_order
                else float("inf")
            ),
        )
        categories = ["all"] + sorted_available_categories

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

        filtered_tower_ids = []
        for t_id in buildable_tower_ids:
            tower_data = all_tower_configs.get(t_id, {})
            if isinstance(tower_data, dict):
                if (
                    self.active_tab == "all"
                    or tower_data.get("category") == self.active_tab
                ):
                    filtered_tower_ids.append(t_id)

        self.hotkey_map = filtered_tower_ids
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
                i + 1,
                self.ui_theme,
                self.font_manager,
            )
            self.tower_buttons.append(button)

    def set_active_category_by_index(self, index: int):
        if index < 0 or index >= len(self.tab_buttons):
            logger.warning(f"Hotkey index {index} is out of range. Ignoring.")
            return
        self.active_tab = self.tab_buttons[index].category_name
        self._rebuild_tower_buttons()
        logger.info(f"Active category changed to: {self.active_tab}")

    def select_tower_by_hotkey(self, index: int, game_state: "GameState"):
        if 0 <= index < len(self.hotkey_map):
            tower_id = self.hotkey_map[index]
            if game_state.selected_tower_to_build == tower_id:
                game_state.clear_selection()
            else:
                game_state.selected_tower_to_build = tower_id
                logger.info(f"Player selected '{tower_id}' via hotkey {index + 1}.")

    def _open_upgrade_panel(self, tower_id: uuid.UUID):
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
                rect=panel_rect,
                tower=tower,
                tower_base_data=self.game_manager.configs["tower_types"].get(
                    tower.tower_type_id
                ),
                upgrade_manager=self.game_manager.upgrade_manager,
                game_state=self.game_manager.game_state,
                salvage_refund_percentage=self.game_manager.game_settings.get(
                    "salvage_refund_percentage", 0.5
                ),
                targeting_ai_config=self.game_manager.configs.get("targeting_ai", {}),
                ui_theme=self.ui_theme,
                font_manager=self.font_manager,
                tooltip_manager=self.tooltip_manager,
            )

    def _open_info_panel(self, tower_id: str):
        tower_data = self.game_manager.configs["tower_types"].get(tower_id)
        if tower_data:
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
                rect=panel_rect,
                tower_data=tower_data,
                targeting_ai_config=self.game_manager.configs.get("targeting_ai", {}),
                ui_theme=self.ui_theme,
                font_manager=self.font_manager,
                tooltip_manager=self.tooltip_manager,
            )

    def _close_panel(self):
        self.info_panel = None
        self.upgrade_panel = None

    def _open_persona_panel(self):
        if self.upgrade_panel and self.upgrade_panel.tower:
            tower = self.upgrade_panel.tower
            all_personas = self.game_manager.configs.get("targeting_ai", {})
            eligible_personas = tower.get_eligible_personas(all_personas)
            active_persona = tower.current_persona
            self.persona_panel = PersonaSelectionPanel(
                screen_rect=self.screen_rect,
                all_personas=all_personas,
                eligible_personas=eligible_personas,
                active_persona=active_persona,
                ui_theme=self.ui_theme,
                font_manager=self.font_manager,
                tooltip_manager=self.tooltip_manager,
            )

    def _close_persona_panel(self):
        self.persona_panel = None

    def _change_persona(self, persona_id: str):
        if self.upgrade_panel and self.upgrade_panel.tower:
            self.game_manager.change_tower_persona(
                self.upgrade_panel.tower.entity_id, persona_id
            )
            self._close_persona_panel()

    def on_resize(self, new_screen_rect: pygame.Rect):
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
        if self.persona_panel:
            action = self.persona_panel.handle_event(event, game_state)
            if action:
                if action.type == ActionType.CLOSE_PERSONA_PANEL:
                    self._close_persona_panel()
                elif action.type == ActionType.CHANGE_TARGETING_PERSONA:
                    self._change_persona(action.entity_id)
                return True
            if hasattr(event, "pos"):
                return self.persona_panel.rect.collidepoint(event.pos)
            return False

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
            if hasattr(event, "pos"):
                return self.upgrade_panel.rect.collidepoint(event.pos)
            return False

        if self.info_panel:
            if hasattr(event, "pos") and self.info_panel.rect.collidepoint(event.pos):
                return True

        for button in self.tab_buttons:
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and button.rect.collidepoint(event.pos)
            ):
                self.active_tab = button.category_name.lower()
                self._rebuild_tower_buttons()
                return True
            if hasattr(event, "pos"):
                button.is_hovered = button.rect.collidepoint(event.pos)

        for button in self.tower_buttons:
            action = button.handle_event(event, game_state)
            if action:
                if action.type == ActionType.SELECT_TOWER:
                    game_state.selected_tower_to_build = action.entity_id
                return True
        return False

    def update(self, dt: float, game_state: "GameState"):
        if game_state.selected_entity_id:
            if (
                not self.upgrade_panel
                or self.upgrade_panel.tower.entity_id != game_state.selected_entity_id
            ):
                self._close_panel()
                self._open_upgrade_panel(game_state.selected_entity_id)

        elif game_state.selected_tower_to_build:
            if not self.info_panel or self.info_panel.tower_data.get(
                "name"
            ) != self.game_manager.configs["tower_types"][
                game_state.selected_tower_to_build
            ].get(
                "name"
            ):
                self._close_panel()
                self._open_info_panel(game_state.selected_tower_to_build)

        else:
            if self.info_panel or self.upgrade_panel:
                self._close_panel()

        if self.persona_panel:
            self.persona_panel.update(dt, game_state)
        elif self.upgrade_panel:
            self.upgrade_panel.update(dt, game_state)
        elif self.info_panel:
            self.info_panel.update(dt, game_state)

        self.hovered_tower_button = None
        for button in self.tower_buttons:
            button.update(dt, game_state)
            if button.is_hovered:
                self.hovered_tower_button = button

    # --- MODIFIED: Enhanced styling for the tower bar (Step 2.1) ---
    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws all UI elements, including the newly styled tower bar."""
        panel_rect = pygame.Rect(
            0,
            self.screen_rect.height - self.hud_panel_height,
            self.screen_rect.width,
            self.hud_panel_height,
        )

        # Create a dedicated surface for the panel to draw gradients and effects on.
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)

        # Define gradient colors from the theme.
        color_top = self.colors.get("panel_secondary", [40, 50, 60])
        color_bottom = self.colors.get("panel_primary", [25, 30, 40])

        # Draw the gradient by iterating through each vertical line of the panel.
        for y in range(panel_rect.height):
            # Interpolate color from top to bottom
            ratio = y / panel_rect.height
            r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
            g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
            b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)

            # Draw a horizontal line with the calculated color and alpha.
            pygame.draw.line(panel_surf, (r, g, b, 220), (0, y), (panel_rect.width, y))

        # Add a bright inner highlight along the top edge for a nice finish.
        highlight_color = self.colors.get(
            "border_interactive_selected", (150, 180, 200)
        )
        pygame.draw.line(panel_surf, highlight_color, (0, 0), (panel_rect.width, 0), 2)

        # Blit the final styled surface to the screen.
        screen.blit(panel_surf, panel_rect.topleft)

        # Draw the rest of the UI elements on top of the new panel.
        for button in self.tower_buttons:
            button.draw(screen, game_state)
        for button in self.tab_buttons:
            button.draw(screen)

        if self.upgrade_panel:
            self.upgrade_panel.draw(screen)
        if self.info_panel:
            self.info_panel.draw(screen)
        if self.persona_panel:
            self.persona_panel.draw(screen)
