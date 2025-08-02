# rendering/hud/panels/upgrade_panel.py
import pygame
import logging
from typing import Optional, List, TYPE_CHECKING, Dict, Any

from rendering.common.ui.ui_element import UIElement
from ..buttons.upgrade_button import UpgradeButton
from rendering.common.ui.ui_action import UIAction, ActionType
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from game_logic.entities.tower import Tower
    from game_logic.upgrades.upgrade_manager import UpgradeManager
    from game_logic.game_state import GameState
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class UpgradePanel(UIElement):
    """
    A UI panel that displays stats and upgrade options for a selected tower.
    REFACTORED: Now fully theme-driven and dynamically sized.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower: "Tower",
        tower_base_data: Dict[str, Any],
        upgrade_manager: "UpgradeManager",
        game_state: "GameState",
        salvage_refund_percentage: float,
        targeting_ai_config: Dict[str, Any],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.tower = tower
        self.tower_base_data = tower_base_data
        self.upgrade_manager = upgrade_manager
        self.game_state = game_state
        self.salvage_refund_percentage = salvage_refund_percentage
        self.targeting_ai_config = targeting_ai_config
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self.upgrade_buttons: List[UpgradeButton] = []
        self.persona_change_button_rect = pygame.Rect(0, 0, 0, 0)
        self.is_persona_button_hovered = False
        self.close_button_rect = pygame.Rect(0, 0, 0, 0)
        self.is_close_hovered = False
        self.salvage_button_rect = pygame.Rect(0, 0, 0, 0)
        self.is_salvage_hovered = False

        self._load_theme_assets()
        self.rebuild_layout()

    def _load_theme_assets(self):
        """Loads all necessary fonts and style values from the theme config."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("body_large")
        self.font_header = self.font_manager.get_font("body_medium", bold=True)
        self.font_stat = self.font_manager.get_font("body_small")
        self.font_close = self.font_manager.get_font("body_large")
        self.font_salvage = self.font_manager.get_font("body_medium", bold=True)
        self.font_persona = self.font_manager.get_font("body_tiny", bold=True)

    def on_resize(self, new_screen_rect: pygame.Rect):
        """Updates position based on new screen dimensions."""
        self.rect.right = new_screen_rect.right - self.layout.get("padding_medium", 15)
        self.rebuild_layout()

    def rebuild_layout(self):
        """Forces the panel to re-create its buttons and recalculate layout."""
        self._create_button_objects()
        self._perform_layout_and_positioning()
        self.update_hover_states()

    def update_hover_states(self):
        """Checks mouse position and updates hover state for all elements."""
        mouse_pos = pygame.mouse.get_pos()
        self.is_close_hovered = self.close_button_rect.collidepoint(mouse_pos)
        self.is_salvage_hovered = self.salvage_button_rect.collidepoint(mouse_pos)
        self.is_persona_button_hovered = self.persona_change_button_rect.collidepoint(
            mouse_pos
        )
        for button in self.upgrade_buttons:
            button.is_hovered = button.rect.collidepoint(mouse_pos)

    def _perform_layout_and_positioning(self):
        """Calculates required height and sets positions for all elements."""
        padding = self.layout.get("padding_medium", 15)
        spacing = self.layout.get("spacing_medium", 10)
        current_y = self.rect.y + padding

        # Close button
        self.close_button_rect = pygame.Rect(
            self.rect.right - 28, self.rect.y + 8, 20, 20
        )

        # Title and Stats
        current_y += self.font_title.get_height() + spacing
        stats_to_display = self._get_stats_to_display()
        current_y += self.font_header.get_height() + (spacing / 2)
        current_y += len(stats_to_display) * 22
        current_y += spacing

        # Persona Section
        current_y += self.font_header.get_height() + (spacing / 2)
        current_y += 26  # Space for "Current: ..." text
        button_width = self.rect.width - (padding * 2)
        self.persona_change_button_rect = pygame.Rect(
            self.rect.x + padding, current_y, button_width, 30
        )
        current_y += self.persona_change_button_rect.height + spacing

        # Upgrade Buttons
        if self.upgrade_buttons:
            current_y += spacing
            for button in self.upgrade_buttons:
                button.rect.topleft = (self.rect.x + padding, current_y)
                current_y += button.rect.height + spacing

        # Salvage Button Area
        current_y += 55
        self.rect.height = current_y - self.rect.y
        self.salvage_button_rect = pygame.Rect(
            self.rect.x + padding,
            self.rect.bottom - 55,
            self.rect.width - (padding * 2),
            40,
        )

    def _create_button_objects(self):
        self.upgrade_buttons.clear()
        padding = self.layout.get("padding_medium", 15)
        width = self.rect.width - (padding * 2)

        for path in ["path_a", "path_b"]:
            next_upgrade = self.upgrade_manager.get_next_upgrade(self.tower, path)
            if next_upgrade:
                can_afford = self.game_state.gold >= next_upgrade.cost
                button_rect = pygame.Rect(0, 0, width, 0)
                self.upgrade_buttons.append(
                    UpgradeButton(
                        button_rect,
                        next_upgrade,
                        can_afford,
                        self.ui_theme,
                        self.font_manager,
                    )
                )

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        if event.type == pygame.MOUSEMOTION:
            self.update_hover_states()
        if not self.rect.collidepoint(pygame.mouse.get_pos()):
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_close_hovered:
                return UIAction(type=ActionType.CLOSE_PANEL)
            if self.is_salvage_hovered:
                return UIAction(type=ActionType.SALVAGE_TOWER)
            if self.is_persona_button_hovered:
                return UIAction(type=ActionType.OPEN_PERSONA_PANEL)
            for button in self.upgrade_buttons:
                action = button.handle_event(event, game_state)
                if action:
                    return action
        return None

    def draw(self, screen: pygame.Surface):
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        # --- FIX (Step 1.2): Convert the list-based color from theme to a tuple ---
        panel_color = self.colors.get("panel_primary", [25, 30, 40])
        panel_surf.fill(tuple(panel_color) + (230,))
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(
            screen,
            self.colors.get("border_primary"),
            self.rect,
            2,
            border_radius=self.layout.get("border_radius_small"),
        )

        self._draw_static_text(screen)
        self._draw_persona_section(screen)
        for button in self.upgrade_buttons:
            button.draw(screen, self.game_state)
        self._draw_salvage_button(screen)
        self._draw_close_button(screen)

    def _draw_persona_section(self, screen: pygame.Surface):
        padding = self.layout.get("padding_medium", 15)
        spacing = self.layout.get("spacing_medium", 10)

        # Calculate Y position based on the layout of the stats section
        stats_to_display = self._get_stats_to_display()
        header_y = (
            self.rect.y
            + padding
            + self.font_title.get_height()
            + spacing
            + self.font_header.get_height()
            + (spacing / 2)
            + (len(stats_to_display) * 22)
            + spacing
        )

        header_surf = self.font_header.render(
            "Targeting Priority", True, self.colors.get("text_primary")
        )
        screen.blit(header_surf, (self.rect.x + padding, header_y))

        info_y = header_y + self.font_header.get_height() + (spacing / 2)
        active_persona_name = self.targeting_ai_config.get(
            self.tower.current_persona, {}
        ).get("name", "N/A")
        label_surf = self.font_stat.render(
            "Current:", True, self.colors.get("text_secondary")
        )
        value_surf = self.font_stat.render(
            active_persona_name, True, self.colors.get("text_primary")
        )
        screen.blit(label_surf, (self.rect.x + padding, info_y))
        value_rect = value_surf.get_rect(topright=(self.rect.right - padding, info_y))
        screen.blit(value_surf, value_rect)

        bg_color = (
            self.colors.get("panel_interactive_hover")
            if self.is_persona_button_hovered
            else self.colors.get("panel_secondary")
        )
        border_color = self.colors.get("border_primary")
        pygame.draw.rect(
            screen,
            bg_color,
            self.persona_change_button_rect,
            border_radius=self.layout.get("border_radius_small"),
        )
        pygame.draw.rect(
            screen,
            border_color,
            self.persona_change_button_rect,
            1,
            border_radius=self.layout.get("border_radius_small"),
        )
        text_surf = self.font_persona.render(
            "Change Persona...", True, self.colors.get("text_primary")
        )
        text_rect = text_surf.get_rect(center=self.persona_change_button_rect.center)
        screen.blit(text_surf, text_rect)

    def _draw_close_button(self, screen: pygame.Surface):
        color = (
            self.colors.get("text_error")
            if self.is_close_hovered
            else self.colors.get("text_secondary")
        )
        text_surf = self.font_close.render("X", True, color)
        text_rect = text_surf.get_rect(center=self.close_button_rect.center)
        screen.blit(text_surf, text_rect)

    def _draw_salvage_button(self, screen: pygame.Surface):
        bg_color = (
            self.colors.get("panel_interactive_hover")
            if self.is_salvage_hovered
            else self.colors.get("text_error")
        )
        pygame.draw.rect(
            screen,
            bg_color,
            self.salvage_button_rect,
            border_radius=self.layout.get("border_radius_small"),
        )

        refund_amount = int(
            self.tower.total_investment * self.salvage_refund_percentage
        )
        button_text = f"Salvage for {refund_amount}G"
        text_surf = self.font_salvage.render(
            button_text, True, self.colors.get("text_primary")
        )
        text_rect = text_surf.get_rect(center=self.salvage_button_rect.center)
        screen.blit(text_surf, text_rect)

    def _get_stats_to_display(self) -> List[tuple[str, Any, Any]]:
        stats = []
        stat_definitions = self.tower_base_data.get("info_panel_stats", [])
        for stat_info in stat_definitions:
            label, value_path = stat_info.get("label"), stat_info.get("value_path")
            live_value = (
                get_nested_value(self.tower, value_path) if value_path else None
            )
            if live_value is not None:
                stats.append((label, live_value, stat_info.get("format")))
        if self.tower.pierce_count > 0 and not any(s[0] == "Pierce" for s in stats):
            stats.append(("Pierce", self.tower.pierce_count, None))
        if self.tower.projectiles_per_shot > 1 and not any(
            s[0] == "Projectiles" for s in stats
        ):
            stats.append(("Projectiles", self.tower.projectiles_per_shot, None))
        return stats

    def _draw_static_text(self, screen: pygame.Surface):
        padding = self.layout.get("padding_medium", 15)
        spacing = self.layout.get("spacing_medium", 10)
        current_y = self.rect.y + padding
        title_surf = self.font_title.render(
            self.tower.name, True, self.colors.get("text_primary")
        )
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        current_y += title_surf.get_height() + spacing
        stats_header_surf = self.font_header.render(
            "Statistics", True, self.colors.get("text_primary")
        )
        screen.blit(stats_header_surf, (self.rect.x + padding, current_y))
        current_y += stats_header_surf.get_height() + (spacing / 2)
        for label, value, value_format in self._get_stats_to_display():
            value_str = format_stat_value(value, value_format)
            label_surf = self.font_stat.render(
                f"{label}:", True, self.colors.get("text_secondary")
            )
            value_surf = self.font_stat.render(
                value_str, True, self.colors.get("text_primary")
            )
            screen.blit(label_surf, (self.rect.x + padding, current_y))
            value_rect = value_surf.get_rect(
                topright=(self.rect.right - padding, current_y)
            )
            screen.blit(value_surf, value_rect)
            current_y += 22
