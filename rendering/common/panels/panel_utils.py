# rendering/hud/panel_utils.py
from typing import Dict, Any


def get_nested_value(data: Any, path: str) -> Any:
    """
    Safely retrieves a value from a nested structure (dicts, lists, or objects)
    using a dot-separated path.
    Example path: 'auras[0].effects.damage_boost.potency' or 'damage'
    """
    # Replace list indices like [0] with .0 for uniform splitting
    keys = path.replace("[", ".").replace("]", "").split(".")
    current_level = data
    for key in keys:
        if current_level is None:
            return None

        if isinstance(current_level, dict):
            current_level = current_level.get(key)
        elif isinstance(current_level, list) and key.isdigit():
            try:
                current_level = current_level[int(key)]
            except IndexError:
                return None
        # --- FIX: Handle object attributes using getattr ---
        elif hasattr(current_level, key):
            current_level = getattr(current_level, key)
        # --- END FIX ---
        else:
            # If no method works, the path is invalid for the current level
            return None
    return current_level


def format_stat_value(value: Any, format_key: str) -> str:
    """Formats a raw stat value into a display-ready string based on a format key."""
    if value is None:
        return "N/A"

    if format_key == "per_second":
        return f"{value:.2f}/s"
    elif format_key == "percentage":
        return f"{int(value * 100)}%"
    elif format_key == "percentage_boost":
        return f"+{int((value - 1) * 100)}%"
    elif format_key == "multiplier":
        return f"{value:.2f}x"
    else:
        # Check if value is a float and format it to remove trailing .0
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
