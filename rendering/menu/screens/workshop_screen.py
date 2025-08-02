# rendering/menu/screens/workshop_screen.py
import pygame
import logging
from typing import List, Dict, Any, Callable, Set, Optional

from rendering.common.ui.ui_element import UIElement
from rendering.text.text_renderer import render_text_wrapped
from game_logic.progression.progression_manager import ProgressionManager
from ..components.scrollable_grid import ScrollableGrid
from ..panels.preview_panel import PreviewPanel
from rendering.common.panels.panel_utils import get_nested_value, format_stat_value

logger = logging.getLogger(__name__)


class WorkshopButton(UIElement):
    """A generic button for the Workshop screen, used for category filters."""

    def __init__(
        self, rect: pygame.Rect, text: str, action: Callable, is_active: bool = False
    ):
        super().__init__(rect)
        self.text = text
        self.action = action
        self.is_active = is_active
        self.font = pygame.font.SysFont("segoeui", 18, bold=True)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_active": (80, 110, 140),
            "text_default": (180, 180, 190),
            "text_active": (240, 240, 250),
            "border_active": (150, 180, 200),
            "border_default": (80, 90, 100),
        }

    def handle_event(self, event: pygame.event.Event):
        if (
            self.is_hovered
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self.action()

    def draw(self, screen: pygame.Surface):
        bg_color = (
            self.colors["bg_active"]
            if self.is_active
            else (
                self.colors["bg_hover"]
                if self.is_hovered
                else self.colors["bg_default"]
            )
        )
        text_color = (
            self.colors["text_active"]
            if self.is_active
            else self.colors["text_default"]
        )
        border_color = (
            self.colors["border_active"]
            if self.is_active
            else self.colors["border_default"]
        )

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


class TowerUnlockButton(UIElement):
    """A UI element for unlocking a new tower in The Workshop, now with stats."""

    def __init__(self, rect: pygame.Rect, tower_info: Dict[str, Any]):
        super().__init__(rect)
        self.tower_info = tower_info
        self.name = tower_info["name"]
        self.is_unlocked = tower_info["unlocked"]

        self._setup_fonts_and_colors()
        self._prepare_stat_surfaces()

    def _setup_fonts_and_colors(self):
        self.font_name = pygame.font.SysFont("segoeui", 20, bold=True)
        self.font_cost = pygame.font.SysFont("segoeui", 18, bold=True)
        self.font_stat_label = pygame.font.SysFont("segoeui", 14)
        self.font_stat_value = pygame.font.SysFont("segoeui", 14, bold=True)
        self.colors = {
            "bg_default": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_selected": (75, 95, 115),
            "bg_unlocked": (35, 60, 45),
            "border_default": (80, 90, 100),
            "border_hover": (150, 180, 200),
            "border_unlocked": (70, 110, 85),
            "text_name": (210, 210, 220),
            "text_unlocked": (180, 230, 190),
            "cost_can_afford": (255, 215, 0),
            "cost_cant_afford": (180, 40, 40),
            "stat_label": (160, 160, 170),
            "stat_value": (220, 220, 230),
        }
        self.is_selected = False

    def _prepare_stat_surfaces(self):
        """Pre-renders the stat text for drawing."""
        self.stat_surfaces = []
        stats_to_display = self.tower_info.get("info_panel_stats", [])

        for stat_info in stats_to_display[:3]:  # Show up to 3 key stats
            label = stat_info.get("label", "N/A")
            value_path = stat_info.get("value_path")
            value = (
                get_nested_value(self.tower_info, value_path) if value_path else "N/A"
            )

            if value is None:
                continue

            value_str = format_stat_value(value, stat_info.get("format"))

            label_surf = self.font_stat_label.render(
                f"{label}:", True, self.colors["stat_label"]
            )
            value_surf = self.font_stat_value.render(
                value_str, True, self.colors["stat_value"]
            )
            self.stat_surfaces.append((label_surf, value_surf))

    def draw(self, screen: pygame.Surface, can_afford: bool):
        if self.is_unlocked:
            bg_color = self.colors["bg_unlocked"]
            border_color = self.colors["border_unlocked"]
            name_color = self.colors["text_unlocked"]
        else:
            bg_color = (
                self.colors["bg_selected"]
                if self.is_selected
                else (
                    self.colors["bg_hover"]
                    if self.is_hovered
                    else self.colors["bg_default"]
                )
            )
            border_color = (
                self.colors["border_hover"]
                if self.is_hovered or self.is_selected
                else self.colors["border_default"]
            )
            name_color = self.colors["text_name"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        # Draw Name and Cost/Status
        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 10))

        if self.is_unlocked:
            status_surf = self.font_cost.render(
                "UNLOCKED", True, self.colors["text_unlocked"]
            )
        else:
            cost_color = (
                self.colors["cost_can_afford"]
                if can_afford
                else self.colors["cost_cant_afford"]
            )
            cost_text = f"{self.tower_info['cost']} CS"
            status_surf = self.font_cost.render(cost_text, True, cost_color)

        status_rect = status_surf.get_rect(
            topright=(self.rect.right - 15, self.rect.y + 12)
        )
        screen.blit(status_surf, status_rect)

        # Draw Stats
        current_y = self.rect.y + 40
        for label_surf, value_surf in self.stat_surfaces:
            screen.blit(label_surf, (self.rect.x + 15, current_y))
            value_rect = value_surf.get_rect(topright=(self.rect.right - 15, current_y))
            screen.blit(value_surf, value_rect)
            current_y += 18


