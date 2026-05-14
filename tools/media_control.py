import logging

logger = logging.getLogger("nexus.tools.media")


def _send_media_key(key_code: int) -> bool:
    """Send a virtual media key press using Windows API."""
    import ctypes
    from ctypes import wintypes

    USER32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002

    try:
        USER32.keybd_event(key_code, 0, 0, 0)
        USER32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


_VK_MEDIA_PLAY_PAUSE = 0xB3
_VK_MEDIA_NEXT_TRACK = 0xB0
_VK_MEDIA_PREV_TRACK = 0xB1
_VK_MEDIA_STOP = 0xB2
_VK_VOLUME_MUTE = 0xAD
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF


def media_play_pause() -> str:
    """Toggle media playback (play/pause)."""
    if _send_media_key(_VK_MEDIA_PLAY_PAUSE):
        logger.info("Media play/pause toggled.")
        return "Toggled play/pause."
    return "Failed to send media key."


def media_next() -> str:
    """Skip to the next track."""
    if _send_media_key(_VK_MEDIA_NEXT_TRACK):
        logger.info("Media next track.")
        return "Skipped to next track."
    return "Failed to send media key."


def media_previous() -> str:
    """Go back to the previous track."""
    if _send_media_key(_VK_MEDIA_PREV_TRACK):
        logger.info("Media previous track.")
        return "Went to previous track."
    return "Failed to send media key."


def media_stop() -> str:
    """Stop media playback."""
    if _send_media_key(_VK_MEDIA_STOP):
        logger.info("Media stopped.")
        return "Stopped media playback."
    return "Failed to send media key."
