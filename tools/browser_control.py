import logging
import os
import time
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger("nexus.tools.browser")

_BROWSER = None
_BROWSER_CONTEXT = None
_PAGE = None
_PLAYWRIGHT = None


def _ensure_browser():
    global _BROWSER, _BROWSER_CONTEXT, _PAGE, _PLAYWRIGHT
    if _BROWSER is not None and _PAGE is not None:
        try:
            _PAGE.title()
            return
        except Exception:
            pass
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright not installed. Run: pip install playwright")
    _PLAYWRIGHT = sync_playwright().start()

    launch_opts = dict(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--start-maximized",
        ],
    )

    # Try system Chrome/Edge first (no separate download needed),
    # then fall back to bundled Chromium (requires `playwright install chromium`)
    for channel in ("chrome", "msedge", None):
        try:
            _BROWSER = _PLAYWRIGHT.chromium.launch(channel=channel, **launch_opts)
            browser_name = channel or "chromium"
            logger.info("Browser launched using system %s.", browser_name)
            break
        except Exception:
            continue
    else:
        raise RuntimeError(
            "No browser found. Install Chrome/Edge, or run: python -m playwright install chromium"
        )

    _BROWSER_CONTEXT = _BROWSER.new_context(
        viewport={"width": 1280, "height": 720},
        no_viewport=True,
    )
    _PAGE = _BROWSER_CONTEXT.new_page()
    logger.info("Browser ready.")


def _safe_page():
    """Return the current page, ensuring browser is alive."""
    _ensure_browser()
    return _PAGE


def browser_launch() -> str:
    """Open a new visible browser window (reuses if already open)."""
    try:
        _ensure_browser()
        return "Browser is open and ready."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("Browser launch failed: %s", exc)
        return f"Failed to launch browser: {exc}"


def browser_navigate(url: str) -> str:
    """Go to a URL in the browser.

    Args:
        url: The full URL (e.g. 'https://www.youtube.com'). 'https://' is prepended if missing.
    """
    page = _safe_page()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)
        logger.info("Navigated to: %s", url)
        return f"Navigated to {url}."
    except Exception as exc:
        logger.error("Navigation failed: %s", exc)
        return f"Navigation to {url} failed: {exc}"


def browser_click(selector: str) -> str:
    """Click an element on the page using a CSS selector or text selector.

    Args:
        selector: CSS selector (e.g. '#search-button') or text selector (e.g. 'text=Search').
    """
    page = _safe_page()
    try:
        page.click(selector, timeout=10000)
        logger.info("Clicked: %s", selector)
        return f"Clicked element '{selector}'."
    except Exception as exc:
        logger.error("Click failed: %s", exc)
        return f"Failed to click '{selector}': {exc}"


def browser_type(selector: str, text: str) -> str:
    """Type text into an input field on the page.

    Args:
        selector: CSS or text selector for the input element.
        text: The text to type.
    """
    page = _safe_page()
    try:
        page.fill(selector, "", timeout=5000)
        page.type(selector, text, delay=20)
        logger.info("Typed into %s", selector)
        return f"Typed into '{selector}'."
    except Exception as exc:
        logger.error("Typing failed: %s", exc)
        return f"Failed to type into '{selector}': {exc}"


def browser_type_text(text: str) -> str:
    """Type text directly into the currently focused element.

    Args:
        text: The text to type.
    """
    page = _safe_page()
    try:
        page.keyboard.type(text, delay=10)
        return f"Typed text: {text[:50]}..."
    except Exception as exc:
        return f"Failed to type text: {exc}"


def browser_press_key(key: str) -> str:
    """Press a keyboard key in the browser.

    Args:
        key: Key name like 'Enter', 'Escape', 'Tab', 'ArrowDown', 'ArrowUp', 'Control+a', etc.
    """
    page = _safe_page()
    try:
        page.keyboard.press(key)
        return f"Pressed key: {key}"
    except Exception as exc:
        return f"Failed to press key: {exc}"


def browser_get_text() -> str:
    """Get all visible text content from the current page."""
    page = _safe_page()
    try:
        text = page.inner_text("body")
        text = text.strip()
        if len(text) > 5000:
            text = text[:5000] + "\n\n...[truncated]"
        return text or "Page appears to have no visible text."
    except Exception as exc:
        return f"Failed to get page text: {exc}"


def browser_get_title() -> str:
    """Get the title of the current page."""
    page = _safe_page()
    try:
        return f"Page title: {page.title()}"
    except Exception as exc:
        return f"Failed to get title: {exc}"


def browser_get_url() -> str:
    """Get the current URL of the browser."""
    page = _safe_page()
    try:
        return f"Current URL: {page.url}"
    except Exception as exc:
        return f"Failed to get URL: {exc}"


def browser_execute_js(script: str) -> str:
    """Execute JavaScript code in the browser page and return the result.

    Args:
        script: JavaScript code to execute (e.g. 'document.title' or 'return window.scrollY').
    """
    page = _safe_page()
    try:
        result = page.evaluate(script)
        return f"JS result: {result}"
    except Exception as exc:
        return f"JS execution failed: {exc}"


