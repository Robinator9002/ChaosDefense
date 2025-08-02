# rendering/menu/screens/level_selection_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set

from rendering.common.ui.ui_element import UIElement
from rendering.common.text.text_renderer import render_text_wrapped

logger = logging.getLogger(__name__)


class LevelButton(UIElement):
    """
    A UI element representing a single, clickable level in the selection screen.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        level_id: str,
        level_data: Dict[str, Any],
        is_locked: bool,
        action: Callable,
    ):
        super().__init__(rect)
        self.level_id = level_id
        self.name = level_id.replace("_", " ").title()
        self.description = level_data.get("generation_params", {}).get(
            "description", "No description available."
        )
        self.is_locked = is_locked
        self.action = action

        self.font_name = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 14)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_locked": (30, 35, 40),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "border_locked": (50, 55, 60),
            "text_name": (210, 210, 220),
            "text_desc": (160, 160, 170),
            "text_locked": (100, 100, 110),
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles mouse clicks. If not locked, it executes its action."""
        if not self.is_locked and self.is_hovered:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.action(self.level_id)
                return True
        return False

    def draw(self, screen: pygame.Surface):
        """Draws the level button to the screen."""
        if self.is_locked:
            bg_color = self.colors["bg_locked"]
            border_color = self.colors["border_locked"]
            name_color = self.colors["text_locked"]
            desc_color = self.colors["text_locked"]
        else:
            bg_color = (
                self.colors["bg_hover"]
                if self.is_hovered
                else self.colors["bg_default"]
            )
            border_color = (
                self.colors["border_hover"]
                if self.is_hovered
                else self.colors["border_default"]
            )
            name_color = self.colors["text_name"]
            desc_color = self.colors["text_desc"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 10))

        desc_surfaces = render_text_wrapped(
            self.description, self.font_desc, desc_color, self.rect.width - 30
        )
        current_y = self.rect.y + 45
        for line in desc_surfaces:
            screen.blit(line, (self.rect.x + 15, current_y))
            current_y += line.get_height()


class LevelSelectionScreen:
    """
    Manages and renders the level selection UI, allowing the player to choose
    which map to play on.

    REFACTORED: Now uses a scrollable grid layout to support many levels.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        level_configs: Dict[str, Any],
        unlocked_levels: Set[str],
        start_level_callback: Callable,
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.level_configs = level_configs
        self.unlocked_levels = unlocked_levels
        self.start_level_callback = start_level_callback
        self.back_callback = back_callback

        self.buttons: List[LevelButton] = []
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
        self.back_font = pygame.font.SysFont("segoeui", 24, bold=True)
        self.colors = {
            "title": (220, 220, 230),
            "back_text": (210, 210, 220),
            "back_bg_default": (40, 50, 60),
            "back_bg_hover": (60, 75, 90),
            "scrollbar_track": (30, 35, 45),
            "scrollbar_handle": (80, 90, 100),
        }

    def _build_layout(self):
        """Creates and positions all UI elements for the screen."""
        self.buttons.clear()

        header_height = self.screen_rect.height * 0.2
        footer_height = 100
        self.visible_height = self.screen_rect.height - header_height - footer_height

        button_width, button_height, spacing = 450, 100, 25
        columns = 2

        # Filter out non-dictionary items like comments from the configs
        valid_levels = {
            k: v for k, v in self.level_configs.items() if isinstance(v, dict)
        }

        current_y = spacing
        for i, (level_id, level_data) in enumerate(valid_levels.items()):
            is_locked = level_id not in self.unlocked_levels

            col = i % columns
            row = i // columns
            x_pos = (
                self.screen_rect.centerx
                + ((col - 0.5) * (button_width + spacing))
                - (button_width / 2)
            )
            y_pos = current_y + (row * (button_height + spacing))

            button_rect = pygame.Rect(x_pos, y_pos, button_width, button_height)
            self.buttons.append(
                LevelButton(
                    button_rect,
                    level_id,
                    level_data,
                    is_locked,
                    self.start_level_callback,
                )
            )

        num_rows = (len(self.buttons) + columns - 1) // columns
        self.content_height = (num_rows * (button_height + spacing)) + spacing

        self.is_scrollable = self.content_height > self.visible_height
        self.max_scroll = max(0, self.content_height - self.visible_height)
        self.scroll_y = min(self.scroll_y, self.max_scroll)

        back_button_rect = pygame.Rect(30, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)

    def handle_event(self, event: pygame.event.Event):
        """Delegates events to the level buttons and the back button."""
        mouse_pos = pygame.mouse.get_pos()

        if self.is_scrollable and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll_y = max(0, self.scroll_y - 35)
            elif event.button == 5:
                self.scroll_y = min(self.max_scroll, self.scroll_y + 35)

        header_height = self.screen_rect.height * 0.2
        for button in self.buttons:
            on_screen_rect = button.rect.move(0, header_height - self.scroll_y)
            button.is_hovered = on_screen_rect.collidepoint(mouse_pos)
            if button.handle_event(event):
                return

        self.back_button.is_hovered = self.back_button.rect.collidepoint(mouse_pos)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the entire level selection screen."""
        # --- Static Header ---
        title_surf = self.title_font.render(
            "Select Mission", True, self.colors["title"]
        )
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.1
        )
        screen.blit(title_surf, title_rect)

        # --- Scrollable Content ---
        header_height = self.screen_rect.height * 0.2
        content_area_rect = pygame.Rect(
            0, header_height, self.screen_rect.width, self.visible_height
        )
        screen.set_clip(content_area_rect)

        for button in self.buttons:
            original_rect = button.rect.copy()
            button.rect.topleft = (
                original_rect.x,
                original_rect.y + header_height - self.scroll_y,
            )
            button.draw(screen)
            button.rect = original_rect

        screen.set_clip(None)

        if self.is_scrollable:
            self._draw_scrollbar(screen, content_area_rect)

        # --- Static Footer ---
        back_bg_color = (
            self.colors["back_bg_hover"]
            if self.back_button.is_hovered
            else self.colors["back_bg_default"]
        )
        pygame.draw.rect(screen, back_bg_color, self.back_button.rect, border_radius=8)
        back_text_surf = self.back_font.render("Back", True, self.colors["back_text"])
        back_text_rect = back_text_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_text_surf, back_text_rect)

    def _draw_scrollbar(self, screen: pygame.Surface, area: pygame.Rect):
        """Draws a custom scrollbar for the content area."""
        track_width = 10
        track_rect = pygame.Rect(
            area.right - track_width - 15, area.top + 5, track_width, area.height - 10
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
