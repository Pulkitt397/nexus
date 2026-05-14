"""
Nexus Application Manager — Launch, close, and list Windows applications.
"""

import logging
import re
import subprocess
import sys
from typing import Optional

import psutil

logger = logging.getLogger("nexus.tools.app_manager")

# ---------------------------------------------------------------------------
# Safe application registry — maps friendly names to executables
# ---------------------------------------------------------------------------
_APP_MAP: dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "browser": "start msedge",
    "edge": "msedge.exe",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "snipping tool": "snippingtool.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "vscode": "code.exe",
    "code": "code.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "slack": "slack.exe",
    "obs": "obs64.exe",
    "vlc": "vlc.exe",
    "steam": "steam.exe",
}

# Characters that must NEVER appear in app names passed to shell
_SHELL_METACHAR = re.compile(r"[;&|`$><\\\n\r]")


def _sanitize(value: str) -> str:
    """Strip dangerous shell metacharacters from user input."""
    if _SHELL_METACHAR.search(value):
        raise ValueError(f"Input contains forbidden characters: {value!r}")
    return value.strip().lower()


# ---------------------------------------------------------------------------
# Tool functions (Gemini will call these directly)
# ---------------------------------------------------------------------------

def open_application(app_name: str) -> str:
    """
    Open a Windows application by its common name.

    Args:
        app_name: A human-friendly name like 'notepad', 'calculator', 'browser', 'terminal', 'vscode'.

    Returns:
        A status message confirming the app was launched or describing the error.
    """
    try:
        clean_name = _sanitize(app_name)
    except ValueError as exc:
        return f"Rejected: {exc}"

    executable = _APP_MAP.get(clean_name)
    if executable is None:
        # Try launching the raw name as a last resort (still sanitized)
        executable = clean_name

    try:
        if executable.startswith("ms-settings"):
            subprocess.Popen(
                ["start", executable],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif executable.startswith("start "):
            subprocess.Popen(
                executable,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            subprocess.Popen(
                [executable],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
        logger.info("Launched: %s → %s", clean_name, executable)
        return f"Opened {clean_name} successfully."
    except FileNotFoundError:
        return f"Could not find executable for '{clean_name}'. It may not be installed."
    except OSError as exc:
        return f"Failed to open {clean_name}: {exc}"


def close_application(app_name: str) -> str:
    """
    Close / kill all processes matching the given application name.

    Args:
        app_name: A human-friendly name like 'notepad', 'chrome', 'spotify'.

    Returns:
        A status message confirming how many processes were terminated.
    """
    try:
        clean_name = _sanitize(app_name)
    except ValueError as exc:
        return f"Rejected: {exc}"

    target_exe = _APP_MAP.get(clean_name, f"{clean_name}.exe")
    killed = 0

    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info["name"] or "").lower()
                if pname == target_exe.lower() or pname.startswith(clean_name):
                    proc.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as exc:
        return f"Error while closing {clean_name}: {exc}"

    if killed == 0:
        return f"No running processes found for '{clean_name}'."
    return f"Terminated {killed} process(es) for '{clean_name}'."


def list_running_applications() -> str:
    """
    List the top running applications on this PC (excludes system services).

    Returns:
        A formatted string listing process names and their memory usage.
    """
    try:
        procs: list[tuple[str, float]] = []
        seen: set[str] = set()

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                name = proc.info["name"] or "unknown"
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                mem_mb = (proc.info["memory_info"].rss / (1024 * 1024)) if proc.info["memory_info"] else 0.0
                if mem_mb > 5:  # Skip tiny background services
                    procs.append((name, mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x[1], reverse=True)
        top = procs[:20]

        lines = [f"  • {name} — {mem:.0f} MB" for name, mem in top]
        return "Top running applications:\n" + "\n".join(lines)

    except Exception as exc:
        return f"Failed to list applications: {exc}"
