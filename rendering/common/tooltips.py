# rendering/common/tooltips.py
import pygame
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from rendering.text.text_renderer import render_text_wrapped

if TYPE_CHECKING:
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class Tooltip:
    """
    A data and rendering class for a single tooltip instance.
    It handles the visual representation, including background panel and wrapped text.
    """

    def __init__(
        self,
        text: str,
        mouse_pos: tuple[int, int],
        screen_rect: pygame.Rect,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes and builds the tooltip surface.
        """
        self.ui_theme = ui_theme
        self.font_manager = font_manager
        self.colors = self.ui_theme.get("colors", {})
        self.layout = self.ui_theme.get("layout", {})
        self.font = self.font_manager.get_font("body_tiny")

        self.surface = self._create_surface(text)
        self.rect = self.surface.get_rect()
        self._position_rect(mouse_pos, screen_rect)

    def _create_surface(self, text: str) -> pygame.Surface:
        """Creates the final tooltip surface with background and text."""
        padding = self.layout.get("padding_small", 10)
        max_width = 250  # A reasonable max width for tooltips

        rendered_lines = render_text_wrapped(
            text, self.font, self.colors.get("text_primary"), max_width
        )

        if not rendered_lines:
            return pygame.Surface((0, 0))

        content_width = max(line.get_width() for line in rendered_lines)
        content_height = sum(line.get_height() for line in rendered_lines)

        surface_width = content_width + padding * 2
        surface_height = content_height + padding * 2

        surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
        bg_color = tuple(self.colors.get("panel_primary")) + (240,)
        surface.fill(bg_color)

        # Draw content
        current_y = padding
        for line in rendered_lines:
            surface.blit(line, (padding, current_y))
            current_y += line.get_height()

        # Draw border
        pygame.draw.rect(
            surface,
            self.colors.get("border_primary"),
            surface.get_rect(),
            self.layout.get("border_width_standard", 2),
            border_radius=self.layout.get("border_radius_small", 5),
        )

        return surface

    def _position_rect(self, mouse_pos: tuple[int, int], screen_rect: pygame.Rect):
        """Positions the tooltip rect relative to the mouse, ensuring it stays on screen."""
        self.rect.topleft = (mouse_pos[0] + 15, mouse_pos[1] + 15)
        # Clamp to screen edges
        self.rect.clamp_ip(screen_rect)

    def draw(self, screen: pygame.Surface):
        """Draws the tooltip to the main screen."""
        screen.blit(self.surface, self.rect)


class TooltipManager:
    """
    Manages the lifecycle of tooltips, including hover detection, timing,
    and display.
    """

    def __init__(
        self,
        screen_rect: pygame.Rect,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        self.screen_rect = screen_rect
        self.ui_theme = ui_theme
        self.font_manager = font_manager

        self.active_tooltip: Optional[Tooltip] = None
        self.pending_tooltip_text: Optional[str] = None
        self.hover_target_rect: Optional[pygame.Rect] = None
        self.hover_timer = 0.0
        self.hover_delay = 0.5  # Seconds to wait before showing tooltip

    def request_tooltip(self, text: str, target_rect: pygame.Rect):
        """
        A UI element calls this method when the mouse is hovering over it.
        This initiates the timer to show a tooltip.
        """
        # If the mouse is still over the same target, do nothing.
        if self.hover_target_rect and self.hover_target_rect == target_rect:
            return

        # If the mouse moves to a new target, reset everything.
        self.cancel_tooltip()
        self.pending_tooltip_text = text
        self.hover_target_rect = target_rect

    def cancel_tooltip(self):
        """
        Called when the mouse moves off a hoverable element.
        Resets the timer and hides any active tooltip.
        """
        self.active_tooltip = None
        self.pending_tooltip_text = None
        self.hover_target_rect = None
        self.hover_timer = 0.0

    def update(self, dt: float):
        """
        Updates the hover timer and creates the tooltip when the delay is met.
        Should be called every frame.
        """
        mouse_pos = pygame.mouse.get_pos()

        # If there's a pending tooltip, check if the mouse is still over the target.
        if self.hover_target_rect:
            if self.hover_target_rect.collidepoint(mouse_pos):
                self.hover_timer += dt
                if self.hover_timer >= self.hover_delay and not self.active_tooltip:
                    if self.pending_tooltip_text:
                        self.active_tooltip = Tooltip(
                            self.pending_tooltip_text,
                            mouse_pos,
                            self.screen_rect,
                            self.ui_theme,
                            self.font_manager,
                        )
            else:
                # Mouse has moved off the target.
                self.cancel_tooltip()

        # If a tooltip is active, make sure it's still valid.
        if self.active_tooltip and self.hover_target_rect:
            if not self.hover_target_rect.collidepoint(mouse_pos):
                self.cancel_tooltip()

    def draw(self, screen: pygame.Surface):
        """Draws the active tooltip. Should be called every frame."""
        if self.active_tooltip:
            self.active_tooltip.draw(screen)