class WorkshopScreen:
    """Manages The Workshop UI with a scrollable grid, filters, and a preview panel."""

    def __init__(
        self,
        screen_rect: pygame.Rect,
        progression_manager: ProgressionManager,
        back_callback: Callable,
    ):
        self.screen_rect = screen_rect
        self.progression_manager = progression_manager
        self.back_callback = back_callback

        self.all_unlockable_towers = self.progression_manager.get_unlockable_towers()
        self.filtered_towers: List[Dict[str, Any]] = []
        self.tower_buttons: List[TowerUnlockButton] = []
        self.selected_tower: Optional[TowerUnlockButton] = None

        self.active_filter = "All"
        self.filter_buttons: List[WorkshopButton] = []

        self._setup_components()
        self._build_layout()

    def _setup_components(self):
        grid_area = pygame.Rect(
            50, 160, self.screen_rect.width * 0.5, self.screen_rect.height - 240
        )
        preview_area = pygame.Rect(
            grid_area.right + 50,
            160,
            self.screen_rect.width * 0.35,
            self.screen_rect.height * 0.7,
        )

        self.grid = ScrollableGrid(
            area=grid_area,
            item_size=(int(grid_area.width * 0.45), 110),
            item_spacing=(20, 20),
            columns=2,
        )
        self.preview_panel = PreviewPanel(preview_area)

        back_button_rect = pygame.Rect(30, self.screen_rect.bottom - 80, 150, 50)
        self.back_button = UIElement(back_button_rect)

        self._setup_fonts_and_colors()

    def _setup_fonts_and_colors(self):
        self.title_font = pygame.font.SysFont("segoeui", 52, bold=True)
        self.currency_font = pygame.font.SysFont("segoeui", 28, bold=True)
        self.back_font = pygame.font.SysFont("segoeui", 24, bold=True)

    def _build_layout(self):
        """Filters towers and rebuilds the grid and filter buttons."""
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
            # Add the full config data to the info dict for the button
            full_config = self.progression_manager.all_tower_configs.get(
                tower_info["id"], {}
            )
            tower_info_full = {**full_config, **tower_info}
            button = TowerUnlockButton(pygame.Rect(0, 0, 0, 0), tower_info_full)
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

        btn_width, btn_height, btn_spacing = 120, 35, 10
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
                button_action=self._purchase_tower,
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
        title_surf = self.title_font.render("The Workshop", True, (220, 220, 230))
        title_rect = title_surf.get_rect(
            centerx=self.screen_rect.centerx, y=self.screen_rect.height * 0.05
        )
        screen.blit(title_surf, title_rect)

        currency = self.progression_manager.get_player_data().meta_currency
        currency_surf = self.currency_font.render(
            f"Chaos Shards: {currency}", True, (255, 215, 0)
        )
        currency_rect = currency_surf.get_rect(
            topright=(self.screen_rect.right - 30, 30)
        )
        screen.blit(currency_surf, currency_rect)

        back_bg = (60, 75, 90) if self.back_button.is_hovered else (40, 50, 60)
        pygame.draw.rect(screen, back_bg, self.back_button.rect, border_radius=8)
        back_surf = self.back_font.render("Back", True, (210, 210, 220))
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
