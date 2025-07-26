# game_logic/level_manager.py
import logging
from pathlib import Path

# Project-specific imports
from game_logic.level_generation.grid import Grid
from game_logic.level_generation.generator import LevelGenerator

logger = logging.getLogger(__name__)


class LevelManager:
    """
    Manages the loading and creation of game levels based on style presets.

    This class reads level style configurations, which include both visual
    definitions and procedural generation parameters, and uses them to
    construct fully realized game levels.
    """

    def __init__(self, level_styles: dict):
        """
        Initializes the LevelManager with level style data.

        Args:
            level_styles (dict): The loaded content of level_styles.json.
        """
        if not isinstance(level_styles, dict) or not level_styles:
            raise ValueError("Level styles data is missing or invalid.")
        self.level_styles = level_styles
        logger.info(f"LevelManager initialized with {len(level_styles)} style presets.")

    def get_level_presets(self) -> list[str]:
        """
        Returns a list of available level preset names (e.g., "Forest", "Rocky").

        Returns:
            list[str]: A list of keys for the available level styles.
        """
        return list(self.level_styles.keys())

    def build_level_from_preset(self, preset_name: str) -> tuple[Grid, dict]:
        """
        Constructs a new Grid object based on a named preset.

        Args:
            preset_name (str): The key of the preset to use (e.g., "Forest").

        Returns:
            tuple[Grid, dict]: A tuple containing the newly generated Grid
                               and the full style definition dictionary for that preset.

        Raises:
            KeyError: If the preset_name does not exist in the loaded styles.
        """
        logger.info(f"Building level from preset: '{preset_name}'")
        if preset_name not in self.level_styles:
            raise KeyError(f"Level preset '{preset_name}' not found.")

        style_config = self.level_styles[preset_name]
        gen_params = style_config.get("generation_params")

        if not gen_params:
            raise ValueError(f"Preset '{preset_name}' is missing 'generation_params'.")

        grid_width = gen_params.get("grid_width")
        grid_height = gen_params.get("grid_height")

        if not all([grid_width, grid_height]):
            raise ValueError(f"Preset '{preset_name}' is missing grid dimensions.")

        # 1. Create a new Grid instance with the specified dimensions.
        grid = Grid(width=grid_width, height=grid_height)

        # 2. Use the LevelGenerator as a tool to populate the grid.
        #    We pass the specific generation parameters for this preset.
        LevelGenerator.generate(grid, gen_params)

        # 3. Return the populated grid and the complete style configuration,
        #    which the game will need for rendering (background color, tile sprites).
        return grid, style_config
