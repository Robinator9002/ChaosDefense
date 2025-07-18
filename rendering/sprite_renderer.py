# rendering/sprite_renderer.py
import arcade
import logging
from pathlib import Path

# Import the Grid class for type hinting
from level_generation.grid import Grid

logger = logging.getLogger(__name__)


class SpriteRenderer:
    """
    Renders the game's logical grid using sprites.

    This class is responsible for translating the logical Grid object into
    a visible representation on the screen. It loads textures for each tile
    type based on the current level style, with a built-in fallback to simple
    colored squares if a texture is missing.
    """

    def __init__(
        self, grid: Grid, tile_size: int, style_definitions: dict, assets_path: Path
    ):
        """
        Initializes the renderer.

        Args:
            grid (Grid): The logical grid object to be rendered.
            tile_size (int): The size of each tile in pixels.
            style_definitions (dict): The 'tile_definitions' part of a style from the config.
            assets_path (Path): The Path object pointing to the main 'assets' directory.
        """
        self.grid = grid
        self.tile_size = tile_size
        self.style_definitions = style_definitions
        self.assets_path = assets_path

        # Using a SpriteList is highly efficient for drawing many static objects.
        self.tile_sprite_list = arcade.SpriteList(use_spatial_hash=True)
        self._create_sprite_list()

    def _create_sprite_list(self):
        """
        Populates the sprite list based on the logical grid.

        This method iterates through every tile in the grid, determines the
        correct sprite or color, creates a sprite object, and adds it to the
        master sprite list for efficient drawing.
        """
        logger.info("Creating sprite list for level rendering...")
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                tile = self.grid.get_tile(x, y)
                if not tile:
                    continue

                tile_def = self.style_definitions.get(tile.tile_key)
                if not tile_def:
                    logger.warning(
                        f"No style definition found for tile key: '{tile.tile_key}'. Skipping."
                    )
                    continue

                # Calculate the sprite's on-screen position from its grid coordinates.
                center_x = (x * self.tile_size) + (self.tile_size / 2)
                center_y = (y * self.tile_size) + (self.tile_size / 2)

                sprite = self._create_tile_sprite(tile_def, tile.tile_key)
                sprite.center_x = center_x
                sprite.center_y = center_y
                self.tile_sprite_list.append(sprite)

        logger.info(f"Created sprite list with {len(self.tile_sprite_list)} tiles.")

    def _create_tile_sprite(self, tile_def: dict, tile_key: str) -> arcade.Sprite:
        """
        Creates a single sprite, attempting to load its texture and falling back to color.

        Args:
            tile_def (dict): The definition dictionary for this tile type.
            tile_key (str): The key of the tile (e.g., "MOUNTAIN").

        Returns:
            arcade.Sprite: A new sprite, either with a texture or a solid color.
        """
        try:
            # Construct the full path to the sprite asset.
            sprite_path_str = tile_def.get("sprite")
            if not sprite_path_str:
                raise KeyError("Sprite path not defined in config.")

            sprite_path = self.assets_path / "sprites" / sprite_path_str

            if not sprite_path.is_file():
                raise FileNotFoundError(f"Sprite file not found at {sprite_path}")

            # If the file exists, create a sprite with that texture.
            return arcade.Sprite(sprite_path, scale=1)

        except (KeyError, FileNotFoundError) as e:
            # This is our fallback mechanism. If anything goes wrong with finding
            # or loading the sprite, we create a colored square instead.
            logger.warning(
                f"Could not load sprite for '{tile_key}' ({e}). Creating color fallback."
            )
            color = tile_def.get(
                "color", (255, 0, 255)
            )  # Default to magenta if no color is defined
            texture = arcade.make_soft_square_texture(
                self.tile_size, color, outer_alpha=255
            )
            return arcade.Sprite(texture)

    def draw(self):
        """
        Draws all the tile sprites to the screen in a single, efficient batch.
        """
        self.tile_sprite_list.draw()
