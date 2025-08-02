# rendering/menu/components/scrollable_grid.py
import pygame
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ScrollableGrid:
    """
    A helper class to manage the layout and scrolling logic for a grid of UI elements.
    REFACTORED: Now fully theme-driven for consistent scrollbar styling.
    """

    def __init__(
        self,
        area: pygame.Rect,
        item_size: Tuple[int, int],
        item_spacing: Tuple[int, int],
        columns: int,
        ui_theme: Dict[str, Any],
    ):
        """
        Initializes the ScrollableGrid manager.

        Args:
            area (pygame.Rect): The visible area for the grid content.
            item_size (Tuple[int, int]): The (width, height) of each grid item.
            item_spacing (Tuple[int, int]): The (h, v) spacing between items.
            columns (int): The number of columns in the grid.
            ui_theme (Dict[str, Any]): The UI theme dictionary.
        """
        self.area = area
        self.item_width, self.item_height = item_size
        self.spacing_x, self.spacing_y = item_spacing
        self.columns = columns

        # --- NEW: Load styles from theme ---
        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})

        # --- Scrolling State ---
        self.scroll_y = 0
        self.content_height = 0
        self.max_scroll = 0
        self.is_scrollable = False

    def update_item_count(self, num_items: int):
        """
        Recalculates the grid's total height and scrolling parameters.
        """
        if self.columns <= 0:
            return

        num_rows = (num_items + self.columns - 1) // self.columns
        self.content_height = (num_rows * self.item_height) + (
            max(0, num_rows - 1) * self.spacing_y
        )

        self.is_scrollable = self.content_height > self.area.height
        self.max_scroll = max(0, self.content_height - self.area.height)
        self.scroll_y = min(self.scroll_y, self.max_scroll)

    def get_item_rect(self, index: int) -> pygame.Rect:
        """
        Calculates the layout position for an item at a given index.
        """
        col = index % self.columns
        row = index // self.columns

        total_grid_width = (self.columns * self.item_width) + (
            max(0, self.columns - 1) * self.spacing_x
        )
        start_x = self.area.x + (self.area.width - total_grid_width) / 2

        x_pos = start_x + col * (self.item_width + self.spacing_x)
        y_pos = self.area.y + row * (self.item_height + self.spacing_y)

        return pygame.Rect(x_pos, y_pos, self.item_width, self.item_height)

    def handle_scroll_event(self, event: pygame.event.Event):
        """Processes mouse wheel events to update the scroll offset."""
        if self.is_scrollable and event.type == pygame.MOUSEBUTTONDOWN:
            if self.area.collidepoint(pygame.mouse.get_pos()):
                if event.button == 4:  # Scroll up
                    self.scroll_y = max(0, self.scroll_y - 40)
                elif event.button == 5:  # Scroll down
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 40)

    def draw_scrollbar(self, screen: pygame.Surface):
        """Draws a visual scrollbar next to the grid area using theme styles."""
        if not self.is_scrollable:
            return

        # --- NEW: Use theme for styling ---
        track_color = self.colors.get("scrollbar_track", (30, 35, 45))
        handle_color = self.colors.get("scrollbar_handle", (80, 90, 100))
        track_width = self.layout.get("scrollbar_width", 10)
        border_radius = self.layout.get("border_radius_small", 5)

        track_rect = pygame.Rect(
            self.area.right + 5, self.area.top, track_width, self.area.height
        )
        handle_height = self.area.height * (self.area.height / self.content_height)
        handle_height = max(20, handle_height)

        scroll_ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
        handle_y = track_rect.y + (track_rect.height - handle_height) * scroll_ratio
        handle_rect = pygame.Rect(
            track_rect.x, handle_y, track_rect.width, handle_height
        )

        pygame.draw.rect(screen, track_color, track_rect, border_radius=border_radius)
        pygame.draw.rect(screen, handle_color, handle_rect, border_radius=border_radius)
