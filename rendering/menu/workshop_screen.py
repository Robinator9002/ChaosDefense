# rendering/menu/workshop_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set

from ..common.ui.ui_element import UIElement
from ..common.text.text_renderer import render_text_wrapped
from game_logic.progression.progression_manager import ProgressionManager

logger = logging.getLogger(__name__)


class TowerUnlockButton(UIElement):
    """
    A UI element for unlocking a new tower in The Workshop.
    """

    def __init__(
        self, rect: pygame.Rect, tower_info: Dict[str, Any], purchase_callback: Callable
    ):
        super().__init__(rect)
        self.tower_id = tower_info["id"]
        self.name = tower_info["name"]
        self.description = tower_info["description"]
        self.cost = tower_info["cost"]
        self.is_unlocked = tower_info["unlocked"]
        self.purchase_callback = purchase_callback

        self.font_name = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 14)
        self.font_cost = pygame.font.SysFont("segoeui", 20, bold=True)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_unlocked": (35, 60, 45),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "border_unlocked": (70, 110, 85),
            "text_name": (210, 210, 220),
            "text_desc": (160, 160, 170),
            "text_unlocked": (180, 230, 190),
            "cost_can_afford": (255, 215, 0),
            "cost_cant_afford": (180, 40, 40),
        }

    def handle_event(self, event: pygame.event.Event, can_afford: bool) -> bool:
        """Handles clicks. If affordable and not unlocked, triggers purchase callback."""
        # The parent screen now calculates the hover state based on scroll position.
        if not self.is_unlocked and can_afford and self.is_hovered:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.purchase_callback(self.tower_id)
                return True
        return False

    def draw(self, screen: pygame.Surface, can_afford: bool):
        """Draws the button, showing its state (locked, unlocked, affordable)."""
        if self.is_unlocked:
            bg_color = self.colors["bg_unlocked"]
            border_color = self.colors["border_unlocked"]
            name_color = self.colors["text_unlocked"]
        else:
            bg_color = (
                self.colors["bg_hover"]
                if self.is_hovered and can_afford
                else self.colors["bg_default"]
            )
            border_color = (
                self.colors["border_hover"]
                if self.is_hovered and can_afford
                else self.colors["border_default"]
            )
            name_color = self.colors["text_name"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 10))

        if self.is_unlocked:
            status_surf = self.font_cost.render(
                "UNLOCKED", True, self.colors["text_unlocked"]
            )
            status_rect = status_surf.get_rect(
                topright=(self.rect.right - 15, self.rect.y + 12)
            )
            screen.blit(status_surf, status_rect)
        else:
            cost_color = (
                self.colors["cost_can_afford"]
                if can_afford
                else self.colors["cost_cant_afford"]
            )
            cost_surf = self.font_cost.render(f"{self.cost} CS", True, cost_color)
            cost_rect = cost_surf.get_rect(
                topright=(self.rect.right - 15, self.rect.y + 12)
            )
            screen.blit(cost_surf, cost_rect)

        desc_surfaces = render_text_wrapped(
            self.description,
            self.font_desc,
            self.colors["text_desc"],
            self.rect.width - 30,
        )
        current_y = self.rect.y + 45
        for line in desc_surfaces:
            screen.blit(line, (self.rect.x + 15, current_y))
            current_y += line.get_height()


