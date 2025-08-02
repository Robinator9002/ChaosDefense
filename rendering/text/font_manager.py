# rendering/font/font_manager.py
import pygame
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FontManager:
    """
    A centralized manager for loading, caching, and providing access to all
    fonts defined in the UI theme.

    This class prevents the repeated loading of font files and the scattering
    of font definitions across multiple UI components. It reads a font
    configuration dictionary and provides `pygame.font.Font` objects on demand.
    """

    def __init__(self, font_config: Dict[str, Any]):
        """
        Initializes the FontManager and pre-loads all defined fonts.

        Args:
            font_config (Dict[str, Any]): The 'fonts' section of the
                                          ui_theme.json configuration file.
        """
        self._font_cache: Dict[str, pygame.font.Font] = {}
        self._config = font_config
        self._load_fonts()

    def _load_fonts(self):
        """
        Parses the font configuration and loads each defined font style into
        the cache.
        """
        try:
            family = self._config.get("default_font_family", "sans-serif")
            definitions = self._config.get("definitions", {})

            if not definitions:
                logger.warning("No font definitions found in the theme config.")
                return

            logger.info(f"Loading fonts from family: '{family}'...")
            for name, definition in definitions.items():
                if not isinstance(definition, dict):
                    logger.warning(f"Skipping invalid font definition for '{name}'.")
                    continue

                size = definition.get("size", 12)
                style = definition.get("style", [])
                is_bold = "bold" in style
                is_italic = "italic" in style

                # pygame.font.SysFont is a reliable way to get system fonts.
                # For custom .ttf files, pygame.font.Font(path, size) would be used.
                try:
                    font_obj = pygame.font.SysFont(
                        family, size, bold=is_bold, italic=is_italic
                    )
                    self._font_cache[name] = font_obj
                    logger.debug(
                        f"  - Loaded font '{name}' (size: {size}, bold: {is_bold}, italic: {is_italic})"
                    )
                except pygame.error as e:
                    logger.error(
                        f"Could not load system font '{family}' for style '{name}'. Error: {e}"
                    )
                    # As a fallback, try to load the default pygame font
                    self._font_cache[name] = pygame.font.Font(None, size)

            logger.info("FontManager initialized successfully with all fonts loaded.")

        except Exception as e:
            logger.critical(
                f"Failed to initialize FontManager. Error: {e}", exc_info=True
            )
            # Ensure the cache is empty if initialization fails
            self._font_cache.clear()

    def get_font(
        self, name: str, default_size: int = 14, **kwargs: Any
    ) -> pygame.font.Font:
        """
        Retrieves a pre-loaded font object from the cache.

        Args:
            name (str): The semantic name of the font (e.g., 'title_large').
            default_size (int): A fallback size if the requested font name
                                does not exist.
            **kwargs: Catches any extra keyword arguments (like 'bold=True')
                      to prevent a TypeError without affecting the logic,
                      as font styles are now defined in the theme config.

        Returns:
            A pygame.font.Font object. If the requested font is not found,
            it returns a default Pygame font as a fallback to prevent crashes.
        """
        font = self._font_cache.get(name)
        if font:
            return font
        else:
            logger.warning(
                f"Font '{name}' not found in cache. Returning default fallback font."
            )
            # Return a default system font to avoid crashing the game.
            return pygame.font.Font(None, default_size)
