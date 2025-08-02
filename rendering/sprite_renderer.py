# rendering/sprite_renderer.py
import pygame
import logging
from pathlib import Path

# Import the Grid class for type hinting.
from game_logic.level_generation.grid import Grid

logger = logging.getLogger(__name__)


class SpriteRenderer:
    """
    Renders the game's logical grid using Pygame surfaces.

    This class is responsible for translating the logical Grid object into a
    visible representation. It pre-renders the entire static map onto a single
    large surface for efficient drawing. It also handles camera transformations
    like zooming and panning when drawing this surface to the screen.
    """

    def __init__(
        self, grid: Grid, tile_size: int, style_definitions: dict, assets_path: Path
    ):
        """
        Initializes the renderer and pre-renders the map.

        Args:
            grid (Grid): The logical grid object to be rendered.
            tile_size (int): The size of each tile in pixels.
            style_definitions (dict): The 'tile_definitions' part of a style config.
            assets_path (Path): The Path object pointing to the main 'assets' directory.
        """
        self.grid = grid
        self.tile_size = tile_size
        self.style_definitions = style_definitions
        self.assets_path = assets_path

        # This surface will hold the entire rendered map.
        self.map_surface = self._create_map_surface()

    def _load_tile_image(self, tile_def: dict, tile_key: str) -> pygame.Surface:
        """
        Creates a single tile surface, loading its texture or falling back to a color.

        Args:
            tile_def (dict): The definition dictionary for this tile type.
            tile_key (str): The key of the tile (e.g., "MOUNTAIN").

        Returns:
            pygame.Surface: A new surface for the tile, correctly sized.
        """
        try:
            sprite_path_str = tile_def.get("sprite")
            if not sprite_path_str:
                raise KeyError("Sprite path not defined in config.")

            sprite_path = self.assets_path / "sprites" / sprite_path_str
            if not sprite_path.is_file():
                raise FileNotFoundError(f"Sprite file not found at {sprite_path}")

            image = pygame.image.load(sprite_path).convert_alpha()
            return pygame.transform.scale(image, (self.tile_size, self.tile_size))

        except (KeyError, FileNotFoundError, pygame.error) as e:
            logger.warning(
                f"Could not load sprite for '{tile_key}' ({e}). Creating color fallback."
            )
            color = tile_def.get("color", (255, 0, 255))
            surface = pygame.Surface((self.tile_size, self.tile_size))
            surface.fill(color)
            return surface

    def _create_map_surface(self) -> pygame.Surface:
        """
        Creates a single, large surface with the entire static map pre-drawn.
        """
        map_width_px = self.grid.width * self.tile_size
        map_height_px = self.grid.height * self.tile_size
        logger.info(f"Creating {map_width_px}x{map_height_px} map surface...")

        map_surface = pygame.Surface((map_width_px, map_height_px), pygame.SRCALPHA)
        map_surface.fill((0, 255, 0))

        drawn_tiles_count = 0
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                tile = self.grid.get_tile(x, y)
                if not tile:
                    continue

                tile_def = self.style_definitions.get(tile.tile_key)
                if not tile_def:
                    logger.warning(
                        f"No style definition for tile key: '{tile.tile_key}'. Skipping."
                    )
                    continue

                tile_surface = self._load_tile_image(tile_def, tile.tile_key)
                px_position = (x * self.tile_size, y * self.tile_size)
                map_surface.blit(tile_surface, px_position)
                drawn_tiles_count += 1

        if drawn_tiles_count == 0:
            logger.critical(
                "CRITICAL: Map surface is empty! No tile definitions found or all were skipped. "
                "The screen will display a solid color. Please check level_styles.json."
            )
        else:
            logger.info(
                f"Map surface created successfully with {drawn_tiles_count} tiles."
            )

        return map_surface

    def draw(self, screen: pygame.Surface, camera_offset: pygame.Vector2, zoom: float):
        """
        Draws the map to the screen, applying camera zoom and offset.

        Args:
            screen (pygame.Surface): The main display surface to draw on.
            camera_offset (pygame.Vector2): The top-left position of the camera view.
            zoom (float): The current zoom level.
        """
        if zoom == 1.0:
            scaled_surface = self.map_surface
        else:
            new_size = (
                int(self.map_surface.get_width() * zoom),
                int(self.map_surface.get_height() * zoom),
            )
            # --- MODIFIED: Switched to pygame.transform.scale for better performance (Issue #4) ---
            # smoothscale provides higher quality but is too slow for real-time
            # map scaling. 'scale' is much faster and the quality difference
            # is acceptable for this use case.
            scaled_surface = pygame.transform.scale(self.map_surface, new_size)

        screen.blit(scaled_surface, camera_offset)
