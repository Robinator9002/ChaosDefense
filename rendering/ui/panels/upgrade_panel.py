# rendering/ui/panels/upgrade_panel.py
import pygame
import logging
from typing import Optional, List, TYPE_CHECKING

from ..ui_element import UIElement
from ..buttons.upgrade_button import UpgradeButton

# Use TYPE_CHECKING to avoid circular imports for type hinting.
if TYPE_CHECKING:
    from game_logic.entities.tower import Tower
    from game_logic.upgrades.upgrade_manager import UpgradeManager
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class UpgradePanel(UIElement):
    """
    A UI panel that displays detailed stats and upgrade options for a selected tower.

    This panel is dynamically created and populated when a player selects a tower
    on the map. It is responsible for laying out all the relevant information,
    including the tower's name, its current statistics, and the buttons for its
    two distinct upgrade paths.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower: "Tower",
        upgrade_manager: "UpgradeManager",
        game_state: "GameState",
    ):
        """
        Initializes the UpgradePanel.

        Args:
            rect (pygame.Rect): The rectangle defining the panel's position and size.
            tower (Tower): The specific tower instance this panel represents.
            upgrade_manager (UpgradeManager): The game's upgrade manager, used to
                                            fetch upgrade data.
            game_state (GameState): The current state of the game, used for checking
                                    affordability.
        """
        super().__init__(rect)
        self.tower = tower
        self.upgrade_manager = upgrade_manager
        self.game_state = game_state

        self.upgrade_buttons: List[UpgradeButton] = []
        self._setup_fonts_and_colors()
        self._create_layout()

    def _setup_fonts_and_colors(self):
        """Initializes fonts and color constants for drawing."""
        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_header = pygame.font.SysFont("segoeui", 18, bold=True)
        self.font_stat = pygame.font.SysFont("segoeui", 16)
        self.colors = {
            "bg": (25, 30, 40, 230),
            "border": (80, 90, 100),
            "title": (240, 240, 240),
            "header": (200, 200, 210),
            "stat_label": (160, 160, 170),
            "stat_value": (220, 220, 230),
        }

    def _create_layout(self):
        """
        Creates and positions all the sub-elements within the panel.

        This method is responsible for arranging the tower's stats and creating
        the UpgradeButton instances for the two upgrade paths.
        """
        self.upgrade_buttons.clear()
        padding = 15
        button_height = 60
        button_spacing = 10

        # --- Upgrade Path A ---
        next_upgrade_a = self.upgrade_manager.get_next_upgrade(self.tower, "path_a")
        if next_upgrade_a:
            can_afford_a = self.game_state.gold >= next_upgrade_a.cost
            button_rect_a = pygame.Rect(
                self.rect.x + padding,
                self.rect.y + 200,  # Position below the stats section
                self.rect.width - padding * 2,
                button_height,
            )
            self.upgrade_buttons.append(
                UpgradeButton(button_rect_a, next_upgrade_a, can_afford_a)
            )

        # --- Upgrade Path B ---
        next_upgrade_b = self.upgrade_manager.get_next_upgrade(self.tower, "path_b")
        if next_upgrade_b:
            can_afford_b = self.game_state.gold >= next_upgrade_b.cost
            # Position the second button below the first one.
            y_pos_b = self.rect.y + 200 + button_height + button_spacing
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
    ) -> Optional[str]:
        """
        Delegates event handling to child buttons.

        It checks each UpgradeButton to see if it was clicked and returns the
        corresponding action string if so.
        """
        # First, check if the mouse is even inside the panel. If not, do nothing.
        if not self.rect.collidepoint(pygame.mouse.get_pos()):
            return None

        # Pass the event to each button.
        for button in self.upgrade_buttons:
            action = button.handle_event(event, game_state)
            if action:
                return action
        return None

    def draw(self, screen: pygame.Surface):
        """Draws the panel and all its components."""
        # --- Draw Panel Background and Border ---
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors["bg"])
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=5)

        # --- Draw Text Information ---
        self._draw_text(screen)

        # --- Draw Child Buttons ---
        for button in self.upgrade_buttons:
            button.draw(screen, self.game_state)

    def _draw_text(self, screen: pygame.Surface):
        """Renders and blits all the text elements for the panel."""
        padding = 15
        line_height = 24
        current_y = self.rect.y + padding

        # Tower Name (Title)
        title_surf = self.font_title.render(self.tower.name, True, self.colors["title"])
        screen.blit(title_surf, (self.rect.x + padding, current_y))
        current_y += 40

        # Stats Header
        stats_header_surf = self.font_header.render(
            "Statistics", True, self.colors["header"]
        )
        screen.blit(stats_header_surf, (self.rect.x + padding, current_y))
        current_y += line_height + 5

        # Individual Stats
        stats_to_display = {
            "Damage": self.tower.damage,
            "Range": self.tower.range,
            "Fire Rate": f"{self.tower.fire_rate:.2f}/s",
            "Pierce": self.tower.pierce_count,
            "Projectiles": self.tower.projectiles_per_shot,
        }

        for label, value in stats_to_display.items():
            # Don't display stats that are zero (like Pierce on a base turret)
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
