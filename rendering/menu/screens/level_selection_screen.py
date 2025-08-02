# rendering/menu/screens/level_selection_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set, Optional

from rendering.common.ui.ui_element import UIElement
from rendering.common.text.text_renderer import render_text_wrapped

# --- NEW: Import reusable components ---
from ..components.scrollable_grid import ScrollableGrid
from ..panels.preview_panel import PreviewPanel

logger = logging.getLogger(__name__)


class LevelButton(UIElement):
    """
    A UI element representing a single, clickable level in the selection screen.
    Its primary job is now to draw itself and report hover status.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        level_id: str,
        level_data: Dict[str, Any],
        is_locked: bool,
    ):
        super().__init__(rect)
        self.level_id = level_id
        self.level_data = level_data
        self.name = level_id.replace("_", " ").title()
        self.description = level_data.get("generation_params", {}).get(
            "description", "No description available."
        )
        self.is_locked = is_locked

        self.font_name = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 14)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_selected": (75, 95, 115),
            "bg_locked": (30, 35, 40),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "border_locked": (50, 55, 60),
            "text_name": (210, 210, 220),
            "text_desc": (160, 160, 170),
            "text_locked": (100, 100, 110),
        }
        self.is_selected = False  # New state to show which item is in the preview

    def draw(self, screen: pygame.Surface):
        """Draws the level button to the screen."""
        if self.is_locked:
            bg_color = self.colors["bg_locked"]
            border_color = self.colors["border_locked"]
            name_color = self.colors["text_locked"]
        else:
            if self.is_selected:
                bg_color = self.colors["bg_selected"]
            else:
                bg_color = (
                    self.colors["bg_hover"]
                    if self.is_hovered
                    else self.colors["bg_default"]
                )
            border_color = (
                self.colors["border_hover"]
                if self.is_hovered or self.is_selected
                else self.colors["border_default"]
            )
            name_color = self.colors["text_name"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 10))


class LevelSelectionScreen:
    """
    Manages and renders the level selection UI.

    REFACTORED: Now uses a two-column layout with a reusable ScrollableGrid
    for the level list and a PreviewPanel for displaying details.
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
        self.level_configs = {
            k: v for k, v in level_configs.items() if isinstance(v, dict)
        }
        self.unlocked_levels = unlocked_levels
        self.start_level_callback = start_level_callback
        self.back_callback = back_callback

        self.buttons: List[LevelButton] = []
        self.selected_level: Optional[LevelButton] = None

        self._setup_components()
        self._build_layout()

    def _setup_components(self):
        """Initializes the core UI components like the grid and preview panel."""
        # Define layout areas
        grid_area_width = self.screen_rect.width * 0.5
        preview_area_width = self.screen_rect.width * 0.4
        grid_area = pygame.Rect(50, 120, grid_area_width, self.screen_rect.height - 200)
        preview_area = pygame.Rect(
            grid_area.right + 50, 120, preview_area_width, self.screen_rect.height * 0.7
        )

        # Initialize Grid
        self.grid = ScrollableGrid(
            area=grid_area,
            item_size=(int(grid_area_width * 0.9), 80),
            item_spacing=(20, 20),
            columns=1,
        )

        # Initialize Preview Panel
        self.preview_panel = PreviewPanel(preview_area)

        # Back Button
        back_button_rect = pygame.Rect(30, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)
        self.back_font = pygame.font.SysFont("segoeui", 24, bold=True)
        self.title_font = pygame.font.SysFont("segoeui", 52, bold=True)

    def _build_layout(self):
        """Creates the level buttons and populates the grid."""
        self.buttons.clear()

        for level_id, level_data in self.level_configs.items():
            is_locked = level_id not in self.unlocked_levels
            # Initial rect is temporary; the grid will position it.
            button = LevelButton(
                pygame.Rect(0, 0, 0, 0), level_id, level_data, is_locked
            )
            self.buttons.append(button)

        self.grid.update_item_count(len(self.buttons))

    def handle_event(self, event: pygame.event.Event):
        """Delegates events to the grid, preview panel, and back button."""
        self.grid.handle_scroll_event(event)
        self.preview_panel.handle_event(event)

        mouse_pos = pygame.mouse.get_pos()

        # Handle hover and selection logic for level buttons
        hovered_button = None
        for i, button in enumerate(self.buttons):
            # Get the button's position from the grid helper
            layout_rect = self.grid.get_item_rect(i)
            # Calculate its on-screen position, accounting for scroll
            on_screen_rect = layout_rect.move(0, -self.grid.scroll_y)

            if self.grid.area.contains(on_screen_rect):
                button.is_hovered = on_screen_rect.collidepoint(mouse_pos)
                if button.is_hovered:
                    hovered_button = button
            else:
                button.is_hovered = False

        # Update preview panel based on hover state
        if hovered_button and hovered_button != self.selected_level:
            self.selected_level = hovered_button
            for btn in self.buttons:  # Update selection visual state
                btn.is_selected = btn == self.selected_level

            self.preview_panel.set_item(
                item_data={
                    "id": self.selected_level.level_id,
                    "name": self.selected_level.name,
                    "description": self.selected_level.description,
                },
                button_text="Start Mission",
                button_action=self.start_level_callback,
                is_button_enabled=not self.selected_level.is_locked,
            )

        # Handle back button
        self.back_button.is_hovered = self.back_button.rect.collidepoint(mouse_pos)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the entire level selection screen."""
        # --- Static Header & Footer ---
        title_surf = self.title_font.render("Select Mission", True, (220, 220, 230))
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.05
        )
        screen.blit(title_surf, title_rect)

        back_bg_color = (60, 75, 90) if self.back_button.is_hovered else (40, 50, 60)
        pygame.draw.rect(screen, back_bg_color, self.back_button.rect, border_radius=8)
        back_text_surf = self.back_font.render("Back", True, (210, 210, 220))
        back_text_rect = back_text_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_text_surf, back_text_rect)

        # --- Components ---
        self.preview_panel.draw(screen)

        # --- Scrollable Content ---
        screen.set_clip(self.grid.area)
        for i, button in enumerate(self.buttons):
            layout_rect = self.grid.get_item_rect(i)
            button.rect.topleft = (layout_rect.x, layout_rect.y - self.grid.scroll_y)
            button.draw(screen)
        screen.set_clip(None)

        self.grid.draw_scrollbar(screen)
