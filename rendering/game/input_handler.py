# rendering/game/input_handler.py
import pygame
import logging
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from game_logic.game_manager import GameManager
    from rendering.hud.ui_manager import UIManager
    from .camera import Camera

logger = logging.getLogger(__name__)


class InputHandler:
    """
    Manages all in-game (non-UI) player input, including keyboard shortcuts
    and mouse interactions with the game world. This decouples input processing
    from the main game loop.
    """

    def __init__(
        self,
        game_manager: "GameManager",
        ui_manager: "UIManager",
        camera: "Camera",
    ):
        """
        Initializes the InputHandler.

        Args:
            game_manager (GameManager): The central game logic manager.
            ui_manager (UIManager): The manager for the heads-up display.
            camera (Camera): The game's camera object.
        """
        self.game_manager = game_manager
        self.ui_manager = ui_manager
        self.camera = camera

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Processes a single Pygame event for in-game actions.

        Args:
            event (pygame.event.Event): The event to process.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouse_down(event)
        elif event.type == pygame.KEYDOWN:
            return self._handle_keyboard_input(event)

        return False

    def _handle_mouse_down(self, event: pygame.event.Event) -> bool:
        """Handles mouse down events that were not consumed by the UI."""
        if event.button == 1:
            self._handle_map_click(event)
            return True
        elif event.button == 3:
            game_state = self.game_manager.game_state
            if game_state.selected_tower_to_build or game_state.selected_entity_id:
                game_state.clear_selection()
            return True
        return False

    def _handle_map_click(self, event: pygame.event.Event):
        """Handles left-clicks on the game map for building or selecting towers."""
        game_state = self.game_manager.game_state

        if game_state.selected_tower_to_build:
            world_pos = self.camera.screen_to_world(pygame.Vector2(event.pos))
            tile_x = int(world_pos.x // self.game_manager.tile_size)
            tile_y = int(world_pos.y // self.game_manager.tile_size)
            self.game_manager.place_tower(
                game_state.selected_tower_to_build, tile_x, tile_y
            )
            return

        mouse_pos = pygame.Vector2(event.pos)
        clicked_on_tower = False
        for tower in self.game_manager.towers.values():
            scaled_pos = (tower.pos * self.camera.zoom) + self.camera.offset
            scaled_rect = pygame.Rect(
                0,
                0,
                tower.rect.width * self.camera.zoom,
                tower.rect.height * self.camera.zoom,
            )
            scaled_rect.center = scaled_pos

            if scaled_rect.collidepoint(mouse_pos):
                if game_state.selected_entity_id == tower.entity_id:
                    game_state.clear_selection()
                else:
                    game_state.selected_entity_id = tower.entity_id
                    logger.info(f"Player selected tower with ID: {tower.entity_id}")
                clicked_on_tower = True
                break

        if not clicked_on_tower:
            game_state.clear_selection()

    def _handle_keyboard_input(self, event: pygame.event.Event) -> bool:
        """Handles all keyboard presses for in-game actions."""
        mods = pygame.key.get_mods()
        is_ctrl_pressed = mods & pygame.KMOD_CTRL

        # --- UI Navigation Hotkeys ---
        # These can remain as direct calls as they are simple UI state changes.
        if event.key == pygame.K_TAB:
            # self.ui_manager.cycle_category() # This method doesn't exist, might be a planned feature
            return True

        f_key_map = {
            pygame.K_F1: 0,
            pygame.K_F2: 1,
            pygame.K_F3: 2,
            pygame.K_F4: 3,
            pygame.K_F5: 4,
            pygame.K_F6: 5,
            pygame.K_F7: 6,
            pygame.K_F8: 7,
            pygame.K_F9: 8,
            pygame.K_F10: 9,
        }
        if event.key in f_key_map:
            self.ui_manager.set_active_category_by_index(f_key_map[event.key])
            return True

        # --- Tower Selection Hotkeys ---
        num_key_map = {
            pygame.K_1: 0,
            pygame.K_2: 1,
            pygame.K_3: 2,
            pygame.K_4: 3,
            pygame.K_5: 4,
            pygame.K_6: 5,
            pygame.K_7: 6,
            pygame.K_8: 7,
            pygame.K_9: 8,
            pygame.K_0: 9,
        }
        if is_ctrl_pressed and event.key in num_key_map:
            self.ui_manager.set_active_category_by_index(num_key_map[event.key])
            return True

        # --- MODIFIED: Decoupled hotkey logic (Issue #8) ---
        # The InputHandler no longer contains logic for how to select a tower.
        # It simply translates the key press into an index and tells the
        # UIManager to handle it. This improves separation of concerns.
        if not is_ctrl_pressed and event.key in num_key_map:
            hotkey_index = num_key_map[event.key]
            self.ui_manager.select_tower_by_hotkey(
                hotkey_index, self.game_manager.game_state
            )
            return True

        return False
