# rendering/ui/panels/upgrade_panel.py
import pygame
import logging
from typing import Optional, List, TYPE_CHECKING

from ..ui_element import UIElement
from ..buttons.upgrade_button import UpgradeButton

# --- MODIFIED: Import the new structured action classes ---
# We import our action vocabulary to create and handle structured,
# type-safe commands instead of relying on fragile strings.
from ..ui_action import UIAction, ActionType

# Use TYPE_CHECKING to avoid circular imports for type hinting.
if TYPE_CHECKING:
    from game_logic.entities.tower import Tower
    from game_logic.upgrades.upgrade_manager import UpgradeManager
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class UpgradePanel(UIElement):
    """
    A UI panel that displays detailed stats and upgrade options for a selected tower.
    This panel now also includes a button for salvaging the tower and communicates
    all actions via structured UIAction objects.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower: "Tower",
        upgrade_manager: "UpgradeManager",
        game_state: "GameState",
        salvage_refund_percentage: float,
    ):
        """
        Initializes the UpgradePanel.
        """
        super().__init__(rect)
        self.tower = tower
        self.upgrade_manager = upgrade_manager
        self.game_state = game_state
        self.salvage_refund_percentage = salvage_refund_percentage

        self.upgrade_buttons: List[UpgradeButton] = []
        self._setup_fonts_and_colors()
        self._create_layout()

        # --- Close Button Attributes ---
        self.close_button_rect = pygame.Rect(
            self.rect.right - 28, self.rect.y + 8, 20, 20
        )
        self.is_close_hovered = False

        # --- Salvage Button Attributes ---
        self.salvage_button_rect = pygame.Rect(
            self.rect.x + 15, self.rect.bottom - 55, self.rect.width - 30, 40
        )
        self.is_salvage_hovered = False

    def _setup_fonts_and_colors(self):
        """Initializes fonts and color constants for drawing."""
        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_header = pygame.font.SysFont("segoeui", 18, bold=True)
        self.font_stat = pygame.font.SysFont("segoeui", 16)
        self.font_close = pygame.font.SysFont("segoeui", 20, bold=True)
        self.font_salvage = pygame.font.SysFont("segoeui", 16, bold=True)
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
        }

    def _create_layout(self):
        """
        Creates and positions all the sub-elements within the panel.
        """
        self.upgrade_buttons.clear()
        padding = 15
        button_height = 60
        button_spacing = 10
        stats_start_y = self.rect.y + 80

        next_upgrade_a = self.upgrade_manager.get_next_upgrade(self.tower, "path_a")
        if next_upgrade_a:
            can_afford_a = self.game_state.gold >= next_upgrade_a.cost
            button_rect_a = pygame.Rect(
                self.rect.x + padding,
                stats_start_y + 120,
                self.rect.width - padding * 2,
                button_height,
            )
            self.upgrade_buttons.append(
                UpgradeButton(button_rect_a, next_upgrade_a, can_afford_a)
            )

        next_upgrade_b = self.upgrade_manager.get_next_upgrade(self.tower, "path_b")
        if next_upgrade_b:
            can_afford_b = self.game_state.gold >= next_upgrade_b.cost
            y_pos_b = stats_start_y + 120 + button_height + button_spacing
            button_rect_b = pygame.Rect(
                self.rect.x + padding,
                y_pos_b,
                self.rect.width - padding * 2,
                button_height,
            )
            self.upgrade_buttons.append(
                UpgradeButton(button_rect_b, next_upgrade_b, can_afford_b)
            )

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:  # --- MODIFIED: Return type is now UIAction ---
        """
        Delegates event handling and returns a structured UIAction if triggered.
        """
        mouse_pos = pygame.mouse.get_pos()

        # --- NEU: Hover-Zustände für alle Elemente im Panel aktualisieren ---
        # Dies muss immer geschehen, unabhängig davon, ob die Maus im Panel ist,
        # damit der Hover-Zustand korrekt zurückgesetzt wird, wenn die Maus das Panel verlässt.
        self.is_close_hovered = self.close_button_rect.collidepoint(mouse_pos)
        self.is_salvage_hovered = self.salvage_button_rect.collidepoint(mouse_pos)
        for button in self.upgrade_buttons:
            # `handle_event` in `UpgradeButton` aktualisiert `is_hovered` basierend auf `mouse_pos`
            button.handle_event(
                event, game_state
            )  # Pass the event to update hover state

        # Nur Klicks verarbeiten, wenn die Maus im Panel ist
        if not self.rect.collidepoint(mouse_pos):
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_close_hovered:
                logger.debug("Upgrade panel close button clicked.")
                # --- MODIFIED: Return a structured UIAction object ---
                return UIAction(type=ActionType.CLOSE_PANEL)
            if self.is_salvage_hovered:
                logger.info(f"Player clicked salvage for tower {self.tower.entity_id}.")
                # --- MODIFIED: Return a structured UIAction object ---
                return UIAction(type=ActionType.SALVAGE_TOWER)

        # Klicks an Upgrade-Buttons weiterleiten und deren Aktion propagieren.
        for button in self.upgrade_buttons:
            # Die `handle_event`-Methode des Buttons gibt jetzt eine `Optional[UIAction]` zurück.
            action = button.handle_event(event, game_state)
            if action:
                # Wenn der Button eine Aktion zurückgegeben hat, propagieren wir sie.
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

        for button in self.upgrade_buttons:
            button.draw(screen, self.game_state)

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

        stats_to_display = {
            "Damage": self.tower.damage,
            "Range": self.tower.range,
            "Fire Rate": f"{self.tower.fire_rate:.2f}/s",
            "Pierce": self.tower.pierce_count,
            "Projectiles": self.tower.projectiles_per_shot,
        }

        for label, value in stats_to_display.items():
            if value == 0 and label in ["Pierce", "Projectiles"]:
                continue

            label_surf = self.font_stat.render(
                f"{label}:", True, self.colors["stat_label"]
            )
            value_surf = self.font_stat.render(
                str(value), True, self.colors["stat_value"]
            )

            screen.blit(label_surf, (self.rect.x + padding, current_y))
            screen.blit(value_surf, (self.rect.x + 120, current_y))
            current_y += line_height
