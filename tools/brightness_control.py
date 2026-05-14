"""
Nexus Brightness Control — Screen brightness manipulation via screen-brightness-control.
"""

import logging

import screen_brightness_control as sbc

logger = logging.getLogger("nexus.tools.brightness")


def change_brightness(level: int) -> str:
    """
    Set the screen brightness to a specific percentage.

    Args:
        level: Brightness percentage from 0 (dimmest) to 100 (brightest).

    Returns:
        Confirmation string with the new brightness level.
    """
    try:
        level = max(0, min(100, int(level)))
        sbc.set_brightness(level)
        logger.info("Brightness set to %d%%", level)
        return f"Brightness set to {level}%."
    except Exception as exc:
        logger.error("Failed to set brightness: %s", exc)
        return f"Failed to set brightness: {exc}"


def get_brightness() -> str:
    """
    Get the current screen brightness percentage.

    Returns:
        A string describing the current brightness level.
    """
    try:
        current = sbc.get_brightness()
        # sbc.get_brightness() returns a list (one per display)
        if isinstance(current, list):
            levels = ", ".join(f"{b}%" for b in current)
            return f"Current brightness: {levels}."
        return f"Current brightness: {current}%."
    except Exception as exc:
        logger.error("Failed to get brightness: %s", exc)
        return f"Failed to read brightness: {exc}"
