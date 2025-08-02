# rendering/text/text_renderer.py
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

    MODIFIED: Now robustly handles single words that are longer than the
    max_width by breaking them across multiple lines. This prevents UI
    layout breakage from long, uninterrupted strings (Issue #2).
    """
    words = text.split(" ")
    lines: List[str] = []
    current_line = ""

    for word in words:
        # --- NEW: Handle words longer than the max_width ---
        if font.size(word)[0] > max_width:
            # First, if the current line has any content, add it to the list.
            if current_line:
                lines.append(current_line)
                current_line = ""

            # Then, break the overly long word character by character.
            temp_word_line = ""
            for char in word:
                test_char_line = f"{temp_word_line}{char}"
                if font.size(test_char_line)[0] <= max_width:
                    temp_word_line = test_char_line
                else:
                    # The line is full, add it and start a new one with the current char.
                    lines.append(temp_word_line)
                    temp_word_line = char
            # The remainder of the long word becomes the new current line.
            current_line = temp_word_line
            continue  # Proceed to the next word in the main loop.

        # Original logic for adding normal words to the current line.
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            # The new word doesn't fit, so finalize the current line.
            lines.append(current_line)
            # And start a new line with the current word.
            current_line = word

    # Add the last remaining line to the list.
    if current_line:
        lines.append(current_line)

    # Render each line of text into a separate surface, skipping any empty lines.
    rendered_lines = [font.render(line, True, color) for line in lines if line]
    return rendered_lines
