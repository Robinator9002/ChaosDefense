# rendering/ui/panels/persona_selection_panel.py
import pygame
import logging
from typing import List, Dict, Any, Optional

from ..ui_element import UIElement
from ..ui_action import UIAction, ActionType
from ..text.text_renderer import render_text_wrapped

logger = logging.getLogger(__name__)


class _PersonaButton(UIElement):
    """
    A private helper class representing a single button within the selection panel.
    Manages its own state and drawing logic.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        persona_id: str,
        persona_data: Dict[str, Any],
        is_active: bool,
        is_eligible: bool,
    ):
        super().__init__(rect)
        self.persona_id = persona_id
        self.name = persona_data.get("name", "N/A")
        self.description = persona_data.get("description", "")
        self.is_active = is_active
        self.is_eligible = is_eligible

        self.font_name = pygame.font.SysFont("segoeui", 16, bold=True)
        self.font_desc = pygame.font.SysFont("segoeui", 12)
        self.colors = {
            "bg_eligible": (40, 50, 60),
            "bg_hover": (60, 75, 90),
            "bg_active": (80, 110, 140),
            "bg_ineligible": (30, 35, 40),
            "border_eligible": (80, 90, 100),
            "border_active": (150, 180, 200),
            "border_ineligible": (50, 55, 60),
            "text_name": (210, 210, 220),
            "text_desc": (160, 160, 170),
            "text_ineligible": (100, 100, 110),
        }

    def handle_event(
        self, event: pygame.event.Event, game_state=None
    ) -> Optional[UIAction]:
        # The parent panel now calculates the hover state based on the scroll position.
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
        if self.is_active:
            bg_color = self.colors["bg_active"]
            border_color = self.colors["border_active"]
            name_color = self.colors["text_name"]
            desc_color = self.colors["text_desc"]
        elif self.is_eligible:
            bg_color = (
                self.colors["bg_hover"]
                if self.is_hovered
                else self.colors["bg_eligible"]
            )
            border_color = self.colors["border_eligible"]
            name_color = self.colors["text_name"]
            desc_color = self.colors["text_desc"]
        else:  # Ineligible
            bg_color = self.colors["bg_ineligible"]
            border_color = self.colors["border_ineligible"]
            name_color = self.colors["text_ineligible"]
            desc_color = self.colors["text_ineligible"]

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)

        name_surf = self.font_name.render(self.name, True, name_color)
        screen.blit(name_surf, (self.rect.x + 10, self.rect.y + 8))

        desc_surfaces = render_text_wrapped(
            self.description, self.font_desc, desc_color, self.rect.width - 20
        )
        current_y = self.rect.y + 30
        for line in desc_surfaces:
            screen.blit(line, (self.rect.x + 10, current_y))
            current_y += line.get_height()


class PersonaSelectionPanel(UIElement):
    """
    A modal panel that displays all available AI personas, allowing the player
    to select a new one for a tower. Features a scrollbar if content overflows.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        all_personas: Dict[str, Any],
        eligible_personas: List[str],
        active_persona: str,
    ):
        panel_width = 400
        max_panel_height = screen_rect.height * 0.8

        super().__init__(pygame.Rect(0, 0, panel_width, 0))

        self.buttons: List[_PersonaButton] = []
        self._setup_fonts_and_colors()
        self._create_buttons(all_personas, eligible_personas, active_persona)

        self.scroll_y = 0
        self.content_height = 0
        self.visible_height = 0
        self.max_scroll = 0
        self.is_scrollable = False

        self._perform_layout(max_panel_height)
        self.rect.center = screen_rect.center

        self.close_button_rect = pygame.Rect(
            self.rect.right - 32, self.rect.y + 8, 24, 24
        )
        self.is_close_hovered = False

    def _setup_fonts_and_colors(self):
        self.font_title = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_close = pygame.font.SysFont("segoeui", 22, bold=True)
        self.colors = {
            "bg": (20, 25, 35, 245),
            "border": (80, 90, 100),
            "title": (220, 220, 230),
            "close_default": (150, 150, 160),
            "close_hover": (255, 80, 80),
            "scrollbar_track": (30, 35, 45),
            "scrollbar_handle": (80, 90, 100),
        }

    def _create_buttons(
        self,
        all_personas: Dict[str, Any],
        eligible_personas: List[str],
        active_persona: str,
    ):
        for persona_id, persona_data in all_personas.items():
            if not isinstance(persona_data, dict):
                continue

            is_active = persona_id == active_persona
            is_eligible = persona_id in eligible_personas
            button = _PersonaButton(
                pygame.Rect(0, 0, 0, 0),
                persona_id,
                persona_data,
                is_active,
                is_eligible,
            )
            self.buttons.append(button)

    def _perform_layout(self, max_height: float):
        padding = 20
        header_height = 60
        footer_padding = 10
        button_width = self.rect.width - (padding * 2)
        button_height = 65
        button_spacing = 10

        self.content_height = (
            len(self.buttons) * (button_height + button_spacing) - button_spacing
        )

        total_required_height = self.content_height + header_height + footer_padding
        if total_required_height > max_height:
            self.rect.height = max_height
            self.is_scrollable = True
            button_width -= 15  # Make space for scrollbar
        else:
            self.rect.height = total_required_height
            self.is_scrollable = False

        self.visible_height = self.rect.height - header_height - footer_padding
        self.max_scroll = max(0, self.content_height - self.visible_height)

        current_y = 0
        for button in self.buttons:
            button.rect.topleft = (padding, current_y)
            button.rect.size = (button_width, button_height)
            current_y += button_height + button_spacing

    def handle_event(
        self, event: pygame.event.Event, game_state=None
    ) -> Optional[UIAction]:
        if event.type == pygame.MOUSEMOTION:
            self.is_close_hovered = self.close_button_rect.collidepoint(event.pos)
            for button in self.buttons:
                on_screen_rect = button.rect.move(
                    self.rect.x, self.rect.y + 60 - self.scroll_y
                )
                button.is_hovered = on_screen_rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_scrollable and self.rect.collidepoint(event.pos):
                if event.button == 4:  # Scroll up
                    self.scroll_y = max(0, self.scroll_y - 35)
                elif event.button == 5:  # Scroll down
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 35)

            if event.button == 1:
                if self.is_close_hovered:
                    return UIAction(type=ActionType.CLOSE_PERSONA_PANEL)

                for button in self.buttons:
                    if button.is_hovered:
                        action = button.handle_event(event, game_state)
                        if action:
                            return action

                if self.rect.collidepoint(event.pos):
                    return UIAction(type=ActionType.UI_CLICK)

        return None

    def draw(self, screen: pygame.Surface):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors["bg"])
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=8)

        title_surf = self.font_title.render(
            "Change Targeting Persona", True, self.colors["title"]
        )
        title_rect = title_surf.get_rect(centerx=self.rect.centerx, y=self.rect.y + 20)
        screen.blit(title_surf, title_rect)

        # --- FIX: Define the clipping area precisely ---
        # The content area is the space below the header and above the bottom padding.
        content_area_rect = pygame.Rect(
            self.rect.x + 1,
            self.rect.y + 60,  # 60 is header height
            self.rect.width - 2,
            self.visible_height,  # This is calculated correctly in _perform_layout
        )

        # Set the clipping area to prevent buttons from drawing outside the content box
        screen.set_clip(content_area_rect)

        for button in self.buttons:
            # Calculate the button's on-screen position, accounting for scroll
            on_screen_pos_y = content_area_rect.y + button.rect.y - self.scroll_y
            on_screen_pos = (self.rect.x + button.rect.x, on_screen_pos_y)

            # Simple culling: only process if the button is vertically visible
            if (
                on_screen_pos_y < content_area_rect.bottom
                and on_screen_pos_y + button.rect.height > content_area_rect.top
            ):
                # Create a temporary rect for drawing at the correct on-screen position
                draw_rect = button.rect.copy()
                draw_rect.topleft = on_screen_pos

                # Temporarily update the button's main rect for its own draw call
                original_rect = button.rect
                button.rect = draw_rect
                button.draw(screen)
                button.rect = original_rect  # Restore original layout rect

        # Reset clipping area to draw the rest of the UI
        screen.set_clip(None)

        if self.is_scrollable:
            self._draw_scrollbar(screen)

        close_color = (
            self.colors["close_hover"]
            if self.is_close_hovered
            else self.colors["close_default"]
        )
        close_surf = self.font_close.render("X", True, close_color)
        close_rect = close_surf.get_rect(center=self.close_button_rect.center)
        screen.blit(close_surf, close_rect)

    def _draw_scrollbar(self, screen: pygame.Surface):
        track_width = 10
        track_rect = pygame.Rect(
            self.rect.right - track_width - 5,
            self.rect.top + 60,
            track_width,
            self.visible_height,
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
