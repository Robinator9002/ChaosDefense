# rendering/menu/screens/workshop_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from game_logic.progression.progression_manager import ProgressionManager
from ..components.scrollable_grid import ScrollableGrid
from ..panels.preview_panel import PreviewPanel
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

# --- NEW: Import the consolidated ListItemButton ---
from ..buttons.list_item_button import ListItemButton

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class WorkshopButton(UIElement):
    """A generic button for the Workshop screen, used for category filters."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        action: Callable,
        is_active: bool,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.text = text
        self.action = action
        self.is_active = is_active
        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font = font_manager.get_font("button_medium")

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if (
            self.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.action()

    def draw(self, screen: pygame.Surface):
        border_radius = self.layout.get("border_radius_small", 5)
        # --- FIX: Use border_interactive_selected for consistency ---
        if self.is_active:
            bg_color = self.colors.get("panel_interactive_hover")
            text_color = self.colors.get("text_primary")
            border_color = self.colors.get("border_interactive_selected")
        else:
            bg_color = (
                self.colors.get("panel_interactive_hover")
                if self.is_hovered
                else self.colors.get("panel_secondary")
            )
            text_color = self.colors.get("text_primary")
            border_color = self.colors.get("border_primary")

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)
        pygame.draw.rect(
            screen, border_color, self.rect, 2, border_radius=border_radius
        )
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


# --- REMOVED: The old TowerUnlockButton class is now obsolete ---


class WorkshopScreen:
    """
    Manages The Workshop UI.
    REFACTORED: Now uses the consolidated ListItemButton for its tower list.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        progression_manager: ProgressionManager,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.progression_manager = progression_manager
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.back_callback = back_callback

        self.filtered_towers_data: List[Dict[str, Any]] = []
        # --- MODIFIED: The list now holds the new, generic button type ---
        self.tower_buttons: List[ListItemButton] = []
        self.selected_tower_button: Optional[ListItemButton] = None
        self.active_filter = "All"
        self.filter_buttons: List[WorkshopButton] = []

        self._load_theme_assets()
        self._setup_components()
        self._build_layout()

    def _load_theme_assets(self):
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("title_medium")
        self.font_currency = self.font_manager.get_font("title_small")
        self.font_back_button = self.font_manager.get_font("button_large")

    def _setup_components(self):
        padding = self.layout.get("padding_large", 20)
        grid_area = pygame.Rect(
            padding * 2,
            160,
            self.screen_rect.width * 0.5,
            self.screen_rect.height - 240,
        )
        preview_area = pygame.Rect(
            grid_area.right + padding * 2,
            160,
            self.screen_rect.width * 0.35,
            self.screen_rect.height * 0.7,
        )

        self.grid = ScrollableGrid(
            area=grid_area,
            item_size=(int(grid_area.width * 0.45), 110),
            item_spacing=(padding, padding),
            columns=2,
            ui_theme=self.ui_theme,
        )
        self.preview_panel = PreviewPanel(
            preview_area, self.ui_theme, self.font_manager
        )
        back_button_rect = pygame.Rect(padding, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)

    def _build_layout(self):
        """Filters tower data and builds the UI with new ListItemButtons."""
        # First, get the latest tower data
        all_unlockable_towers = self.progression_manager.get_unlockable_towers()
        all_tower_configs = self.progression_manager.all_tower_configs

        # Filter the raw data
        if self.active_filter.lower() == "all":
            self.filtered_towers_data = all_unlockable_towers
        else:
            self.filtered_towers_data = [
                t
                for t in all_unlockable_towers
                if all_tower_configs.get(t["id"], {}).get("category")
                == self.active_filter
            ]

        # Now, create the button objects from the filtered data
        self.tower_buttons.clear()
        for tower_data in self.filtered_towers_data:
            full_config = all_tower_configs.get(tower_data["id"], {})
            tower_info_full = {**full_config, **tower_data}

            # --- NEW: Prepare data specifically for the ListItemButton ---
            player_currency = self.progression_manager.get_player_data().meta_currency
            can_afford = player_currency >= tower_info_full.get("cost", 0)

            status_text = f"{tower_info_full.get('cost', 0)} CS"
            if tower_info_full.get("unlocked"):
                status_text = "UNLOCKED"

            stats = []
            stats_to_display = tower_info_full.get("info_panel_stats", [])
            for stat_info in stats_to_display[:3]:
                label = stat_info.get("label", "N/A")
                value_path = stat_info.get("value_path")
                value = (
                    get_nested_value(tower_info_full, value_path)
                    if value_path
                    else "N/A"
                )
                if value is None:
                    continue
                value_str = format_stat_value(value, stat_info.get("format"))
                stats.append((label, value_str))

            button_data = {
                "id": tower_info_full.get("id"),
                "title": tower_info_full.get("name", "N/A"),
                "is_locked": False,  # Workshop items are never "locked", just not purchased
                "can_afford": can_afford,
                "status_text": status_text,
                "stats": stats,
            }

            button = ListItemButton(
                pygame.Rect(0, 0, 0, 0), button_data, self.ui_theme, self.font_manager
            )
            self.tower_buttons.append(button)

        self.grid.update_item_count(len(self.tower_buttons))
        self._build_filter_buttons()

    def _build_filter_buttons(self):
        """Creates the category filter buttons."""
        self.filter_buttons.clear()
        all_tower_configs = self.progression_manager.all_tower_configs
        all_unlockable_towers = self.progression_manager.get_unlockable_towers()
        all_categories = sorted(
            list(
                set(
                    all_tower_configs.get(t["id"], {}).get("category", "N/A")
                    for t in all_unlockable_towers
                )
            )
        )
        categories = ["All"] + [cat for cat in all_categories if cat != "N/A"]

        btn_width, btn_height, btn_spacing = (
            120,
            35,
            self.layout.get("spacing_medium", 10),
        )
        start_x = self.grid.area.left
        for i, category in enumerate(categories):
            rect = pygame.Rect(
                start_x + i * (btn_width + btn_spacing),
                self.grid.area.top - btn_height - 10,
                btn_width,
                btn_height,
            )
            btn = WorkshopButton(
                rect,
                category.title(),
                lambda c=category.lower(): self.set_filter(c),
                is_active=(self.active_filter == category.lower()),
                ui_theme=self.ui_theme,
                font_manager=self.font_manager,
            )
            self.filter_buttons.append(btn)

    def set_filter(self, category: str):
        self.active_filter = category
        self.selected_tower_button = None
        self.preview_panel.set_item(None, "", lambda: None)
        self._build_layout()

    def _purchase_tower(self, tower_id: str):
        if self.progression_manager.purchase_tower(tower_id):
            self.set_filter(self.active_filter)

    def handle_event(self, event: pygame.event.Event):
        """Handles user input for the workshop screen."""
        mouse_pos = pygame.mouse.get_pos()

        # Update hover states for all interactive elements
        self.back_button.is_hovered = self.back_button.rect.collidepoint(mouse_pos)
        for btn in self.filter_buttons:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)

        hovered_button_index: Optional[int] = None
        for i, button in enumerate(self.tower_buttons):
            layout_rect = self.grid.get_item_rect(i)
            on_screen_rect = layout_rect.move(0, -self.grid.scroll_y)
            # --- FIX: Update the button's internal rect before checking for hover ---
            button.rect = on_screen_rect

            # --- FIX: Use colliderect instead of contains for more lenient click detection ---
            if self.grid.area.colliderect(
                on_screen_rect
            ) and on_screen_rect.collidepoint(mouse_pos):
                button.is_hovered = True
                hovered_button_index = i
            else:
                button.is_hovered = False

        # Delegate events to child components
        self.grid.handle_scroll_event(event)
        self.preview_panel.handle_event(event)
        for btn in self.filter_buttons:
            btn.handle_event(event)

        # Handle primary actions (clicks)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button.is_hovered:
                self.back_callback()
                return

            if hovered_button_index is not None:
                self.selected_tower_button = self.tower_buttons[hovered_button_index]
                for btn in self.tower_buttons:
                    btn.is_selected = btn == self.selected_tower_button

                # Get the full data for the preview panel
                selected_tower_data = self.filtered_towers_data[hovered_button_index]
                full_config = self.progression_manager.all_tower_configs.get(
                    selected_tower_data["id"], {}
                )
                tower_info_full = {**full_config, **selected_tower_data}

                can_afford = (
                    self.progression_manager.get_player_data().meta_currency
                    >= tower_info_full["cost"]
                )

                self.preview_panel.set_item(
                    item_data=tower_info_full,
                    button_text=f"Unlock ({tower_info_full['cost']} CS)",
                    button_action=lambda: self._purchase_tower(tower_info_full["id"]),
                    is_button_enabled=not tower_info_full["unlocked"] and can_afford,
                )

    def draw(self, screen: pygame.Surface):
        # Draw static elements
        title_surf = self.font_title.render(
            "The Workshop", True, self.colors.get("text_primary")
        )
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.05
        )
        screen.blit(title_surf, title_rect)

        currency = self.progression_manager.get_player_data().meta_currency
        currency_surf = self.font_currency.render(
            f"Chaos Shards: {currency}", True, self.colors.get("text_accent")
        )
        currency_rect = currency_surf.get_rect(
            topright=(self.screen_rect.right - 30, 30)
        )
        screen.blit(currency_surf, currency_rect)

        back_bg = (
            self.colors.get("panel_interactive_hover")
            if self.back_button.is_hovered
            else self.colors.get("panel_secondary")
        )
        pygame.draw.rect(
            screen,
            back_bg,
            self.back_button.rect,
            border_radius=self.layout.get("border_radius_large"),
        )
        back_surf = self.font_back_button.render(
            "Back", True, self.colors.get("text_primary")
        )
        back_text_rect = back_surf.get_rect(center=self.back_button.rect.center)
        screen.blit(back_surf, back_text_rect)

        # Draw child components
        self.preview_panel.draw(screen)
        for btn in self.filter_buttons:
            btn.draw(screen)

        # Draw scrollable content
        screen.set_clip(self.grid.area)
        for i, button in enumerate(self.tower_buttons):
            # The button's rect is updated in handle_event, so we can just draw it
            layout_rect = self.grid.get_item_rect(i)
            # --- FIX: Update the button's internal rect for drawing ---
            button.rect.topleft = (layout_rect.x, layout_rect.y - self.grid.scroll_y)
            button.draw(screen)
        screen.set_clip(None)

        self.grid.draw_scrollbar(screen)
