"""
Nexus Volume Control — Master volume manipulation via pycaw (Windows Core Audio API).
"""

import logging
from ctypes import POINTER, cast

logger = logging.getLogger("nexus.tools.volume")


def _get_volume_interface():
    """Acquire the IAudioEndpointVolume COM interface for the default speakers."""
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def change_volume(level: int) -> str:
    """
    Set the system master volume to a specific percentage.

    Args:
        level: Volume percentage from 0 (mute) to 100 (max).

    Returns:
        Confirmation string with the new volume level.
    """
    try:
        level = max(0, min(100, int(level)))
        volume = _get_volume_interface()
        scalar = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        logger.info("Volume set to %d%%", level)
        return f"Volume set to {level}%."
    except Exception as exc:
        logger.error("Failed to set volume: %s", exc)
        return f"Failed to set volume: {exc}"


def get_volume() -> str:
    """
    Get the current system master volume percentage.

    Returns:
        A string describing the current volume level.
    """
    try:
        volume = _get_volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        pct = round(current * 100)
        muted = volume.GetMute()
        status = f"Current volume: {pct}%"
        if muted:
            status += " (muted)"
        return status
    except Exception as exc:
        logger.error("Failed to get volume: %s", exc)
        return f"Failed to read volume: {exc}"


def toggle_mute() -> str:
    """
    Toggle the system mute state.

    Returns:
        A string confirming whether the system is now muted or unmuted.
    """
    try:
        volume = _get_volume_interface()
        current_mute = volume.GetMute()
        volume.SetMute(not current_mute, None)
        state = "muted" if not current_mute else "unmuted"
        logger.info("System %s.", state)
        return f"System is now {state}."
    except Exception as exc:
        logger.error("Failed to toggle mute: %s", exc)
        return f"Failed to toggle mute: {exc}"
