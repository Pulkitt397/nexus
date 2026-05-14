"""
Nexus File & Clipboard Operations — Search files, open them, and manage clipboard content.

Security:
    - Path traversal attacks are blocked (no '..' components).
    - Access to critical system directories is denied.
    - Glob patterns are validated before execution.
"""

import logging
import os
import re
from pathlib import Path

import pyperclip

logger = logging.getLogger("nexus.tools.file_ops")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
_BLOCKED_ROOTS = {
    Path("C:/Windows"),
    Path("C:/Windows/System32"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData"),
}

_DANGEROUS_PATTERN = re.compile(r"\.\.")


def _validate_path(raw: str) -> Path:
    """
    Validate and resolve a file path, blocking traversal attacks and system directories.

    Raises ValueError on violations.
    """
    if _DANGEROUS_PATTERN.search(raw):
        raise ValueError("Path traversal ('..') is not allowed.")

    resolved = Path(raw).resolve()

    for blocked in _BLOCKED_ROOTS:
        try:
            resolved.relative_to(blocked.resolve())
            raise ValueError(f"Access to {blocked} is restricted for safety.")
        except ValueError as exc:
            if "restricted" in str(exc):
                raise
            continue  # Not under this blocked root — fine

    return resolved


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def search_files(query: str, directory: str = "") -> str:
    """
    Search for files matching a name pattern within a directory.

    Args:
        query: A filename pattern (e.g. '*.pdf', 'report*', 'budget.xlsx').
        directory: The directory to search in. Defaults to the user's home folder.

    Returns:
        A list of matching file paths or a message if none found.
    """
    if not directory:
        directory = str(Path.home())

    try:
        base = _validate_path(directory)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not base.is_dir():
        return f"'{directory}' is not a valid directory."

    # Sanitize the glob query
    clean_query = query.strip().replace("/", "").replace("\\", "")
    if not clean_query:
        return "Empty search query."

    try:
        matches = list(base.rglob(clean_query))[:50]  # Cap at 50 results
    except Exception as exc:
        return f"Search error: {exc}"

    if not matches:
        return f"No files matching '{clean_query}' found in {base}."

    lines = [f"  • {m}" for m in matches[:25]]
    header = f"Found {len(matches)} file(s) matching '{clean_query}':"
    if len(matches) > 25:
        lines.append(f"  … and {len(matches) - 25} more.")
    return header + "\n" + "\n".join(lines)


def open_file(filepath: str) -> str:
    """
    Open a file with its default Windows application.

    Args:
        filepath: The full path to the file to open.

    Returns:
        Confirmation or error message.
    """
    try:
        target = _validate_path(filepath)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not target.exists():
        return f"File not found: {filepath}"

    try:
        os.startfile(str(target))
        logger.info("Opened file: %s", target)
        return f"Opened {target.name}."
    except OSError as exc:
        logger.error("Failed to open file %s: %s", target, exc)
        return f"Failed to open {target.name}: {exc}"


def read_clipboard() -> str:
    """
    Read the current text content from the Windows clipboard.

    Returns:
        The clipboard text, or an error message.
    """
    try:
        content = pyperclip.paste()
        if not content:
            return "Clipboard is empty."
        # Truncate for safety
        if len(content) > 2000:
            return f"Clipboard content (truncated):\n{content[:2000]}…"
        return f"Clipboard content:\n{content}"
    except Exception as exc:
        logger.error("Failed to read clipboard: %s", exc)
        return f"Failed to read clipboard: {exc}"


def write_clipboard(text: str) -> str:
    """
    Write text to the Windows clipboard.

    Args:
        text: The text string to copy to clipboard.

    Returns:
        Confirmation message.
    """
    if not text:
        return "Nothing to copy — empty text."

    try:
        pyperclip.copy(text)
        preview = text[:80] + "…" if len(text) > 80 else text
        logger.info("Wrote to clipboard: %s", preview)
        return f"Copied to clipboard: {preview}"
    except Exception as exc:
        logger.error("Failed to write clipboard: %s", exc)
        return f"Failed to write to clipboard: {exc}"
