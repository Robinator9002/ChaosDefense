# rendering/hud/text_renderer.py
import pygame
from typing import List, Tuple

# It's good practice to have a central place for reusable UI utilities.
# This module will contain functions for advanced text rendering, starting
# with a much-needed text wrapping function.


def render_text_wrapped(
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    max_width: int,
) -> List[pygame.Surface]:
    """
    Renders a string of text, automatically wrapping it to fit within a
    specified maximum width.

    This is a crucial utility for creating robust UI elements that can handle
    variable-length text without overflowing their containers.

    Args:
        text (str): The full string of text to be rendered.
        font (pygame.font.Font): The Pygame font object to use for rendering.
        color (Tuple[int, int, int]): The RGB color for the text.
        max_width (int): The maximum width in pixels that a line of text
                         can occupy before being wrapped.

    Returns:
        List[pygame.Surface]: A list of Pygame surfaces, where each surface
                              represents a single, rendered line of the
                              wrapped text.
    """
    words = text.split(" ")
    lines: List[str] = []
    current_line = ""

    for word in words:
        # Check if adding the new word exceeds the max width
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            # The new word doesn't fit, so finalize the current line
            lines.append(current_line)
            # Start a new line with the current word
            current_line = word

    # Add the last remaining line
    lines.append(current_line)

    # Render each line of text into a separate surface
    rendered_lines = [font.render(line, True, color) for line in lines]
    return rendered_lines
