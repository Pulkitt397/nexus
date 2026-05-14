import logging
import time

logger = logging.getLogger("nexus.tools.mouse_keyboard")


def _ensure_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1
        return pyautogui
    except ImportError:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def mouse_move(x: int, y: int) -> str:
    """Move the mouse cursor to absolute screen coordinates.

    Args:
        x: Horizontal position in pixels.
        y: Vertical position in pixels.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.moveTo(x, y, duration=0.3)
        return f"Moved mouse to ({x}, {y})."
    except Exception as exc:
        logger.error("Mouse move failed: %s", exc)
        return f"Failed to move mouse: {exc}"


def mouse_click(x: int, y: int, button: str = "left") -> str:
    """Click at absolute screen coordinates.

    Args:
        x: Horizontal position.
        y: Vertical position.
        button: 'left', 'right', or 'middle'.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.click(x, y, button=button)
        return f"Clicked {button} at ({x}, {y})."
    except Exception as exc:
        logger.error("Mouse click failed: %s", exc)
        return f"Failed to click: {exc}"


def mouse_double_click(x: int, y: int) -> str:
    """Double-click at absolute screen coordinates.

    Args:
        x: Horizontal position.
        y: Vertical position.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.doubleClick(x, y)
        return f"Double-clicked at ({x}, {y})."
    except Exception as exc:
        return f"Failed to double-click: {exc}"


def mouse_right_click(x: int, y: int) -> str:
    """Right-click at absolute screen coordinates.

    Args:
        x: Horizontal position.
        y: Vertical position.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.rightClick(x, y)
        return f"Right-clicked at ({x}, {y})."
    except Exception as exc:
        return f"Failed to right-click: {exc}"


def mouse_drag(x1: int, y1: int, x2: int, y2: int) -> str:
    """Drag the mouse from one point to another.

    Args:
        x1: Start horizontal position.
        y1: Start vertical position.
        x2: End horizontal position.
        y2: End vertical position.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.moveTo(x1, y1, duration=0.2)
        pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)
        return f"Dragged from ({x1},{y1}) to ({x2},{y2})."
    except Exception as exc:
        return f"Failed to drag: {exc}"


def mouse_scroll(amount: int) -> str:
    """Scroll the mouse wheel.

    Args:
        amount: Positive = scroll up, negative = scroll down (e.g. -3 scrolls down 3 clicks).
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.scroll(amount)
        direction = "up" if amount > 0 else "down"
        return f"Scrolled {direction} {abs(amount)} clicks."
    except Exception as exc:
        return f"Failed to scroll: {exc}"


def mouse_position() -> str:
    """Get the current mouse cursor position on screen."""
    try:
        pyautogui = _ensure_pyautogui()
        x, y = pyautogui.position()
        return f"Mouse position: ({x}, {y})."
    except Exception as exc:
        return f"Failed to get mouse position: {exc}"


def keyboard_type(text: str) -> str:
    """Type text at the current cursor position (simulates real keyboard input).

    Args:
        text: The text to type.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.typewrite(text, interval=0.02)
        preview = text[:60] + "..." if len(text) > 60 else text
        return f"Typed: {preview}"
    except Exception as exc:
        return f"Failed to type: {exc}"


def keyboard_press(key: str) -> str:
    """Press a single keyboard key.

    Args:
        key: Key name like 'enter', 'escape', 'tab', 'up', 'down', 'f5', 'ctrl', 'win', etc.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.press(key)
        return f"Pressed key: {key}"
    except Exception as exc:
        return f"Failed to press key: {exc}"


def keyboard_hotkey(keys: str) -> str:
    """Press a keyboard shortcut combination.

    Args:
        keys: Comma-separated key names like 'ctrl,c' for Ctrl+C, 'ctrl,shift,escape' for Ctrl+Shift+Esc.
    """
    try:
        pyautogui = _ensure_pyautogui()
        key_list = [k.strip() for k in keys.split(",")]
        pyautogui.hotkey(*key_list)
        return f"Pressed hotkey: {keys}"
    except Exception as exc:
        return f"Failed to press hotkey: {exc}"


def keyboard_hold(key: str) -> str:
    """Hold down a keyboard key.

    Args:
        key: Key name to hold (e.g. 'shift', 'ctrl').
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.keyDown(key)
        return f"Holding key: {key}"
    except Exception as exc:
        return f"Failed to hold key: {exc}"


def keyboard_release(key: str) -> str:
    """Release a previously held keyboard key.

    Args:
        key: Key name to release.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.keyUp(key)
        return f"Released key: {key}"
    except Exception as exc:
        return f"Failed to release key: {exc}"


def keyboard_write_enter(text: str) -> str:
    """Type text and press Enter.

    Args:
        text: The text to type before pressing Enter.
    """
    try:
        pyautogui = _ensure_pyautogui()
        pyautogui.typewrite(text, interval=0.02)
        pyautogui.press("enter")
        preview = text[:60] + "..." if len(text) > 60 else text
        return f"Typed '{preview}' and pressed Enter."
    except Exception as exc:
        return f"Failed: {exc}"
