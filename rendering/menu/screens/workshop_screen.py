# rendering/menu/screens/workshop_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from game_logic.progression.progression_manager import ProgressionManager
from ..components.scrollable_grid import ScrollableGrid
from ..panels.preview_panel import PreviewPanel
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class WorkshopButton(UIElement):
    """
    A generic button for the Workshop screen, used for category filters.
    REFACTORED: Now fully theme-driven.
    """

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
        if (
            self.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.action()

    def draw(self, screen: pygame.Surface):
        border_radius = self.layout.get("border_radius_small", 5)
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


class TowerUnlockButton(UIElement):
    """
    A UI element for unlocking a new tower in The Workshop.
    REFACTORED: Redesigned with theme-driven styles for better visual clarity.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower_info: Dict[str, Any],
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.tower_info = tower_info
        self.name = tower_info["name"]
        self.is_unlocked = tower_info["unlocked"]
        self.is_selected = False

        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font_name = font_manager.get_font("body_medium", bold=True)
        self.font_cost = font_manager.get_font("body_medium", bold=True)
        self.font_stat_label = font_manager.get_font("body_tiny")
        self.font_stat_value = font_manager.get_font("body_tiny", bold=True)

        self._prepare_stat_surfaces()

    def _prepare_stat_surfaces(self):
        """Pre-renders the stat text for drawing."""
        self.stat_surfaces = []
        stats_to_display = self.tower_info.get("info_panel_stats", [])
        stat_label_color = self.colors.get("text_secondary")
        stat_value_color = self.colors.get("text_primary")

        for stat_info in stats_to_display[:3]:
            label = stat_info.get("label", "N/A")
            value_path = stat_info.get("value_path")
            value = (
                get_nested_value(self.tower_info, value_path) if value_path else "N/A"
            )
            if value is None:
                continue
            value_str = format_stat_value(value, stat_info.get("format"))
            label_surf = self.font_stat_label.render(
                f"{label}:", True, stat_label_color
            )
            value_surf = self.font_stat_value.render(value_str, True, stat_value_color)
            self.stat_surfaces.append((label_surf, value_surf))

    def draw(self, screen: pygame.Surface, can_afford: bool):
        border_radius = self.layout.get("border_radius_large", 8)
        border_width = self.layout.get("border_width_standard", 2)
        padding = self.layout.get("padding_medium", 15)

        if self.is_unlocked:
            bg_color = self.colors.get("panel_primary")
            border_color = self.colors.get("text_success")
            name_color = self.colors.get("text_success")
        else:
            name_color = self.colors.get("text_primary")
            if self.is_selected:
                bg_color = self.colors.get("panel_secondary")
                border_color = self.colors.get("border_accent")
                border_width = self.layout.get("border_width_selected", 3)
            else:
                bg_color = (
                    self.colors.get("panel_interactive_hover")
                    if self.is_hovered
                    else self.colors.get("panel_primary")
                )
                border_color = self.colors.get("border_primary")

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)
        pygame.draw.rect(
            screen, border_color, self.rect, border_width, border_radius=border_radius
        )

        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + padding, self.rect.y + 10))

        if self.is_unlocked:
            status_surf = self.font_cost.render(
                "UNLOCKED", True, self.colors.get("text_success")
            )
        else:
            cost_color = (
                self.colors.get("text_accent")
                if can_afford
                else self.colors.get("text_error")
            )
            cost_text = f"{self.tower_info['cost']} CS"
            status_surf = self.font_cost.render(cost_text, True, cost_color)
        status_rect = status_surf.get_rect(
            topright=(self.rect.right - padding, self.rect.y + 12)
        )
        screen.blit(status_surf, status_rect)

        current_y = self.rect.y + 40
        for label_surf, value_surf in self.stat_surfaces:
            screen.blit(label_surf, (self.rect.x + padding, current_y))
            value_rect = value_surf.get_rect(
                topright=(self.rect.right - padding, current_y)
            )
            screen.blit(value_surf, value_rect)
            current_y += 18


class WorkshopScreen:
    """
    Manages The Workshop UI.
    REFACTORED: Now fully theme-driven and correctly initializes child components.
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

        self.all_unlockable_towers = self.progression_manager.get_unlockable_towers()
        self.filtered_towers: List[Dict[str, Any]] = []
        self.tower_buttons: List[TowerUnlockButton] = []
        self.selected_tower: Optional[TowerUnlockButton] = None
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
        self.all_unlockable_towers = self.progression_manager.get_unlockable_towers()
        if self.active_filter.lower() == "all":
            self.filtered_towers = self.all_unlockable_towers
        else:
            all_tower_configs = self.progression_manager.all_tower_configs
            self.filtered_towers = [
                t
                for t in self.all_unlockable_towers
                if all_tower_configs.get(t["id"], {}).get("category")
                == self.active_filter
            ]

        self.tower_buttons.clear()
        for tower_info in self.filtered_towers:
            full_config = self.progression_manager.all_tower_configs.get(
                tower_info["id"], {}
            )
            tower_info_full = {**full_config, **tower_info}
            button = TowerUnlockButton(
                pygame.Rect(0, 0, 0, 0),
                tower_info_full,
                self.ui_theme,
                self.font_manager,
            )
            self.tower_buttons.append(button)
        self.grid.update_item_count(len(self.tower_buttons))

        self.filter_buttons.clear()
        all_categories = sorted(
            list(
                set(
                    self.progression_manager.all_tower_configs.get(t["id"], {}).get(
                        "category", "N/A"
                    )
                    for t in self.all_unlockable_towers
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
        self.selected_tower = None
        self.preview_panel.set_item(None, "", lambda: None)
        self._build_layout()

    def _purchase_tower(self, tower_id: str):
        if self.progression_manager.purchase_tower(tower_id):
            self.set_filter(self.active_filter)

    def handle_event(self, event: pygame.event.Event):
        mouse_pos = pygame.mouse.get_pos()
        self.grid.handle_scroll_event(event)
        self.preview_panel.handle_event(event)

        for btn in self.filter_buttons:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
            btn.handle_event(event)

        hovered_button = None
        for i, button in enumerate(self.tower_buttons):
            layout_rect = self.grid.get_item_rect(i)
            on_screen_rect = layout_rect.move(0, -self.grid.scroll_y)
            if self.grid.area.contains(on_screen_rect):
                button.rect.topleft = on_screen_rect.topleft
                button.is_hovered = on_screen_rect.collidepoint(mouse_pos)
                if button.is_hovered:
                    hovered_button = button
            else:
                button.is_hovered = False

        if hovered_button and hovered_button != self.selected_tower:
            self.selected_tower = hovered_button
            for btn in self.tower_buttons:
                btn.is_selected = btn == self.selected_tower
            can_afford = (
                self.progression_manager.get_player_data().meta_currency
                >= self.selected_tower.tower_info["cost"]
            )
            self.preview_panel.set_item(
                item_data=self.selected_tower.tower_info,
                button_text=f"Unlock ({self.selected_tower.tower_info['cost']} CS)",
                button_action=lambda: self._purchase_tower(
                    self.selected_tower.tower_info["id"]
                ),
                is_button_enabled=not self.selected_tower.is_unlocked and can_afford,
            )

        self.back_button.is_hovered = self.back_button.rect.collidepoint(mouse_pos)
        if (
            self.back_button.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.back_callback()

    def draw(self, screen: pygame.Surface):
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
        screen.blit(back_surf, back_surf.get_rect(center=self.back_button.rect.center))

        self.preview_panel.draw(screen)
        for btn in self.filter_buttons:
            btn.draw(screen)

        screen.set_clip(self.grid.area)
        player_currency = self.progression_manager.get_player_data().meta_currency
        for i, button in enumerate(self.tower_buttons):
            layout_rect = self.grid.get_item_rect(i)
            button.rect.topleft = (layout_rect.x, layout_rect.y - self.grid.scroll_y)
            button.draw(screen, player_currency >= button.tower_info["cost"])
        screen.set_clip(None)

        self.grid.draw_scrollbar(screen)
