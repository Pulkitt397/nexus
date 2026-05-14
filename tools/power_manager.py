"""
Nexus Power Manager — Secure system power state control for Windows 11.

Only four actions are permitted: lock, sleep, restart, shutdown.
All actions use well-known Windows executables with strict argument validation.
"""

import logging
import subprocess
import ctypes

logger = logging.getLogger("nexus.tools.power")

# ---------------------------------------------------------------------------
# Strict allowlist — no other strings are accepted
# ---------------------------------------------------------------------------
_POWER_ACTIONS: dict[str, dict] = {
    "lock": {
        "description": "Lock the workstation",
        "method": "dll",
    },
    "sleep": {
        "description": "Put the PC to sleep",
        "command": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
    },
    "restart": {
        "description": "Restart the PC in 5 seconds",
        "command": ["shutdown.exe", "/r", "/t", "5"],
    },
    "shutdown": {
        "description": "Shut down the PC in 5 seconds",
        "command": ["shutdown.exe", "/s", "/t", "5"],
    },
}


def system_power_action(action: str) -> str:
    """
    Execute a system power action.

    Args:
        action: One of 'lock', 'sleep', 'restart', or 'shutdown'.

    Returns:
        Confirmation or error message.
    """
    clean = action.strip().lower()

    if clean not in _POWER_ACTIONS:
        allowed = ", ".join(sorted(_POWER_ACTIONS.keys()))
        return f"Invalid power action '{action}'. Allowed: {allowed}."

    entry = _POWER_ACTIONS[clean]

    try:
        if clean == "lock":
            # Use ctypes to call LockWorkStation directly — no shell involved
            result = ctypes.windll.user32.LockWorkStation()
            if result:
                logger.info("Workstation locked.")
                return "Workstation locked."
            else:
                return "Failed to lock the workstation — may require a logged-in desktop session."

        command = entry["command"]
        logger.info("Executing power action: %s → %s", clean, command)
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=10,
        )
        return f"{entry['description']} — command issued successfully."

    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip() if exc.stderr else "unknown error"
        logger.error("Power action '%s' failed: %s", clean, stderr)
        return f"Power action '{clean}' failed: {stderr}"
    except subprocess.TimeoutExpired:
        return f"Power action '{clean}' timed out."
    except Exception as exc:
        logger.error("Unexpected error in power action '%s': %s", clean, exc)
        return f"Power action '{clean}' error: {exc}"
