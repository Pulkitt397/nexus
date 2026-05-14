"""
Nexus Episode Log — Persistent local conversation memory stored as JSONL.

Each episode captures: timestamp, user input, assistant response, tools invoked.
This provides long-term context for the Nexus system prompt without any cloud storage.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger("nexus.memory")

_LOG_FILE: Path = config.LOG_DIR / "episodes.jsonl"


def _ensure_log_file() -> None:
    """Create the log file if it doesn't exist."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _LOG_FILE.exists():
        _LOG_FILE.touch()


def log_episode(
    user_input: str,
    assistant_response: str,
    tools_used: list[str] | None = None,
) -> None:
    """
    Append a single conversation episode to the local log.

    Args:
        user_input: What the user said or typed.
        assistant_response: What Nexus responded.
        tools_used: List of tool function names that were invoked.
    """
    _ensure_log_file()

    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user_input,
        "assistant": assistant_response,
        "tools": tools_used or [],
    }

    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.debug("Episode logged.")
    except Exception as exc:
        logger.error("Failed to log episode: %s", exc)


def get_recent_episodes(n: int = 5) -> list[dict[str, Any]]:
    """
    Retrieve the last *n* episodes from the log.

    Args:
        n: Number of recent episodes to return.

    Returns:
        A list of episode dicts, most recent last.
    """
    _ensure_log_file()

    episodes: list[dict[str, Any]] = []
    try:
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        episodes.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as exc:
        logger.error("Failed to read episodes: %s", exc)
        return []

    return episodes[-n:]


def search_episodes(query: str) -> list[dict[str, Any]]:
    """
    Simple keyword search over all logged episodes.

    Args:
        query: The search term to look for in user inputs and assistant responses.

    Returns:
        A list of matching episodes (capped at 20).
    """
    _ensure_log_file()
    query_lower = query.lower()
    matches: list[dict[str, Any]] = []

    try:
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    episode = json.loads(line)
                except json.JSONDecodeError:
                    continue

                user_text = episode.get("user", "").lower()
                assistant_text = episode.get("assistant", "").lower()

                if query_lower in user_text or query_lower in assistant_text:
                    matches.append(episode)
                    if len(matches) >= 20:
                        break
    except Exception as exc:
        logger.error("Failed to search episodes: %s", exc)

    return matches


def get_context_summary(n: int = 3) -> str:
    """
    Build a brief context string from recent episodes for injection into the system prompt.

    Args:
        n: Number of recent episodes to summarize.

    Returns:
        A formatted string summarizing recent interactions.
    """
    recent = get_recent_episodes(n)
    if not recent:
        return ""

    lines = ["Recent conversation context:"]
    for ep in recent:
        ts = ep.get("timestamp", "?")[:19]
        user = ep.get("user", "")[:100]
        lines.append(f"  [{ts}] User: {user}")

    return "\n".join(lines)
