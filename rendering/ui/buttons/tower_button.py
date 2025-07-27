# rendering/ui/buttons/tower_button.py
import pygame
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ..ui_element import UIElement

# Using Any for game_state to avoid circular dependencies
if "GameState" not in globals():
    from typing import Any as GameState

logger = logging.getLogger(__name__)


class TowerButton(UIElement):
    """
    A specific UI element that represents a clickable button to select a tower.
    This has been updated to display a numeric hotkey.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        tower_type_id: str,
        tower_data: Dict[str, Any],
        assets_path: Path,
        hotkey_number: int,  # NEW: Added hotkey number
    ):
        """
        Initializes a new TowerButton.

        Args:
            rect (pygame.Rect): The rectangle for the button's position and size.
            tower_type_id (str): The unique identifier for the tower (e.g., "turret").
            tower_data (Dict[str, Any]): The configuration data for this tower type.
            assets_path (Path): The root path to the assets directory.
            hotkey_number (int): The number to display as the keyboard shortcut (e.g., 1, 2).
        """
        super().__init__(rect)
        self.tower_type_id = tower_type_id
        self.tower_data = tower_data
        self.assets_path = assets_path
        self.hotkey_number = hotkey_number  # NEW: Store the hotkey

        self.cost = self.tower_data.get("cost", 0)
        self.tooltip = f"{self.tower_data.get('name', 'N/A')} - Cost: {self.cost}"

        # --- Asset Loading ---
        self.font = pygame.font.SysFont("segoeui", 14, bold=True)
        self.hotkey_font = pygame.font.SysFont(
            "segoeui", 12, bold=True
        )  # NEW: Font for the hotkey
        self.icon = self._load_icon()

    def _load_icon(self) -> pygame.Surface:
        """
        Loads the tower's icon from the assets folder, or creates a placeholder.
        """
        sprite_key = self.tower_data.get("sprite_key")
        icon_size = (
            self.rect.width - 10,
            self.rect.height - 20,
        )  # Leave space for text

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

        # Fallback to a colored square if no sprite_key or loading fails
        placeholder = pygame.Surface(icon_size)
        placeholder.fill(self.tower_data.get("placeholder_color", (128, 128, 128)))
        return placeholder

    def handle_event(
        self, event: pygame.event.Event, game_state: "GameState"
    ) -> Optional[str]:
        """Handles mouse clicks on the button."""
        action = super().handle_event(event, game_state)
        if action:
            return action

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                logger.info(f"Player clicked tower button: {self.tower_type_id}")
                return f"select_tower_{self.tower_type_id}"

        return None

    def draw(self, screen: pygame.Surface, game_state: "GameState"):
        """Draws the button, its icon, its cost, and its hotkey to the screen."""
        # Determine background color based on state
        is_selected = game_state.selected_tower_to_build == self.tower_type_id
        can_afford = game_state.gold >= self.cost

        bg_color = (40, 50, 60)  # Default
        if is_selected:
            bg_color = (80, 100, 120)
        elif self.is_hovered:
            bg_color = (60, 75, 90)

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=5)

        # Draw Icon
        icon_rect = self.icon.get_rect(centerx=self.rect.centerx, y=self.rect.y + 5)
        screen.blit(self.icon, icon_rect)

        # Draw Cost Text
        cost_color = (255, 215, 0) if can_afford else (180, 40, 40)
        cost_text = self.font.render(f"${self.cost}", True, cost_color)
        text_rect = cost_text.get_rect(
            centerx=self.rect.centerx, bottom=self.rect.bottom - 5
        )
        screen.blit(cost_text, text_rect)

        # Draw border
        border_color = (
            (255, 255, 255)
            if is_selected
            else ((150, 180, 200) if self.is_hovered else (80, 90, 100))
        )
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)

        # --- NEW: Draw Hotkey Number ---
        hotkey_surf = self.hotkey_font.render(
            str(self.hotkey_number), True, (200, 200, 200)
        )
        hotkey_rect = hotkey_surf.get_rect(topleft=(self.rect.x + 5, self.rect.y + 5))
        screen.blit(hotkey_surf, hotkey_rect)
