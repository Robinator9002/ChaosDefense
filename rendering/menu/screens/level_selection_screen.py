# rendering/menu/screens/level_selection_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set, Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from ..components.scrollable_grid import ScrollableGrid
from ..panels.preview_panel import PreviewPanel
from ..buttons.list_item_button import ListItemButton

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class LevelSelectionScreen:
    """
    Manages and renders the level selection UI.
    REFACTORED: Now uses the consolidated ListItemButton for its level list,
    fixing all visual and interaction bugs.
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

        self.buttons: List[ListItemButton] = []
        self.selected_button: Optional[ListItemButton] = None

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
        """Creates the level buttons using the new ListItemButton."""
        self.buttons.clear()
        for level_id, level_data in self.level_configs.items():
            is_locked = level_id not in self.unlocked_levels

            button_data = {
                "id": level_id,
                "title": level_id.replace("_", " ").title(),
                "description": level_data.get("generation_params", {}).get(
                    "description", "No description available."
                ),
                "is_locked": is_locked,
                "item_data": level_data,  # Store original data
            }

            button = ListItemButton(
                pygame.Rect(0, 0, 0, 0),
                button_data,
                self.ui_theme,
                self.font_manager,
            )
            self.buttons.append(button)

        self.grid.update_item_count(len(self.buttons))

    def handle_event(self, event: pygame.event.Event):
        """
        Handles user input for the level selection screen with a clean,
        event-type-based structure.
        """
        # 1. Delegate events to child components that manage their own state
        self.grid.handle_scroll_event(event)
        self.preview_panel.handle_event(event)

        # 2. Handle MOUSEMOTION for hover effects
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            self.back_button.is_hovered = self.back_button.rect.collidepoint(mouse_pos)

            for i, button in enumerate(self.buttons):
                layout_rect = self.grid.get_item_rect(i)
                on_screen_rect = layout_rect.move(0, -self.grid.scroll_y)
                # --- FIX: Update the button's internal rect before checking for hover ---
                button.rect = on_screen_rect

                if self.grid.area.contains(on_screen_rect):
                    button.is_hovered = on_screen_rect.collidepoint(mouse_pos)
                else:
                    button.is_hovered = False

        # 3. Handle MOUSEBUTTONDOWN for clicks and selections
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.back_button.rect.collidepoint(mouse_pos):
                self.back_callback()
                return

            clicked_button = None
            for i, button in enumerate(self.buttons):
                layout_rect = self.grid.get_item_rect(i)
                on_screen_rect = layout_rect.move(0, -self.grid.scroll_y)
                # --- FIX: Update the button's internal rect before checking for clicks ---
                button.rect = on_screen_rect

                if self.grid.area.contains(
                    on_screen_rect
                ) and on_screen_rect.collidepoint(mouse_pos):
                    clicked_button = button
                    break

            if clicked_button:
                self.selected_button = clicked_button
                for btn in self.buttons:
                    btn.is_selected = btn == self.selected_button

                level_id = self.selected_button.item_data["id"]

                self.preview_panel.set_item(
                    item_data={
                        "id": level_id,
                        "name": self.selected_button.title,
                        "description": self.selected_button.item_data["description"],
                    },
                    button_text="Start Mission",
                    button_action=self.start_level_callback,
                    is_button_enabled=not self.selected_button.is_locked,
                )

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
            # Calculate final position here, just for drawing
            layout_rect = self.grid.get_item_rect(i)
            # --- FIX: Update the button's internal rect for drawing ---
            button.rect.topleft = (layout_rect.x, layout_rect.y - self.grid.scroll_y)
            button.draw(screen)
        screen.set_clip(None)

        self.grid.draw_scrollbar(screen)
