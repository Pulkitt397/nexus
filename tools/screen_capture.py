import logging
import time
from pathlib import Path

import config

logger = logging.getLogger("nexus.tools.screen")


def _get_screenshot_path() -> Path:
    config.TEMP_AUDIO_DIR.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    return config.TEMP_AUDIO_DIR / f"screenshot_{ts}.png"


def screen_capture() -> str:
    """Take a screenshot of the entire desktop and save it.

    Returns:
        Path to the saved screenshot image file.
    """
    try:
        from mss import mss
    except ImportError:
        return "mss not installed. Run: pip install mss"

    path = _get_screenshot_path()
    try:
        with mss() as sct:
            sct.shot(output=str(path))
        logger.info("Screenshot saved: %s", path)
        return f"Screenshot saved to {path}."
    except Exception as exc:
        logger.error("Screenshot failed: %s", exc)
        return f"Screenshot failed: {exc}"


def screen_capture_monitor(monitor: int = 0) -> str:
    """Take a screenshot of a specific monitor.

    Args:
        monitor: Monitor number (0 = all-in-one, 1 = first monitor, 2 = second, etc.).
    """
    try:
        from mss import mss
    except ImportError:
        return "mss not installed."

    path = _get_screenshot_path()
    try:
        with mss() as sct:
            mon = sct.monitors[monitor] if monitor < len(sct.monitors) else sct.monitors[1]
            sct.shot(mon=monitor if monitor > 0 else 1, output=str(path))
        return f"Monitor {monitor} screenshot saved to {path}."
    except Exception as exc:
        return f"Screenshot failed: {exc}"


def screen_capture_region(left: int, top: int, width: int, height: int) -> str:
    """Take a screenshot of a specific screen region.

    Args:
        left: X coordinate of top-left corner.
        top: Y coordinate of top-left corner.
        width: Width of the region in pixels.
        height: Height of the region in pixels.
    """
    try:
        from mss import mss
    except ImportError:
        return "mss not installed."

    path = _get_screenshot_path()
    try:
        with mss() as sct:
            region = {"left": left, "top": top, "width": width, "height": height}
            sct.shot(output=str(path), **region)
        return f"Region screenshot saved to {path}."
    except Exception as exc:
        return f"Region screenshot failed: {exc}"


def screen_get_text() -> str:
    """Extract all visible text from the screen using OCR.

    Requires Tesseract OCR installed on the system.
    Download from: https://github.com/UB-Mannheim/tesseract/wiki
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "pytesseract not installed. Run: pip install pytesseract"

    try:
        from mss import mss
        import numpy as np
    except ImportError:
        return "Required libraries missing."

    try:
        with mss() as sct:
            screenshot = sct.grab(sct.monitors[0])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        text = pytesseract.image_to_string(img)
        text = text.strip()
        if not text:
            return "No text detected on screen."
        if len(text) > 3000:
            text = text[:3000] + "\n\n...[truncated]"
        return f"Screen text:\n{text}"
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return f"OCR failed: {exc}. Is Tesseract installed?"


def screen_find_text(text: str) -> str:
    """Search for text on screen and return its location.

    Args:
        text: The text to search for on screen.
    """
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
    except ImportError:
        return "pytesseract not installed."

    try:
        from mss import mss
    except ImportError:
        return "mss not installed."

    try:
        with mss() as sct:
            screenshot = sct.grab(sct.monitors[0])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

        img_np = np.array(img)
        boxes = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        found = []
        for i, word in enumerate(boxes["text"]):
            if text.lower() in word.lower():
                x, y, w, h = boxes["left"][i], boxes["top"][i], boxes["width"][i], boxes["height"][i]
                found.append(f"  '{word}' at ({x}, {y}) size ({w}x{h})")

        if found:
            return f"Found text '{text}':\n" + "\n".join(found[:10])
        return f"Text '{text}' not found on screen."
    except Exception as exc:
        return f"Search failed: {exc}"


def screen_get_color(x: int, y: int) -> str:
    """Get the color of the pixel at the given screen coordinates.

    Args:
        x: Horizontal position.
        y: Vertical position.
    """
    try:
        from mss import mss
        import numpy as np
    except ImportError:
        return "Required libraries missing."

    try:
        with mss() as sct:
            region = {"left": x, "top": y, "width": 1, "height": 1}
            pixel = sct.grab(region)
            color = pixel.pixel(0, 0)
            hex_color = "#{:02X}{:02X}{:02X}".format(*color)
            return f"Color at ({x}, {y}): RGB{color} ({hex_color})."
    except Exception as exc:
        return f"Failed to get pixel color: {exc}"
