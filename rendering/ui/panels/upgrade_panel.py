# rendering/ui/panels/upgrade_panel.py
import pygame
import logging
from typing import Optional, List, TYPE_CHECKING, Dict, Any

from ..ui_element import UIElement
from ..buttons.upgrade_button import UpgradeButton
from ..ui_action import UIAction, ActionType
from .panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from game_logic.entities.tower import Tower
    from game_logic.upgrades.upgrade_manager import UpgradeManager
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class UpgradePanel(UIElement):
    """
    A UI panel that displays stats and upgrade options for a selected tower.

    REFACTORED: The persona selection is now handled by a single button that
    opens a dedicated modal panel, creating a cleaner and more scalable UI.
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
    ):
        super().__init__(rect)
        self.tower = tower
        self.tower_base_data = tower_base_data
        self.upgrade_manager = upgrade_manager
        self.game_state = game_state
        self.salvage_refund_percentage = salvage_refund_percentage
        self.targeting_ai_config = targeting_ai_config

        self.upgrade_buttons: List[UpgradeButton] = []
        # --- UI IMPROVEMENT: Separate rect for the button ---
        self.persona_change_button_rect = pygame.Rect(0, 0, 0, 0)
        self.is_persona_button_hovered = False

        self._setup_fonts_and_colors()

        self.close_button_rect = pygame.Rect(
            self.rect.right - 28, self.rect.y + 8, 20, 20
        )
        self.is_close_hovered = False
        self.salvage_button_rect = pygame.Rect(0, 0, 0, 0)
        self.is_salvage_hovered = False

        self.rebuild_layout()

    def rebuild_layout(self):
        """
        Forces the panel to re-create its buttons, calculate all element positions,
        and resize the panel.
        """
        self._create_button_objects()
        self._perform_layout_and_positioning()

    def update_hover_states(self):
        """
        Checks the current mouse position and updates the hover state for all
        interactive elements on this panel.
        """
        mouse_pos = pygame.mouse.get_pos()
        self.is_close_hovered = self.close_button_rect.collidepoint(mouse_pos)
        self.is_salvage_hovered = self.salvage_button_rect.collidepoint(mouse_pos)
        self.is_persona_button_hovered = self.persona_change_button_rect.collidepoint(
            mouse_pos
        )
        for button in self.upgrade_buttons:
            button.is_hovered = button.rect.collidepoint(mouse_pos)

    def _perform_layout_and_positioning(self):
        """
        Calculates the required height and sets the final position for all elements.
        """
        padding = 15
        current_y = self.rect.y + padding

        # Section 1: Title and Stats
        current_y += self.font_title.get_height() + 10
        stats_to_display = self._get_stats_to_display()
        current_y += self.font_header.get_height() + 5
        current_y += len(stats_to_display) * 24
        current_y += 15

        # --- UI IMPROVEMENT: Layout for persona info and change button ---
        current_y += self.font_header.get_height() + 5  # Header
        current_y += 24  # Space for the "Current: ..." text
        button_width = self.rect.width - (padding * 2)
        self.persona_change_button_rect = pygame.Rect(
            self.rect.x + padding, current_y, button_width, 30
        )
        current_y += self.persona_change_button_rect.height + 15

        # Section 3: Upgrade Buttons
        if self.upgrade_buttons:
            for button in self.upgrade_buttons:
                button.rect.topleft = (self.rect.x + padding, current_y)
                current_y += button.rect.height + 10

        # Section 4: Salvage Button Area
        current_y += 55

        # Final Sizing and Salvage Button Positioning
        self.rect.height = current_y - self.rect.y
        self.salvage_button_rect = pygame.Rect(
            self.rect.x + 15, self.rect.bottom - 55, self.rect.width - 30, 40
        )

    def _setup_fonts_and_colors(self):
        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_header = pygame.font.SysFont("segoeui", 18, bold=True)
        self.font_stat = pygame.font.SysFont("segoeui", 16)
        self.font_close = pygame.font.SysFont("segoeui", 20, bold=True)
        self.font_salvage = pygame.font.SysFont("segoeui", 16, bold=True)
        self.font_persona = pygame.font.SysFont("segoeui", 14, bold=True)
        self.colors = {
            "bg": (25, 30, 40, 230),
            "border": (80, 90, 100),
            "title": (240, 240, 240),
            "header": (200, 200, 210),
            "stat_label": (160, 160, 170),
            "stat_value": (220, 220, 230),
            "close_default": (150, 150, 160),
            "close_hover": (255, 80, 80),
            "salvage_bg_default": (80, 40, 40),
            "salvage_bg_hover": (110, 50, 50),
            "salvage_border": (150, 80, 80),
            "salvage_text": (230, 210, 210),
            "persona_bg_default": (40, 50, 60),
            "persona_bg_hover": (60, 75, 90),
            "persona_border_default": (80, 90, 100),
            "persona_text": (210, 210, 220),
        }

    def _create_button_objects(self):
        self.upgrade_buttons.clear()
        padding = 15
        width = self.rect.width - (padding * 2)

        next_upgrade_a = self.upgrade_manager.get_next_upgrade(self.tower, "path_a")
        if next_upgrade_a:
            can_afford = self.game_state.gold >= next_upgrade_a.cost
            button_rect = pygame.Rect(0, 0, width, 0)
            self.upgrade_buttons.append(
                UpgradeButton(button_rect, next_upgrade_a, can_afford)
            )

        next_upgrade_b = self.upgrade_manager.get_next_upgrade(self.tower, "path_b")
        if next_upgrade_b:
            can_afford = self.game_state.gold >= next_upgrade_b.cost
            button_rect = pygame.Rect(0, 0, width, 0)
            self.upgrade_buttons.append(
                UpgradeButton(button_rect, next_upgrade_b, can_afford)
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
        panel_surf.fill(self.colors["bg"])
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=5)

        self._draw_static_text(screen)
        self._draw_persona_section(screen)
        for button in self.upgrade_buttons:
            button.draw(screen, self.game_state)
        self._draw_salvage_button(screen)
        self._draw_close_button(screen)

    def _draw_persona_section(self, screen: pygame.Surface):
        padding = 15

        # --- UI IMPROVEMENT: Draw separated info and button ---

        # 1. Draw Header
        header_y = (
            self.persona_change_button_rect.y - 24 - self.font_header.get_height() - 5
        )
        header_surf = self.font_header.render(
            "Targeting Priority", True, self.colors["header"]
        )
        screen.blit(header_surf, (self.rect.x + padding, header_y))

        # 2. Draw Current Persona Info Text
        info_y = self.persona_change_button_rect.y - 26
        active_persona_name = self.targeting_ai_config.get(
            self.tower.current_persona, {}
        ).get("name", "N/A")

        label_surf = self.font_stat.render("Current:", True, self.colors["stat_label"])
        value_surf = self.font_stat.render(
            active_persona_name, True, self.colors["stat_value"]
        )

        screen.blit(label_surf, (self.rect.x + padding, info_y))
        value_rect = value_surf.get_rect(topright=(self.rect.right - padding, info_y))
        screen.blit(value_surf, value_rect)

        # 3. Draw the "Change..." Button
        bg_color = (
            self.colors["persona_bg_hover"]
            if self.is_persona_button_hovered
            else self.colors["persona_bg_default"]
        )
        border_color = self.colors["persona_border_default"]

        pygame.draw.rect(
            screen, bg_color, self.persona_change_button_rect, border_radius=4
        )
        pygame.draw.rect(
            screen, border_color, self.persona_change_button_rect, 1, border_radius=4
        )

        button_text = "Change Persona..."
        text_surf = self.font_persona.render(
            button_text, True, self.colors["persona_text"]
        )
        text_rect = text_surf.get_rect(center=self.persona_change_button_rect.center)
        screen.blit(text_surf, text_rect)

    def _draw_close_button(self, screen: pygame.Surface):
        color = (
            self.colors["close_hover"]
            if self.is_close_hovered
            else self.colors["close_default"]
        )
        text_surf = self.font_close.render("X", True, color)
        text_rect = text_surf.get_rect(center=self.close_button_rect.center)
        screen.blit(text_surf, text_rect)

    def _draw_salvage_button(self, screen: pygame.Surface):
        bg_color = (
            self.colors["salvage_bg_hover"]
            if self.is_salvage_hovered
            else self.colors["salvage_bg_default"]
        )
        pygame.draw.rect(screen, bg_color, self.salvage_button_rect, border_radius=5)
        pygame.draw.rect(
            screen,
            self.colors["salvage_border"],
            self.salvage_button_rect,
            2,
            border_radius=5,
        )
        refund_amount = int(
            self.tower.total_investment * self.salvage_refund_percentage
        )
        button_text = f"Salvage for {refund_amount}G"
        text_surf = self.font_salvage.render(
            button_text, True, self.colors["salvage_text"]
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
        padding = 15
        current_y = self.rect.y + padding
        title_surf = self.font_title.render(self.tower.name, True, self.colors["title"])
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        current_y += self.font_title.get_height() + 10
        stats_header_surf = self.font_header.render(
            "Statistics", True, self.colors["header"]
        )
        screen.blit(stats_header_surf, (self.rect.x + padding, current_y))
        current_y += stats_header_surf.get_height() + 5
        stats_to_display = self._get_stats_to_display()
        for label, value, value_format in stats_to_display:
            value_str = format_stat_value(value, value_format)
            label_surf = self.font_stat.render(
                f"{label}:", True, self.colors["stat_label"]
            )
            value_surf = self.font_stat.render(
                value_str, True, self.colors["stat_value"]
            )
            screen.blit(label_surf, (self.rect.x + padding, current_y))
            value_rect = value_surf.get_rect(
                topright=(self.rect.right - padding, current_y)
            )
            screen.blit(value_surf, value_rect)
            current_y += 24
