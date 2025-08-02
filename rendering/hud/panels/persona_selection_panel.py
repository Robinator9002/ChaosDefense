# rendering/hud/panels/persona_selection_panel.py
import pygame
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from rendering.common.ui.ui_action import UIAction, ActionType
from rendering.text.text_renderer import render_text_wrapped

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager
    from game_logic.game_state import GameState

logger = logging.getLogger(__name__)


class _PersonaButton(UIElement):
    """
    Private helper class for a button in the persona selection panel.
    REFACTORED: Now fully theme-driven.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        persona_id: str,
        persona_data: Dict[str, Any],
        is_active: bool,
        is_eligible: bool,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        super().__init__(rect)
        self.persona_id = persona_id
        self.name = persona_data.get("name", "N/A")
        self.description = persona_data.get("description", "")
        self.is_active = is_active
        self.is_eligible = is_eligible

        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font_name = font_manager.get_font("body_medium", bold=True)
        self.font_desc = font_manager.get_font("body_tiny")

    def handle_event(
        self, event: pygame.event.Event, game_state=None
    ) -> Optional[UIAction]:
        if self.is_eligible and not self.is_active:
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.is_hovered
            ):
                return UIAction(
                    type=ActionType.CHANGE_TARGETING_PERSONA, entity_id=self.persona_id
                )
        return None

    def draw(self, screen: pygame.Surface):
        border_radius = self.layout.get("border_radius_small", 5)
        border_width = self.layout.get("border_width_standard", 2)

        if self.is_active:
            bg_color = self.colors.get("panel_interactive_hover")
            border_color = self.colors.get("border_accent")
            name_color = self.colors.get("text_primary")
            desc_color = self.colors.get("text_secondary")
        elif self.is_eligible:
            bg_color = (
                self.colors.get("panel_interactive_hover")
                if self.is_hovered
                else self.colors.get("panel_secondary")
            )
            border_color = (
                self.colors.get("border_interactive_selected")
                if self.is_hovered
                else self.colors.get("border_primary")
            )
            name_color = self.colors.get("text_primary")
            desc_color = self.colors.get("text_secondary")
        else:  # Ineligible
            bg_color = self.colors.get("panel_primary")
            border_color = self.colors.get("border_primary")
            name_color = self.colors.get("text_disabled")
            desc_color = self.colors.get("text_disabled")

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)
        pygame.draw.rect(
            screen, border_color, self.rect, border_width, border_radius=border_radius
        )

        padding = self.layout.get("padding_small", 10)
        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + padding, self.rect.y + 8))

        desc_surfaces = render_text_wrapped(
            self.description,
            self.font_desc,
            desc_color,
            self.rect.width - (padding * 2),
        )
        current_y = self.rect.y + 30
        for line in desc_surfaces:
            screen.blit(line, (self.rect.x + padding, current_y))
            current_y += line.get_height()


class PersonaSelectionPanel(UIElement):
    """
    A modal panel for selecting a tower's AI persona.
    REFACTORED: Now fully theme-driven and robustly handles layout and scrolling.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        all_personas: Dict[str, Any],
        eligible_personas: List[str],
        active_persona: str,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        panel_width = 400
        super().__init__(pygame.Rect(0, 0, panel_width, 0))
        self.screen_rect = screen_rect
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.buttons: List[_PersonaButton] = []

        self._load_theme_assets()
        self._create_buttons(all_personas, eligible_personas, active_persona)

        self.scroll_y = 0
        self.content_height = 0
        self.visible_height = 0
        self.max_scroll = 0
        self.is_scrollable = False

        self._perform_layout()
        self.rect.center = screen_rect.center
        self.close_button_rect = pygame.Rect(
            self.rect.right - 32, self.rect.y + 8, 24, 24
        )
        self.is_close_hovered = False

    def _load_theme_assets(self):
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font_title = self.font_manager.get_font("body_large")
        self.font_close = self.font_manager.get_font("body_large")

    def on_resize(self, new_screen_rect: pygame.Rect):
        self.screen_rect = new_screen_rect
        self._perform_layout()
        self.rect.center = new_screen_rect.center
        self.close_button_rect.topright = (self.rect.right - 8, self.rect.y + 8)

    def _create_buttons(self, all_personas, eligible_personas, active_persona):
        for persona_id, persona_data in all_personas.items():
            if not isinstance(persona_data, dict):
                continue
            button = _PersonaButton(
                pygame.Rect(0, 0, 0, 0),
                persona_id,
                persona_data,
                is_active=(persona_id == active_persona),
                is_eligible=(persona_id in eligible_personas),
                ui_theme=self.ui_theme,
                font_manager=self.font_manager,
            )
            self.buttons.append(button)

    def _perform_layout(self):
        padding = self.layout.get("padding_large", 20)
        spacing = self.layout.get("spacing_medium", 10)
        max_panel_height = self.screen_rect.height * 0.8
        header_height = 60
        button_width = self.rect.width - (padding * 2)
        button_height = 65

        self.content_height = len(self.buttons) * (button_height + spacing) - spacing
        total_required_height = self.content_height + header_height + padding

        if total_required_height > max_panel_height:
            self.rect.height = max_panel_height
            self.is_scrollable = True
            button_width -= self.layout.get("scrollbar_width", 10) + 5
        else:
            self.rect.height = total_required_height
            self.is_scrollable = False

        self.visible_height = self.rect.height - header_height - padding
        self.max_scroll = max(0, self.content_height - self.visible_height)

        current_y = 0
        for button in self.buttons:
            button.rect.topleft = (padding, current_y)
            button.rect.size = (button_width, button_height)
            current_y += button_height + spacing

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        mouse_pos = event.pos if hasattr(event, "pos") else pygame.mouse.get_pos()
        self.is_close_hovered = self.close_button_rect.collidepoint(mouse_pos)

        for button in self.buttons:
            on_screen_rect = button.rect.move(
                self.rect.x, self.rect.y + 60 - self.scroll_y
            )
            button.is_hovered = on_screen_rect.collidepoint(mouse_pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_scrollable and self.rect.collidepoint(mouse_pos):
                if event.button == 4:
                    self.scroll_y = max(0, self.scroll_y - 35)
                elif event.button == 5:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 35)
            if event.button == 1:
                if self.is_close_hovered:
                    return UIAction(type=ActionType.CLOSE_PERSONA_PANEL)
                for button in self.buttons:
                    if button.is_hovered:
                        action = button.handle_event(event, game_state)
                        if action:
                            return action
                if self.rect.collidepoint(mouse_pos):
                    return UIAction(type=ActionType.UI_CLICK)
        return None

    def draw(self, screen: pygame.Surface):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors.get("panel_primary") + (245,))
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(
            screen,
            self.colors.get("border_primary"),
            self.rect,
            2,
            border_radius=self.layout.get("border_radius_large"),
        )

        title_surf = self.font_title.render(
            "Change Targeting Persona", True, self.colors.get("text_primary")
        )
        title_rect = title_surf.get_rect(centerx=self.rect.centerx, y=self.rect.y + 20)
        screen.blit(title_surf, title_rect)

        content_area_rect = pygame.Rect(
            self.rect.x + 1, self.rect.y + 60, self.rect.width - 2, self.visible_height
        )
        screen.set_clip(content_area_rect)

        for button in self.buttons:
            on_screen_pos_y = content_area_rect.y + button.rect.y - self.scroll_y
            if (
                on_screen_pos_y < content_area_rect.bottom
                and on_screen_pos_y + button.rect.height > content_area_rect.top
            ):
                original_rect, button.rect.topleft = button.rect, (
                    self.rect.x + button.rect.x,
                    on_screen_pos_y,
                )
                button.draw(screen)
                button.rect = original_rect

        screen.set_clip(None)
        if self.is_scrollable:
            self._draw_scrollbar(screen)

        close_color = (
            self.colors.get("text_error")
            if self.is_close_hovered
            else self.colors.get("text_secondary")
        )
        close_surf = self.font_close.render("X", True, close_color)
        close_rect = close_surf.get_rect(center=self.close_button_rect.center)
        screen.blit(close_surf, close_rect)

    def _draw_scrollbar(self, screen: pygame.Surface):
        track_width = self.layout.get("scrollbar_width", 10)
        track_rect = pygame.Rect(
            self.rect.right - track_width - 5,
            self.rect.top + 60,
            track_width,
            self.visible_height,
        )
        pygame.draw.rect(
            screen,
            self.colors.get("scrollbar_track"),
            track_rect,
            border_radius=self.layout.get("border_radius_small"),
        )

        if self.content_height > self.visible_height:
            handle_height = max(
                20, self.visible_height * (self.visible_height / self.content_height)
            )
            scroll_ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
            handle_y = track_rect.y + (track_rect.height - handle_height) * scroll_ratio
            handle_rect = pygame.Rect(
                track_rect.x, handle_y, track_rect.width, handle_height
            )
            pygame.draw.rect(
                screen,
                self.colors.get("scrollbar_handle"),
                handle_rect,
                border_radius=self.layout.get("border_radius_small"),
            )
