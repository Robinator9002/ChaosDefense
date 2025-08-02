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
    from rendering.common.tooltips import TooltipManager

logger = logging.getLogger(__name__)


class _PersonaButton(UIElement):
    """
    Private helper class for a button in the persona selection panel.
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

        if self.is_hovered and self.is_eligible and not self.is_active:
            glow_color_list = self.colors.get(
                "border_interactive_selected", (150, 180, 200)
            )
            # --- FIX: Convert list to tuple before concatenation to prevent TypeError ---
            glow_color_tuple = tuple(glow_color_list)
            glow_rect = self.rect.inflate(6, 6)
            glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                glow_surface,
                glow_color_tuple + (80,),
                glow_surface.get_rect(),
                border_radius=border_radius + 2,
            )
            screen.blit(glow_surface, glow_rect.topleft)

        # --- MODIFIED: Improved styling for the active persona button ---
        if self.is_active:
            bg_color = self.colors.get("panel_secondary")
            # Use the standard selection color instead of the jarring yellow accent.
            border_color = self.colors.get("border_interactive_selected")
            # Make the border thicker to emphasize that it's the active selection.
            border_width = self.layout.get("border_width_selected", 3)
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
    MODIFIED: Now includes animated transitions and enhanced styling.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        all_personas: Dict[str, Any],
        eligible_personas: List[str],
        active_persona: str,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
        tooltip_manager: "TooltipManager",
    ):
        panel_width = 400
        super().__init__(pygame.Rect(0, 0, panel_width, 0))
        self.screen_rect = screen_rect
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.tooltip_manager = tooltip_manager
        self.buttons: List[_PersonaButton] = []

        self.animation_progress = 0.0
        self.animation_speed = 5.0

        self._load_theme_assets()
        self._create_buttons(all_personas, eligible_personas, active_persona)

        self.scroll_y = 0
        self.content_height = 0
        self.visible_height = 0
        self.max_scroll = 0
        self.is_scrollable = False

        self._perform_layout()
        self.final_rect = self.rect.copy()
        self.final_rect.center = screen_rect.center
        self.close_button_rect = pygame.Rect(
            self.final_rect.right - 32, self.final_rect.y + 8, 24, 24
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
        self.final_rect.center = new_screen_rect.center
        self.close_button_rect.topright = (
            self.final_rect.right - 8,
            self.final_rect.y + 8,
        )

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

    def update(self, dt: float, game_state: "GameState"):
        if self.animation_progress < 1.0:
            self.animation_progress = min(
                1.0, self.animation_progress + self.animation_speed * dt
            )

        mouse_pos = pygame.mouse.get_pos()
        self.is_close_hovered = self.close_button_rect.collidepoint(mouse_pos)

        hovered_item = False
        for button in self.buttons:
            on_screen_rect = button.rect.move(
                self.final_rect.x, self.final_rect.y + 60 - self.scroll_y
            )
            button.is_hovered = on_screen_rect.collidepoint(mouse_pos)

            if button.is_hovered and button.description:
                self.tooltip_manager.request_tooltip(button.description, on_screen_rect)
                hovered_item = True
                break

        if not hovered_item:
            self.tooltip_manager.cancel_tooltip()

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_scrollable and self.rect.collidepoint(pygame.mouse.get_pos()):
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
                if self.rect.collidepoint(pygame.mouse.get_pos()):
                    return UIAction(type=ActionType.UI_CLICK)
        return None

    def draw(self, screen: pygame.Surface):
        ease_out_progress = 1 - (1 - self.animation_progress) ** 3

        current_width = self.final_rect.width * ease_out_progress
        current_height = self.final_rect.height * ease_out_progress
        self.rect.size = (current_width, current_height)
        self.rect.center = self.final_rect.center

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(150 * ease_out_progress)))
        screen.blit(overlay, (0, 0))

        if self.animation_progress < 0.1:
            return

        panel_surf = pygame.Surface(self.final_rect.size, pygame.SRCALPHA)

        panel_color = tuple(self.colors.get("panel_primary", [25, 30, 40]))
        panel_surf.fill(panel_color + (int(245 * ease_out_progress),))

        pygame.draw.rect(
            panel_surf,
            self.colors.get("border_primary"),
            panel_surf.get_rect(),
            2,
            border_radius=self.layout.get("border_radius_large"),
        )

        title_surf = self.font_title.render(
            "Change Targeting Persona", True, self.colors.get("text_primary")
        )
        title_rect = title_surf.get_rect(centerx=panel_surf.get_width() / 2, y=20)
        panel_surf.blit(title_surf, title_rect)

        content_area_rect = pygame.Rect(
            1, 60, panel_surf.get_width() - 2, self.visible_height
        )
        content_surf = pygame.Surface(content_area_rect.size, pygame.SRCALPHA)

        for button in self.buttons:
            draw_rect = button.rect.copy()
            # We need to calculate the on-screen position for drawing, not just relative
            draw_rect.topleft = (button.rect.x, button.rect.y - self.scroll_y)

            # Temporarily set the button's rect for the draw call
            original_rect = button.rect
            button.rect = draw_rect
            button.draw(content_surf)
            button.rect = original_rect

        panel_surf.blit(content_surf, content_area_rect.topleft)

        if self.is_scrollable:
            self._draw_scrollbar(panel_surf)

        close_color = (
            self.colors.get("text_error")
            if self.is_close_hovered
            else self.colors.get("text_secondary")
        )
        close_surf = self.font_close.render("X", True, close_color)
        close_rect = close_surf.get_rect(topright=(self.final_rect.width - 8, 8))
        panel_surf.blit(close_surf, close_rect)

        if self.rect.width > 0 and self.rect.height > 0:
            scaled_panel = pygame.transform.smoothscale(panel_surf, self.rect.size)
            screen.blit(scaled_panel, self.rect)

    def _draw_scrollbar(self, surface: pygame.Surface):
        track_width = self.layout.get("scrollbar_width", 10)
        track_rect = pygame.Rect(
            surface.get_width() - track_width - 5, 60, track_width, self.visible_height
        )
        pygame.draw.rect(
            surface,
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
                surface,
                self.colors.get("scrollbar_handle"),
                handle_rect,
                border_radius=self.layout.get("border_radius_small"),
            )