def browser_wait(selector_or_ms: str) -> str:
    """Wait for an element to appear or wait a duration.

    Args:
        selector_or_ms: A CSS/text selector to wait for, or a number like '2000' to wait 2 seconds.
    """
    page = _safe_page()
    if selector_or_ms.isdigit():
        ms = int(selector_or_ms)
        page.wait_for_timeout(ms)
        return f"Waited {ms}ms."
    try:
        page.wait_for_selector(selector_or_ms, timeout=15000)
        return f"Element '{selector_or_ms}' appeared."
    except Exception as exc:
        return f"Wait failed: {exc}"


def browser_screenshot() -> str:
    """Take a screenshot of the current browser page and save it.

    Returns:
        Path to the saved screenshot image.
    """
    page = _safe_page()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = config.TEMP_AUDIO_DIR / f"browser_ss_{timestamp}.png"
    try:
        page.screenshot(path=str(path), full_page=False)
        logger.info("Screenshot saved: %s", path)
        return f"Screenshot saved to {path}."
    except Exception as exc:
        return f"Screenshot failed: {exc}"


def browser_new_tab(url: str = "") -> str:
    """Open a new browser tab, optionally navigating to a URL.

    Args:
        url: URL to open in the new tab (optional).
    """
    global _PAGE
    page = _safe_page()
    try:
        context = _BROWSER_CONTEXT
        new_page = context.new_page()
        _PAGE = new_page
        if url:
            new_page.goto(url if url.startswith(("http://", "https://")) else f"https://{url}",
                          wait_until="domcontentloaded")
        return f"Opened new tab{' to ' + url if url else ''}."
    except Exception as exc:
        return f"Failed to open new tab: {exc}"


def browser_close_tab() -> str:
    """Close the current browser tab."""
    global _PAGE
    page = _safe_page()
    try:
        context = _BROWSER_CONTEXT
        pages = context.pages
        if len(pages) <= 1:
            return "Cannot close the only tab."
        page.close()
        _PAGE = context.pages[-1]
        return "Closed current tab."
    except Exception as exc:
        return f"Failed to close tab: {exc}"


def browser_switch_tab(index: int) -> str:
    """Switch to a specific browser tab by index.

    Args:
        index: Tab number (0 = first tab, 1 = second, etc.).
    """
    global _PAGE
    try:
        context = _BROWSER_CONTEXT
        pages = context.pages
        if index < 0 or index >= len(pages):
            return f"Invalid tab index {index}. Only {len(pages)} tabs open."
        _PAGE = pages[index]
        _PAGE.bring_to_front()
        return f"Switched to tab {index}: '{_PAGE.title()}'."
    except Exception as exc:
        return f"Failed to switch tab: {exc}"


def browser_list_tabs() -> str:
    """List all open browser tabs with their titles and URLs."""
    try:
        if _BROWSER_CONTEXT is None:
            return "No browser open."
        pages = _BROWSER_CONTEXT.pages
        if not pages:
            return "No tabs open."
        lines = []
        for i, p in enumerate(pages):
            try:
                lines.append(f"  [{i}] {p.title()} — {p.url[:80]}")
            except Exception:
                lines.append(f"  [{i}] (unavailable)")
        return "Browser tabs:\n" + "\n".join(lines)
    except Exception as exc:
        return f"Failed to list tabs: {exc}"


def browser_go_back() -> str:
    """Navigate back in browser history."""
    page = _safe_page()
    try:
        page.go_back(wait_until="domcontentloaded")
        return f"Went back to: {page.url}"
    except Exception as exc:
        return f"Failed to go back: {exc}"


def browser_go_forward() -> str:
    """Navigate forward in browser history."""
    page = _safe_page()
    try:
        page.go_forward(wait_until="domcontentloaded")
        return f"Went forward to: {page.url}"
    except Exception as exc:
        return f"Failed to go forward: {exc}"


def browser_refresh() -> str:
    """Refresh the current page."""
    page = _safe_page()
    try:
        page.reload(wait_until="domcontentloaded")
        return "Page refreshed."
    except Exception as exc:
        return f"Failed to refresh: {exc}"


def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """Scroll the page vertically or horizontally.

    Args:
        direction: 'down', 'up', 'left', or 'right'.
        amount: Pixels to scroll (default 500).
    """
    page = _safe_page()
    dx, dy = 0, 0
    if direction == "down":
        dy = amount
    elif direction == "up":
        dy = -amount
    elif direction == "right":
        dx = amount
    elif direction == "left":
        dx = -amount
    try:
        page.evaluate(f"window.scrollBy({dx}, {dy})")
        return f"Scrolled {direction} by {amount}px."
    except Exception as exc:
        return f"Scroll failed: {exc}"


def browser_close() -> str:
    """Close the browser and release all resources."""
    global _BROWSER, _BROWSER_CONTEXT, _PAGE, _PLAYWRIGHT
    try:
        if _BROWSER:
            _BROWSER.close()
        if _PLAYWRIGHT:
            _PLAYWRIGHT.stop()
    except Exception:
        pass
    _BROWSER = None
    _BROWSER_CONTEXT = None
    _PAGE = None
    _PLAYWRIGHT = None
    logger.info("Browser closed.")
    return "Browser closed."
