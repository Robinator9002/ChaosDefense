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
        super().handle_event(event, game_state)
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
    to select a new one for a tower.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        all_personas: Dict[str, Any],
        eligible_personas: List[str],
        active_persona: str,
    ):
        panel_width = 400
        panel_height = 500  # Will be adjusted dynamically
        rect = pygame.Rect(0, 0, panel_width, panel_height)
        rect.center = screen_rect.center
        super().__init__(rect)

        self.buttons: List[_PersonaButton] = []
        self._setup_fonts_and_colors()
        self._create_buttons(all_personas, eligible_personas, active_persona)
        self._perform_layout()

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
        }

    def _create_buttons(
        self,
        all_personas: Dict[str, Any],
        eligible_personas: List[str],
        active_persona: str,
    ):
        for persona_id, persona_data in all_personas.items():
            is_active = persona_id == active_persona
            is_eligible = persona_id in eligible_personas
            # Rect position will be set in _perform_layout
            button = _PersonaButton(
                pygame.Rect(0, 0, 0, 0),
                persona_id,
                persona_data,
                is_active,
                is_eligible,
            )
            self.buttons.append(button)

    def _perform_layout(self):
        padding = 20
        button_width = self.rect.width - (padding * 2)
        button_height = 65
        button_spacing = 10

        current_y = self.rect.y + 60  # Space for title

        for button in self.buttons:
            button.rect.topleft = (self.rect.x + padding, current_y)
            button.rect.size = (button_width, button_height)
            current_y += button_height + button_spacing

        # Adjust panel height to fit all buttons
        self.rect.height = (current_y - self.rect.y) + padding - button_spacing

    def handle_event(
        self, event: pygame.event.Event, game_state=None
    ) -> Optional[UIAction]:
        if event.type == pygame.MOUSEMOTION:
            self.is_close_hovered = self.close_button_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_close_hovered:
                # Use a more specific action to avoid closing the main upgrade panel
                return UIAction(type=ActionType.CLOSE_PERSONA_PANEL)

        for button in self.buttons:
            action = button.handle_event(event, game_state)
            if action:
                return action

        # Absorb clicks on the panel background so they don't go through to the map
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            return UIAction(
                type=ActionType.UI_CLICK
            )  # Generic action to signify UI was clicked

        return None

    def draw(self, screen: pygame.Surface):
        # Draw a semi-transparent overlay on the whole screen
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Draw panel background
        panel_surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        panel_surf.fill(self.colors["bg"])
        screen.blit(panel_surf, self.rect.topleft)
        pygame.draw.rect(screen, self.colors["border"], self.rect, 2, border_radius=8)

        # Draw title
        title_surf = self.font_title.render(
            "Change Targeting Persona", True, self.colors["title"]
        )
        title_rect = title_surf.get_rect(centerx=self.rect.centerx, y=self.rect.y + 20)
        screen.blit(title_surf, title_rect)

        # Draw buttons
        for button in self.buttons:
            button.draw(screen)

        # Draw close button
        close_color = (
            self.colors["close_hover"]
            if self.is_close_hovered
            else self.colors["close_default"]
        )
        close_surf = self.font_close.render("X", True, close_color)
        close_rect = close_surf.get_rect(center=self.close_button_rect.center)
        screen.blit(close_surf, close_rect)
