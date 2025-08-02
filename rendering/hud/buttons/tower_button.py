# rendering/hud/buttons/tower_button.py
import pygame
import logging
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING

from rendering.common.ui.ui_element import UIElement
from rendering.common.ui.ui_action import UIAction, ActionType

if TYPE_CHECKING:
    from game_logic.game_state import GameState
    from rendering.text.font_manager import FontManager

logger = logging.getLogger(__name__)


class TowerButton(UIElement):
    """
    A UI element representing a clickable button to select a tower for building.
    MODIFIED: Now includes a smooth animation for hover and selection states
    to provide better visual feedback.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower_type_id: str,
        tower_data: Dict[str, Any],
        assets_path: Path,
        hotkey_number: int,
        ui_theme: Dict[str, Any],
        font_manager: "FontManager",
    ):
        """
        Initializes a new TowerButton.
        """
        super().__init__(rect)
        self.tower_type_id = tower_type_id
        self.tower_data = tower_data
        self.assets_path = assets_path
        self.hotkey_number = hotkey_number
        self.cost = self.tower_data.get("cost", 0)

        # --- NEW: Animation attributes ---
        # The base_rect stores the button's original, resting position.
        self.base_rect = rect.copy()
        # y_offset tracks the current vertical position for smooth animation.
        self.y_offset = 0.0
        # target_y_offset is the position we want to animate towards.
        self.target_y_offset = 0.0
        # animation_speed controls how quickly the button moves.
        self.animation_speed = 10.0

        self.colors = ui_theme.get("colors", {})
        self.layout = ui_theme.get("layout", {})
        self.font_cost = font_manager.get_font("body_tiny", bold=True)
        self.font_hotkey = font_manager.get_font("body_tiny", bold=True)

        self.icon = self._load_icon()

    def _load_icon(self) -> pygame.Surface:
        """Loads the tower's icon or creates a placeholder."""
        sprite_key = self.tower_data.get("sprite_key")
        icon_size = (self.rect.width - 10, self.rect.height - 20)

        if sprite_key:
            try:
                sprite_path = self.assets_path / "sprites" / sprite_key
                if not sprite_path.is_file():
                    raise FileNotFoundError(f"Sprite file not found at {sprite_path}")
                image = pygame.image.load(sprite_path).convert_alpha()
                return pygame.transform.scale(image, icon_size)
            except (FileNotFoundError, pygame.error) as e:
                logger.warning(
                    f"Could not load icon for '{self.tower_type_id}' ({e}). Creating placeholder."
                )

        placeholder = pygame.Surface(icon_size)
        placeholder.fill(self.tower_data.get("placeholder_color", (128, 128, 128)))
        return placeholder

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[UIAction]:
        """Handles mouse clicks and returns a structured UIAction."""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                logger.info(f"Player clicked tower button: {self.tower_type_id}")
                return UIAction(
                    type=ActionType.SELECT_TOWER, entity_id=self.tower_type_id
                )
        return None

    # --- NEW: Update method for animations ---
    def update(self, dt: float, game_state: "GameState"):
        """
        Updates the button's animation state for hover and selection effects.
        This method is called every frame by the UIManager.
        """
        is_selected = game_state.selected_tower_to_build == self.tower_type_id

        # 1. Determine the target Y position based on the button's state.
        # If hovered or selected, the button should move up.
        if self.is_hovered or is_selected:
            self.target_y_offset = -8  # Move up by 8 pixels
        else:
            self.target_y_offset = 0  # Return to base position

        # 2. Smoothly interpolate the current offset towards the target offset.
        # This creates a fluid "ease-out" animation effect.
        delta = self.target_y_offset - self.y_offset
        self.y_offset += delta * self.animation_speed * dt

        # 3. Update the actual drawing rectangle's position.
        # This ensures the animation is visually represented.
        self.rect.y = self.base_rect.y + int(self.y_offset)

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws the button using theme-defined styles."""
        is_selected = game_state.selected_tower_to_build == self.tower_type_id
        can_afford = game_state.gold >= self.cost
        border_radius = self.layout.get("border_radius_small", 5)

        if is_selected:
            bg_color = self.colors.get("panel_interactive_hover")
        elif self.is_hovered:
            bg_color = self.colors.get("panel_secondary")
        else:
            bg_color = self.colors.get("panel_primary")

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=border_radius)

        icon_rect = self.icon.get_rect(centerx=self.rect.centerx, y=self.rect.y + 5)
        screen.blit(self.icon, icon_rect)

        cost_color = (
            self.colors.get("text_accent")
            if can_afford
            else self.colors.get("text_error")
        )
        cost_text = self.font_cost.render(f"{self.cost}G", True, cost_color)
        text_rect = cost_text.get_rect(
            centerx=self.rect.centerx, bottom=self.rect.bottom - 5
        )
        screen.blit(cost_text, text_rect)

        if is_selected:
            border_color = self.colors.get("border_interactive_selected")
            border_width = self.layout.get("border_width_selected", 3)
        elif self.is_hovered:
            border_color = self.colors.get("border_interactive_selected")
            border_width = self.layout.get("border_width_standard", 2)
        else:
            border_color = self.colors.get("border_primary")
            border_width = self.layout.get("border_width_standard", 2)

        pygame.draw.rect(
            screen, border_color, self.rect, border_width, border_radius=border_radius
        )

        hotkey_surf = self.font_hotkey.render(
            str(self.hotkey_number), True, self.colors.get("text_secondary")
        )
        hotkey_rect = hotkey_surf.get_rect(topleft=(self.rect.x + 5, self.rect.y + 5))
        screen.blit(hotkey_surf, hotkey_rect)
