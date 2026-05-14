"""
Nexus Web Search — Open URLs and web searches in the default browser.
"""

import logging
import re
import webbrowser

logger = logging.getLogger("nexus.tools.web_search")

_URL_PATTERN = re.compile(
    r"^https?://"               # Must start with http:// or https://
    r"[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"  # Valid URL characters
    r"$"
)


def open_url(url: str) -> str:
    """
    Open a URL in the default web browser.

    Args:
        url: A fully-qualified URL starting with http:// or https://.

    Returns:
        Confirmation or error message.
    """
    url = url.strip()

    # Auto-prepend https if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not _URL_PATTERN.match(url):
        return f"Invalid URL format: {url}"

    try:
        webbrowser.open(url)
        logger.info("Opened URL: %s", url)
        return f"Opened {url} in your browser."
    except Exception as exc:
        logger.error("Failed to open URL %s: %s", url, exc)
        return f"Failed to open URL: {exc}"


def search_web(query: str) -> str:
    """
    Perform a web search by opening Google in the default browser.

    Args:
        query: The search query string.

    Returns:
        Confirmation message.
    """
    if not query or not query.strip():
        return "Empty search query."

    clean = query.strip()
    # URL-encode the query for safety
    from urllib.parse import quote_plus
    search_url = f"https://www.google.com/search?q={quote_plus(clean)}"

    try:
        webbrowser.open(search_url)
        logger.info("Web search: %s", clean)
        return f"Searching the web for: {clean}"
    except Exception as exc:
        logger.error("Web search failed: %s", exc)
        return f"Failed to open web search: {exc}"
