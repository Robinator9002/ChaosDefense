# rendering/menu/screens/level_selection_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set, Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from ..components.scrollable_grid import ScrollableGrid
from ..panels.preview_panel import PreviewPanel

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class LevelButton(UIElement):
    """
    A UI element representing a single, clickable level.

    REFACTORED: Now fully theme-driven. It features a much clearer visual
    distinction for hover and selected states to improve user experience.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        level_id: str,
        level_data: Dict[str, Any],
        is_locked: bool,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.level_id = level_id
        self.level_data = level_data
        self.name = level_id.replace("_", " ").title()
        self.description = level_data.get("generation_params", {}).get(
            "description", "No description available."
        )
        self.is_locked = is_locked
        self.is_selected = False

        # --- NEW: Load styles from theme ---
        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font_name = font_manager.get_font("body_large")
        self.font_locked = font_manager.get_font(
            "title_small"
        )  # Larger for the lock icon

    def draw(self, screen: pygame.Surface):
        """Draws the level button using theme-defined styles."""
        border_width = self.layout.get("border_width_standard", 2)
        border_radius = self.layout.get("border_radius_large", 8)

        # Determine colors based on state
        if self.is_locked:
            bg_color = self.colors.get("panel_primary")
            border_color = self.colors.get("border_primary")
            name_color = self.colors.get("text_disabled")
        else:
            name_color = self.colors.get("text_primary")
            if self.is_selected:
                bg_color = self.colors.get("panel_secondary")
                border_color = self.colors.get("border_accent")
                border_width = self.layout.get("border_width_selected", 3)
            elif self.is_hovered:
                bg_color = self.colors.get("panel_interactive_hover")
                border_color = self.colors.get("border_primary")
            else:
                bg_color = self.colors.get("panel_primary")
                border_color = self.colors.get("border_primary")

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)
        pygame.draw.rect(
            screen, border_color, self.rect, border_width, border_radius=border_radius
        )

        # Draw Text Content
        padding = self.layout.get("padding_medium", 15)
        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + padding, self.rect.y + padding))

        if self.is_locked:
            lock_surf = self.font_locked.render(
                "🔒", True, self.colors.get("text_disabled")
            )
            lock_rect = lock_surf.get_rect(
                centery=self.rect.centery, right=self.rect.right - padding
            )
            screen.blit(lock_surf, lock_rect)


class LevelSelectionScreen:
    """
    Manages and renders the level selection UI.

    REFACTORED: Now fully theme-driven, passing the theme and font manager
    to all its child components for consistent styling.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        level_configs: Dict[str, Any],
        unlocked_levels: Set[str],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
        start_level_callback: Callable,
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.level_configs = {
            k: v for k, v in level_configs.items() if isinstance(v, dict)
        }
        self.unlocked_levels = unlocked_levels
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.start_level_callback = start_level_callback
        self.back_callback = back_callback

        self.buttons: List[LevelButton] = []
        self.selected_level: Optional[LevelButton] = None

        self._load_theme_assets()
        self._setup_components()
        self._build_layout()

    def _load_theme_assets(self):
        """Loads styles and fonts needed for the screen itself."""
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("title_medium")
        self.font_back_button = self.font_manager.get_font("button_large")

    def _setup_components(self):
        """Initializes the core UI components like the grid and preview panel."""
        padding = self.layout.get("padding_large", 20)
        grid_area_width = self.screen_rect.width * 0.5
        preview_area_width = self.screen_rect.width * 0.4
        grid_area = pygame.Rect(
            padding * 2, 120, grid_area_width, self.screen_rect.height - 200
        )
        preview_area = pygame.Rect(
            grid_area.right + padding * 2,
            120,
            preview_area_width,
            self.screen_rect.height * 0.7,
        )

        self.grid = ScrollableGrid(
            area=grid_area,
            item_size=(int(grid_area.width * 0.9), 80),
            item_spacing=(padding, padding),
            columns=1,
            ui_theme=self.ui_theme,
        )

        self.preview_panel = PreviewPanel(
            preview_area, self.ui_theme, self.font_manager
        )

        back_button_rect = pygame.Rect(padding, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)

    def _build_layout(self):
        """Creates the level buttons and populates the grid."""
        self.buttons.clear()
        for level_id, level_data in self.level_configs.items():
            is_locked = level_id not in self.unlocked_levels
            button = LevelButton(
                pygame.Rect(0, 0, 0, 0),
                level_id,
                level_data,
                is_locked,
                self.ui_theme,
                self.font_manager,
            )
            self.buttons.append(button)
        self.grid.update_item_count(len(self.buttons))

    def handle_event(self, event: pygame.event.Event):
        """Delegates events to the grid, preview panel, and back button."""
        self.grid.handle_scroll_event(event)
        self.preview_panel.handle_event(event)
        mouse_pos = pygame.mouse.get_pos()

        hovered_button = None
        for i, button in enumerate(self.buttons):
            layout_rect = self.grid.get_item_rect(i)
            on_screen_rect = layout_rect.move(0, -self.grid.scroll_y)
            if self.grid.area.contains(on_screen_rect):
                button.rect.topleft = (
                    on_screen_rect.topleft
                )  # Update real position for hover check
                button.is_hovered = button.rect.collidepoint(mouse_pos)
                if button.is_hovered:
                    hovered_button = button
            else:
                button.is_hovered = False

        if hovered_button and hovered_button != self.selected_level:
            self.selected_level = hovered_button
            for btn in self.buttons:
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

        self.back_button.is_hovered = self.back_button.rect.collidepoint(mouse_pos)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
        """Draws the entire level selection screen using theme styles."""
        # Title
        title_surf = self.font_title.render(
            "Select Mission", True, self.colors.get("text_primary")
        )
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.05
        )
        screen.blit(title_surf, title_rect)

        # Back Button
        back_bg_color = (
            self.colors.get("panel_interactive_hover")
            if self.back_button.is_hovered
            else self.colors.get("panel_secondary")
        )
        pygame.draw.rect(
            screen,
            back_bg_color,
            self.back_button.rect,
            border_radius=self.layout.get("border_radius_large"),
        )
        back_text_surf = self.font_back_button.render(
            "Back", True, self.colors.get("text_primary")
        )
        back_text_rect = back_text_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_text_surf, back_text_rect)

        # Components
        self.preview_panel.draw(screen)

        # Scrollable Content
        screen.set_clip(self.grid.area)
        for i, button in enumerate(self.buttons):
            layout_rect = self.grid.get_item_rect(i)
            # The button's rect is already updated in handle_event, so we can just use it
            button.rect.topleft = (layout_rect.x, layout_rect.y - self.grid.scroll_y)
            button.draw(screen)
        screen.set_clip(None)

        self.grid.draw_scrollbar(screen)
