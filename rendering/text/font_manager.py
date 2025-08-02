# rendering/font/font_manager.py
import pygame
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class FontManager:
    """
    A centralized manager for loading, caching, and providing access to all
    fonts defined in the UI theme.

    MODIFIED: Now loads fonts from a bundled file instead of the system,
    ensuring a consistent visual experience for all players (Issue #5).
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
        # --- NEW: Define path to the font file ---
        # We assume the font file is located in 'assets/fonts/'.
        # In a real project, this path would be passed in or constructed
        # from a global assets path constant.
        self._font_path = Path("assets") / "fonts" / "main_font.ttf"
        self._load_fonts()

    def _load_fonts(self):
        """
        Parses the font configuration and loads each defined font style into
        the cache from a bundled .ttf file.
        """
        try:
            definitions = self._config.get("definitions", {})
            if not definitions:
                logger.warning("No font definitions found in the theme config.")
                return

            logger.info(f"Loading fonts from file: '{self._font_path}'...")
            for name, definition in definitions.items():
                if not isinstance(definition, dict):
                    logger.warning(f"Skipping invalid font definition for '{name}'.")
                    continue

                size = definition.get("size", 12)
                # Note: 'style' (bold/italic) is often handled by using
                # separate font files (e.g., 'main_font_bold.ttf'). For simplicity,
                # we'll use Pygame's built-in style properties for now.
                style = definition.get("style", [])
                is_bold = "bold" in style
                is_italic = "italic" in style

                try:
                    # --- MODIFIED: Load font directly from the file path ---
                    font_obj = pygame.font.Font(self._font_path, size)
                    font_obj.set_bold(is_bold)
                    font_obj.set_italic(is_italic)
                    self._font_cache[name] = font_obj
                    logger.debug(
                        f"  - Loaded font '{name}' (size: {size}, bold: {is_bold}, italic: {is_italic})"
                    )
                except pygame.error as e:
                    logger.error(
                        f"Could not load font from '{self._font_path}'. Error: {e}"
                    )
                    # As a fallback, try to load the default pygame font.
                    self._font_cache[name] = pygame.font.Font(None, size)

            logger.info("FontManager initialized successfully with all fonts loaded.")

        except Exception as e:
            logger.critical(
                f"Failed to initialize FontManager. Error: {e}", exc_info=True
            )
            self._font_cache.clear()

    def get_font(
        self, name: str, default_size: int = 24, **kwargs: Any
    ) -> pygame.font.Font:
        """
        Retrieves a pre-loaded font object from the cache.
        """
        font = self._font_cache.get(name)
        if font:
            return font
        else:
            logger.warning(
                f"Font '{name}' not found in cache. Returning default fallback font."
            )
            return pygame.font.Font(None, default_size)
