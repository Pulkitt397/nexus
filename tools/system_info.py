"""
Nexus System Info — Read-only system telemetry via psutil.
"""

import logging
import platform
import socket
from datetime import datetime

import psutil

logger = logging.getLogger("nexus.tools.system_info")


def get_system_info() -> str:
    """
    Get a comprehensive snapshot of the current system status.

    Returns:
        A formatted string with CPU, RAM, disk, battery, and OS info.
    """
    try:
        cpu_pct = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        battery = psutil.sensors_battery()

        lines = [
            f"  CPU Usage:    {cpu_pct}%",
            f"  RAM:          {mem.percent}% used ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)",
            f"  Disk (C:):    {disk.percent}% used ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)",
        ]

        if battery:
            plug = "plugged in" if battery.power_plugged else "on battery"
            lines.append(f"  Battery:      {battery.percent}% ({plug})")
        else:
            lines.append("  Battery:      N/A (desktop)")

        lines.append(f"  OS:           {platform.system()} {platform.release()} ({platform.version()})")
        lines.append(f"  Machine:      {platform.machine()}")

        return "System Status:\n" + "\n".join(lines)

    except Exception as exc:
        logger.error("Failed to get system info: %s", exc)
        return f"Failed to retrieve system info: {exc}"


def get_current_time() -> str:
    """
    Get the current local date and time.

    Returns:
        A formatted datetime string.
    """
    now = datetime.now()
    return now.strftime("It's %A, %B %d, %Y at %I:%M %p.")


def get_ip_address() -> str:
    """
    Get the local IP address of this machine.

    Returns:
        The local IP address string.
    """
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return f"Hostname: {hostname}, Local IP: {ip}"
    except Exception as exc:
        logger.error("Failed to get IP: %s", exc)
        return f"Failed to retrieve IP address: {exc}"
