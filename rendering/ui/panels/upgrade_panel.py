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
    A UI panel that displays stats, upgrade options, and targeting
    priorities for a selected tower. Now dynamically sizes itself.
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
        """
        Initializes the UpgradePanel.
        """
        super().__init__(rect)
        self.tower = tower
        self.tower_base_data = tower_base_data
        self.upgrade_manager = upgrade_manager
        self.game_state = game_state
        self.salvage_refund_percentage = salvage_refund_percentage
        self.targeting_ai_config = targeting_ai_config

        self.upgrade_buttons: List[UpgradeButton] = []
        self.persona_buttons: List[Dict[str, Any]] = []
        self._setup_fonts_and_colors()

        self.close_button_rect = pygame.Rect(
            self.rect.right - 28, self.rect.y + 8, 20, 20
        )
        self.is_close_hovered = False

        self.salvage_button_rect = pygame.Rect(0, 0, 0, 0)
        self.rebuild_layout()

    def rebuild_layout(self):
        """
        Forces the panel to re-create its buttons and resize based on the
        current game state.
        """
        self._create_layout()
        self._calculate_and_set_dynamic_height()
        self.salvage_button_rect = pygame.Rect(
            self.rect.x + 15, self.rect.bottom - 55, self.rect.width - 30, 40
        )
        self.is_salvage_hovered = self.salvage_button_rect.collidepoint(
            pygame.mouse.get_pos()
        )

    def _calculate_and_set_dynamic_height(self):
        """Calculates the total height required and resizes the panel's rect."""
        padding = 15
        line_height = 24

        stats_to_display = self._get_stats_to_display()
        stats_section_height = 40 + (len(stats_to_display) * line_height) + 5
        current_height = padding + stats_section_height

        if self.persona_buttons:
            current_height += 40
            current_height += (len(self.persona_buttons) * (28 + 5)) + 15

        if self.upgrade_buttons:
            total_upgrade_height = sum(b.rect.height for b in self.upgrade_buttons)
            total_spacing = (
                (len(self.upgrade_buttons) - 1) * 10
                if len(self.upgrade_buttons) > 1
                else 0
            )
            current_height += total_upgrade_height + total_spacing

        current_height += 70
        self.rect.height = current_height

    def _setup_fonts_and_colors(self):
        """Initializes fonts and color constants for drawing."""
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
            "persona_bg_active": (80, 110, 140),
            "persona_border_default": (80, 90, 100),
            "persona_border_active": (150, 180, 200),
            "persona_text": (210, 210, 220),
        }

    def _create_layout(self):
        """Creates and positions all UI elements dynamically."""
        self.upgrade_buttons.clear()
        self.persona_buttons.clear()
        padding = 15

        stats_to_display = self._get_stats_to_display()
        stats_section_height = 40 + (len(stats_to_display) * 24) + 5
        current_y = self.rect.y + padding + stats_section_height

        if self.tower.available_personas and len(self.tower.available_personas) > 1:
            current_y += 40
            persona_button_height = 28
            for persona_id in self.tower.available_personas:
                persona_data = self.targeting_ai_config.get(persona_id, {})
                button_rect = pygame.Rect(
                    self.rect.x + padding,
                    current_y,
                    self.rect.width - (padding * 2),
                    persona_button_height,
                )
                self.persona_buttons.append(
                    {
                        "id": persona_id,
                        "name": persona_data.get("name", persona_id),
                        "rect": button_rect,
                        "is_hovered": False,
                    }
                )
                current_y += persona_button_height + 5
            current_y += 15

        next_upgrade_a = self.upgrade_manager.get_next_upgrade(self.tower, "path_a")
        if next_upgrade_a:
            can_afford = self.game_state.gold >= next_upgrade_a.cost
            button_rect = pygame.Rect(
                self.rect.x + padding,
                current_y,
                self.rect.width - (padding * 2),
                0,
            )
            button_a = UpgradeButton(button_rect, next_upgrade_a, can_afford)
            self.upgrade_buttons.append(button_a)
            current_y += button_a.rect.height + 10

        next_upgrade_b = self.upgrade_manager.get_next_upgrade(self.tower, "path_b")
        if next_upgrade_b:
            can_afford = self.game_state.gold >= next_upgrade_b.cost
            button_rect = pygame.Rect(
                self.rect.x + padding,
                current_y,
                self.rect.width - (padding * 2),
                0,
            )
            button_b = UpgradeButton(button_rect, next_upgrade_b, can_afford)
            self.upgrade_buttons.append(button_b)

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        """Delegates event handling to child buttons."""
        mouse_pos = pygame.mouse.get_pos()
        self.is_close_hovered = self.close_button_rect.collidepoint(mouse_pos)
        self.is_salvage_hovered = self.salvage_button_rect.collidepoint(mouse_pos)

        for button_data in self.persona_buttons:
            button_data["is_hovered"] = button_data["rect"].collidepoint(mouse_pos)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if button_data["is_hovered"]:
                    return UIAction(
                        type=ActionType.CHANGE_TARGETING_PERSONA,
                        entity_id=button_data["id"],
                    )

        if not self.rect.collidepoint(mouse_pos):
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_close_hovered:
                return UIAction(type=ActionType.CLOSE_PANEL)
            if self.is_salvage_hovered:
                return UIAction(type=ActionType.SALVAGE_TOWER)

        for button in self.upgrade_buttons:
            action = button.handle_event(event, game_state)
            if action:
                return action
        return None

    def draw(self, screen: pygame.Surface):
        """Draws the panel and all its components."""
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors["bg"])
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=5)

        self._draw_text(screen)
        self._draw_close_button(screen)
        self._draw_salvage_button(screen)
        self._draw_persona_buttons(screen)

        for button in self.upgrade_buttons:
            button.draw(screen, self.game_state)

    def _draw_persona_buttons(self, screen: pygame.Surface):
        """Draws the targeting priority buttons."""
        if not self.persona_buttons:
            return

        padding = 15
        stats_to_display = self._get_stats_to_display()
        stats_section_height = 40 + (len(stats_to_display) * 24) + 5
        header_y = self.rect.y + padding + stats_section_height

        header_surf = self.font_header.render(
            "Targeting Priority", True, self.colors["header"]
        )
        screen.blit(header_surf, (self.rect.x + padding, header_y))

        for button_data in self.persona_buttons:
            is_active = self.tower.current_persona == button_data["id"]
            bg_color = (
                self.colors["persona_bg_active"]
                if is_active
                else (
                    self.colors["persona_bg_hover"]
                    if button_data["is_hovered"]
                    else self.colors["persona_bg_default"]
                )
            )
            border_color = (
                self.colors["persona_border_active"]
                if is_active
                else self.colors["persona_border_default"]
            )
            pygame.draw.rect(screen, bg_color, button_data["rect"], border_radius=4)
            pygame.draw.rect(
                screen, border_color, button_data["rect"], 1, border_radius=4
            )
            text_surf = self.font_persona.render(
                button_data["name"], True, self.colors["persona_text"]
            )
            text_rect = text_surf.get_rect(center=button_data["rect"].center)
            screen.blit(text_surf, text_rect)

    def _draw_close_button(self, screen: pygame.Surface):
        """Draws the 'X' button to close the panel."""
        color = (
            self.colors["close_hover"]
            if self.is_close_hovered
            else self.colors["close_default"]
        )
        text_surf = self.font_close.render("X", True, color)
        text_rect = text_surf.get_rect(center=self.close_button_rect.center)
        screen.blit(text_surf, text_rect)

    def _draw_salvage_button(self, screen: pygame.Surface):
        """Draws the salvage button at the bottom of the panel."""
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
        """
        Gets the list of stats to display by reading the tower's base data
        and fetching the corresponding LIVE values from the tower instance.
        """
        stats = []
        stat_definitions = self.tower_base_data.get("info_panel_stats", [])

        # --- REFACTORED: Create a temporary dictionary of the tower's live data ---
        # This allows us to use the robust get_nested_value function
        tower_live_data = {
            "attack": {"data": self.tower.attack_data.get("data", {})},
            "auras": self.tower.auras,
            "damage": self.tower.damage,
            "range": self.tower.range,
            "fire_rate": self.tower.fire_rate,
        }

        for stat_info in stat_definitions:
            label = stat_info.get("label")
            value_path = stat_info.get("value_path")

            # Use the utility to get the live value from our temporary dict
            live_value = (
                get_nested_value(tower_live_data, value_path) if value_path else None
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

    def _draw_text(self, screen: pygame.Surface):
        """Renders and blits all the text elements for the panel."""
        padding = 15
        line_height = 24
        current_y = self.rect.y + padding

        title_surf = self.font_title.render(self.tower.name, True, self.colors["title"])
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        current_y += 40

        stats_header_surf = self.font_header.render(
            "Statistics", True, self.colors["header"]
        )
        screen.blit(stats_header_surf, (self.rect.x + padding, current_y))
        current_y += line_height + 5

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
            current_y += line_height