class WorkshopScreen:
    """
    Manages and renders The Workshop UI, where players can permanently
    unlock towers and purchase global upgrades.

    REFACTORED: Now features a scrollable grid layout to accommodate a large
    number of unlockable items.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        progression_manager: ProgressionManager,
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.progression_manager = progression_manager
        self.back_callback = back_callback

        self.tower_buttons: List[TowerUnlockButton] = []
        self.back_button: UIElement = None

        # --- Scrolling State ---
        self.scroll_y = 0
        self.content_height = 0
        self.visible_height = 0
        self.max_scroll = 0
        self.is_scrollable = False

        self._setup_fonts_and_colors()
        self._build_layout()

    def _setup_fonts_and_colors(self):
        self.title_font = pygame.font.SysFont("segoeui", 52, bold=True)
        self.currency_font = pygame.font.SysFont("segoeui", 28, bold=True)
        self.back_font = pygame.font.SysFont("segoeui", 24, bold=True)
        self.section_font = pygame.font.SysFont("segoeui", 28, bold=True)
        self.colors = {
            "title": (220, 220, 230),
            "currency": (255, 215, 0),
            "section_header": (180, 180, 190),
            "back_button_text": (210, 210, 220),
            "back_bg_default": (40, 50, 60),
            "back_bg_hover": (60, 75, 90),
            "scrollbar_track": (30, 35, 45),
            "scrollbar_handle": (80, 90, 100),
        }

    def _build_layout(self):
        """Creates and positions all UI elements for the screen."""
        self.tower_buttons.clear()

        # --- Define Layout Constants ---
        padding = 50
        header_height = self.screen_rect.height * 0.15
        footer_height = 100
        self.visible_height = self.screen_rect.height - header_height - footer_height

        # --- Tower Unlocks Section ---
        tower_unlocks = self.progression_manager.get_unlockable_towers()
        button_width, button_height, spacing = 400, 90, 20
        columns = 2

        current_y = spacing  # Start with some padding

        # Tower Blueprints Header
        current_y += self.section_font.get_height() + spacing

        # Grid layout for buttons
        for i, tower_info in enumerate(tower_unlocks):
            col = i % columns
            row = i // columns
            x_pos = (
                self.screen_rect.centerx
                + ((col - 0.5) * (button_width + spacing))
                - (button_width / 2)
            )
            y_pos = current_y + (row * (button_height + spacing))

            button_rect = pygame.Rect(x_pos, y_pos, button_width, button_height)
            self.tower_buttons.append(
                TowerUnlockButton(button_rect, tower_info, self._purchase_tower)
            )

        # Calculate total content height
        num_rows = (len(self.tower_buttons) + columns - 1) // columns
        self.content_height = (
            (num_rows * (button_height + spacing))
            + self.section_font.get_height()
            + spacing
        )

        # Determine if scrolling is needed
        self.is_scrollable = self.content_height > self.visible_height
        self.max_scroll = max(0, self.content_height - self.visible_height)
        self.scroll_y = min(self.scroll_y, self.max_scroll)

        # --- Back Button ---
        back_button_rect = pygame.Rect(30, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)

    def _purchase_tower(self, tower_id: str):
        """Callback for when a purchase is attempted."""
        if self.progression_manager.purchase_tower(tower_id):
            # Rebuild the layout to reflect the new unlocked state
            self._build_layout()

    def handle_event(self, event: pygame.event.Event):
        """Delegates events to all interactive elements."""
        # --- Handle Scrolling ---
        if self.is_scrollable and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Scroll up
                self.scroll_y = max(0, self.scroll_y - 35)
            elif event.button == 5:  # Scroll down
                self.scroll_y = min(self.max_scroll, self.scroll_y + 35)

        # --- Handle Button Events ---
        current_currency = self.progression_manager.get_player_data().meta_currency

        # Calculate on-screen rects for hover detection
        header_height = self.screen_rect.height * 0.15
        for button in self.tower_buttons:
            on_screen_rect = button.rect.move(0, header_height - self.scroll_y)
            button.is_hovered = on_screen_rect.collidepoint(event.pos)

            can_afford = current_currency >= button.cost
            if button.handle_event(event, can_afford):
                return  # Event handled

        self.back_button.handle_event(event, game_state=None)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the entire Workshop screen with scrolling and clipping."""
        # --- Draw Static Header ---
        title_surf = self.title_font.render("The Workshop", True, self.colors["title"])
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.05
        )
        screen.blit(title_surf, title_rect)

        currency = self.progression_manager.get_player_data().meta_currency
        currency_text = f"Chaos Shards: {currency}"
        currency_surf = self.currency_font.render(
            currency_text, True, self.colors["currency"]
        )
        currency_rect = currency_surf.get_rect(
            topright=(self.screen_rect.right - 30, 30)
        )
        screen.blit(currency_surf, currency_rect)

        # --- Draw Scrollable Content ---
        header_height = self.screen_rect.height * 0.15
        content_area_rect = pygame.Rect(
            0, header_height, self.screen_rect.width, self.visible_height
        )

        # Draw section header
        section_surf = self.section_font.render(
            "Tower Blueprints", True, self.colors["section_header"]
        )
        screen.blit(section_surf, (50, header_height + 20 - self.scroll_y))

        # Set clipping area to prevent content from drawing outside the panel
        screen.set_clip(content_area_rect)

        current_currency = self.progression_manager.get_player_data().meta_currency
        for button in self.tower_buttons:
            # Create a temporary rect for drawing at the correct on-screen position
            original_rect = button.rect.copy()
            button.rect.topleft = (
                original_rect.x,
                original_rect.y + header_height - self.scroll_y,
            )

            can_afford = current_currency >= button.cost
            button.draw(screen, can_afford)

            button.rect = original_rect  # Restore original layout rect

        # Reset clipping area to draw the rest of the UI
        screen.set_clip(None)

        if self.is_scrollable:
            self._draw_scrollbar(screen, content_area_rect)

        # --- Draw Static Footer ---
        back_bg_color = (
            self.colors["back_bg_hover"]
            if self.back_button.is_hovered
            else self.colors["back_bg_default"]
        )
        pygame.draw.rect(screen, back_bg_color, self.back_button.rect, border_radius=8)
        back_text_surf = self.back_font.render(
            "Back", True, self.colors["back_button_text"]
        )
        back_text_rect = back_text_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_text_surf, back_text_rect)

    def _draw_scrollbar(self, screen: pygame.Surface, area: pygame.Rect):
        """Draws a custom scrollbar for the content area."""
        track_width = 10
        track_rect = pygame.Rect(
            area.right - track_width - 5, area.top, track_width, area.height
        )
        pygame.draw.rect(
            screen, self.colors["scrollbar_track"], track_rect, border_radius=5
        )

        if self.content_height > self.visible_height:
            handle_height = self.visible_height * (
                self.visible_height / self.content_height
            )
            handle_height = max(20, handle_height)
            scroll_ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
            handle_y = track_rect.y + (track_rect.height - handle_height) * scroll_ratio
            handle_rect = pygame.Rect(
                track_rect.x, handle_y, track_rect.width, handle_height
            )
            pygame.draw.rect(
                screen, self.colors["scrollbar_handle"], handle_rect, border_radius=5
            )
