import logging
from typing import Optional

logger = logging.getLogger("nexus.tools.window")


def _get_win32():
    try:
        import win32con
        import win32gui
        import win32api
        return win32gui, win32con, win32api
    except ImportError:
        raise RuntimeError("pywin32 not installed. Run: pip install pywin32")


def _enum_all_windows():
    """Return list of (hwnd, title) for all visible windows."""
    win32gui, _, _ = _get_win32()
    windows = []

    def _callback(hwnd, _windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                _windows.append((hwnd, title))
        return True

    win32gui.EnumWindows(_callback, windows)
    return windows


def _find_window(title_substring: str):
    """Find a window handle by title substring (case-insensitive)."""
    win32gui, _, _ = _get_win32()
    title_lower = title_substring.lower()
    windows = _enum_all_windows()
    for hwnd, title in windows:
        if title_lower in title.lower():
            return hwnd, title
    return None, None


def window_list() -> str:
    """List all open windows with visible titles."""
    try:
        windows = _enum_all_windows()
        if not windows:
            return "No open windows found."
        lines = []
        for hwnd, title in windows[:30]:
            lines.append(f"  • {title}")
        if len(windows) > 30:
            lines.append(f"  … and {len(windows) - 30} more.")
        return "Open windows:\n" + "\n".join(lines)
    except Exception as exc:
        return f"Failed to list windows: {exc}"


def window_focus(title: str) -> str:
    """Bring a window to the foreground by its title.

    Args:
        title: Full or partial window title (case-insensitive).
    """
    try:
        win32gui, win32con, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."

        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        logger.info("Focused window: %s", actual_title)
        return f"Focused window: {actual_title}."
    except Exception as exc:
        return f"Failed to focus window: {exc}"


def window_minimize(title: str) -> str:
    """Minimize a window.

    Args:
        title: Full or partial window title.
    """
    try:
        win32gui, win32con, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return f"Minimized: {actual_title}."
    except Exception as exc:
        return f"Failed to minimize: {exc}"


def window_maximize(title: str) -> str:
    """Maximize a window.

    Args:
        title: Full or partial window title.
    """
    try:
        win32gui, win32con, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return f"Maximized: {actual_title}."
    except Exception as exc:
        return f"Failed to maximize: {exc}"


def window_restore(title: str) -> str:
    """Restore a minimized/maximized window to normal size.

    Args:
        title: Full or partial window title.
    """
    try:
        win32gui, win32con, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        return f"Restored: {actual_title}."
    except Exception as exc:
        return f"Failed to restore: {exc}"


def window_close(title: str) -> str:
    """Close a window by sending a close request.

    Args:
        title: Full or partial window title.
    """
    try:
        win32gui, win32con, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return f"Sent close request to: {actual_title}."
    except Exception as exc:
        return f"Failed to close window: {exc}"


def window_move(title: str, x: int, y: int) -> str:
    """Move a window to specific screen coordinates.

    Args:
        title: Full or partial window title.
        x: New horizontal position.
        y: New vertical position.
    """
    try:
        win32gui, _, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."
        win32gui.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0001 | 0x0004)
        return f"Moved '{actual_title}' to ({x}, {y})."
    except Exception as exc:
        return f"Failed to move window: {exc}"


def window_resize(title: str, width: int, height: int) -> str:
    """Resize a window.

    Args:
        title: Full or partial window title.
        width: New width in pixels.
        height: New height in pixels.
    """
    try:
        win32gui, _, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."
        win32gui.SetWindowPos(hwnd, 0, 0, 0, width, height, 0x0002 | 0x0004)
        return f"Resized '{actual_title}' to {width}x{height}."
    except Exception as exc:
        return f"Failed to resize window: {exc}"


def window_get_info(title: str) -> str:
    """Get information about a window (position, size, state).

    Args:
        title: Full or partial window title.
    """
    try:
        win32gui, win32con, _ = _get_win32()
        hwnd, actual_title = _find_window(title)
        if hwnd is None:
            return f"No window found matching '{title}'."

        rect = win32gui.GetWindowRect(hwnd)
        x, y, right, bottom = rect
        width = right - x
        height = bottom - y
        is_iconic = win32gui.IsIconic(hwnd)
        is_zoomed = win32gui.IsZoomed(hwnd)

        state = "normal"
        if is_iconic:
            state = "minimized"
        elif is_zoomed:
            state = "maximized"

        return (
            f"Window: {actual_title}\n"
            f"  Position: ({x}, {y})\n"
            f"  Size: {width}x{height}\n"
            f"  State: {state}"
        )
    except Exception as exc:
        return f"Failed to get window info: {exc}"


def window_get_active() -> str:
    """Get the title and info of the currently active (foreground) window."""
    try:
        win32gui, _, _ = _get_win32()
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        x, y, right, bottom = rect
        return f"Active window: '{title}' at ({x},{y}) size {right - x}x{bottom - y}."
    except Exception as exc:
        return f"Failed to get active window: {exc}"
