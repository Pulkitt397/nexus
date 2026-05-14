import logging
import subprocess
import sys

logger = logging.getLogger("nexus.tools.system")


def system_get_resolution() -> str:
    """Get the current screen resolution."""
    try:
        import pyautogui
        w, h = pyautogui.size()
        return f"Screen resolution: {w}x{h}."
    except Exception as exc:
        return f"Failed to get resolution: {exc}"


def system_set_resolution(width: int, height: int) -> str:
    """Change the screen resolution.

    Args:
        width: Horizontal resolution (e.g. 1920).
        height: Vertical resolution (e.g. 1080).
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        DM_PELSWIDTH = 0x80000
        DM_PELSHEIGHT = 0x100000
        CDS_UPDATEREGISTRY = 0x01

        class DEVMODE(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort),
                ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_ulong),
                ("dmOrientation", ctypes.c_short),
                ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short),
                ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short),
                ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short),
                ("dmPrintQuality", ctypes.c_short),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort),
                ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong),
                ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong),
                ("dmDisplayFrequency", ctypes.c_ulong),
            ]

        dm = DEVMODE()
        dm.dmSize = ctypes.sizeof(DEVMODE)
        dm.dmPelsWidth = width
        dm.dmPelsHeight = height
        dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT

        result = user32.ChangeDisplaySettingsW(ctypes.byref(dm), CDS_UPDATEREGISTRY)
        if result == 0:
            return f"Resolution changed to {width}x{height}."
        return f"Failed to change resolution (code {result})."
    except Exception as exc:
        return f"Failed to set resolution: {exc}"


def system_set_wallpaper(image_path: str) -> str:
    """Set the desktop wallpaper to an image file.

    Args:
        image_path: Full path to the image file (.jpg, .png, .bmp).
    """
    try:
        import ctypes
        from pathlib import Path
        target = Path(image_path).resolve()
        if not target.exists():
            return f"Image not found: {image_path}"
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(target), 0)
        if result:
            return f"Wallpaper set to: {target.name}."
        return "Failed to set wallpaper."
    except Exception as exc:
        return f"Failed to set wallpaper: {exc}"


def system_send_notification(title: str, message: str) -> str:
    """Send a Windows toast notification.

    Args:
        title: Notification title.
        message: Notification body text.
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Nexus",
            timeout=5,
        )
        logger.info("Notification sent: %s", title)
        return f"Notification sent: {title}."
    except ImportError:
        pass

    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0)
        return f"Notification shown: {title}."
    except Exception as exc:
        try:
            subprocess.run(
                ["powershell", "-Command",
                 f'New-BurntToastNotification -Text "{title}", "{message}"'],
                capture_output=True, timeout=10,
            )
            return f"Notification sent: {title}."
        except Exception:
            return f"Failed to show notification: {exc}"


def system_get_network_info() -> str:
    """Get network information including SSID, IP, and connection status."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10,
        )
        ssid = "Unknown"
        for line in result.stdout.splitlines():
            if "SSID" in line and "BSSID" not in line:
                parts = line.split(":")
                if len(parts) > 1:
                    ssid = parts[1].strip()
                    break

        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        return f"Network: Connected to '{ssid}', IP: {ip}, Hostname: {hostname}."
    except Exception as exc:
        return f"Failed to get network info: {exc}"


def system_wifi_connect(ssid: str, password: str = "") -> str:
    """Connect to a WiFi network.

    Args:
        ssid: The WiFi network name (SSID).
        password: The network password (empty for open networks).
    """
    try:
        if password:
            profile = (
                f'<?xml version="1.0"?>'
                f'<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">'
                f"<name>{ssid}</name>"
                f"<SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>"
                f"<connectionType>ESS</connectionType>"
                f"<connectionMode>auto</connectionMode>"
                f"<MSM><security><authEncryption>"
                f"<authentication>WPA2PSK</authentication>"
                f"<encryption>AES</encryption>"
                f"</authEncryption><sharedKey>"
                f"<keyType>passPhrase</keyType>"
                f"<protected>false</protected>"
                f"<keyMaterial>{password}</keyMaterial>"
                f"</sharedKey></security></MSM>"
                f"</WLANProfile>"
            )
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
                f.write(profile)
                xml_path = f.name
            subprocess.run(["netsh", "wlan", "add", "profile", f"filename={xml_path}"],
                           capture_output=True, timeout=10)
            import os as _os
            _os.unlink(xml_path)

        result = subprocess.run(
            ["netsh", "wlan", "connect", f"name={ssid}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return f"Connected to WiFi: {ssid}."
        return f"Failed to connect: {result.stderr.strip()}"
    except Exception as exc:
        return f"Failed to connect to WiFi: {exc}"


def system_wifi_disconnect() -> str:
    """Disconnect from the current WiFi network."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "disconnect"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return "Disconnected from WiFi."
        return f"Failed to disconnect: {result.stderr.strip()}"
    except Exception as exc:
        return f"Failed to disconnect: {exc}"


def system_list_drives() -> str:
    """List all available drives on the system."""
    try:
        import string
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:\\"
                import ctypes
                drive_type = windll.kernel32.GetDriveTypeW(drive)
                types = {
                    2: "Removable",
                    3: "Fixed",
                    4: "Network",
                    5: "CD/DVD",
                    6: "RAM Disk",
                }
                drives.append(f"  {drive} ({types.get(drive_type, 'Unknown')})")
            bitmask >>= 1
        return "Drives:\n" + "\n".join(drives)
    except Exception as exc:
        return f"Failed to list drives: {exc}"


def system_eject_drive(drive_letter: str) -> str:
    """Safely eject a removable drive.

    Args:
        drive_letter: Drive letter (e.g. 'D', 'E:', 'D:\\').
    """
    try:
        letter = drive_letter.strip().upper().rstrip(":\\")
        result = subprocess.run(
            ["powershell", "-Command",
             f"$drive = Get-WmiObject -Class Win32_Volume | Where-Object {{ $_.DriveLetter -eq '{letter}:' }}; "
             f"if ($drive) {{ $drive.Dismount($false) }}"],
            capture_output=True, text=True, timeout=30,
        )
        logger.info("Ejecting drive %s:", letter, result.stdout)
        return f"Ejected drive {letter}."
    except Exception as exc:
        return f"Failed to eject drive: {exc}"


def system_empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "(New-Object -ComObject Shell.Application).NameSpace(0xa).Items() | "
             "ForEach-Object { $_.InvokeVerb('delete') }"],
            capture_output=True, text=True, timeout=30,
        )
        return "Recycle bin emptied."
    except Exception as exc:
        return f"Failed to empty recycle bin: {exc}"


def system_get_uptime() -> str:
    """Get the system uptime."""
    try:
        import psutil
        import datetime
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        now = datetime.datetime.now()
        uptime = now - boot_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"System uptime: {days}d {hours}h {minutes}m (since {boot_time.strftime('%Y-%m-%d %H:%M:%S')})."
    except Exception as exc:
        return f"Failed to get uptime: {exc}"


def system_open_folder(path: str) -> str:
    """Open a folder in Windows File Explorer.

    Args:
        path: Full path to the folder to open.
    """
    try:
        subprocess.Popen(["explorer", path])
        return f"Opened folder: {path}."
    except Exception as exc:
        return f"Failed to open folder: {exc}"


def system_open_with(path: str, app_name: str = "") -> str:
    """Open a file with a specific application.

    Args:
        path: Path to the file.
        app_name: Application to open with (e.g. 'notepad', 'chrome'). Defaults to system default.
    """
    try:
        if app_name:
            subprocess.Popen(["cmd", "/c", "start", "", app_name, path],
                             shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import os as _os
            _os.startfile(path)
        return f"Opened {path} with {app_name or 'default app'}."
    except Exception as exc:
        return f"Failed to open with: {exc}"


def system_get_env(key: str) -> str:
    """Get the value of an environment variable.

    Args:
        key: Environment variable name (e.g. 'PATH', 'USERNAME').
    """
    try:
        import os
        value = os.environ.get(key, "")
        if not value:
            return f"Environment variable '{key}' is not set."
        if len(value) > 500:
            value = value[:500] + "..."
        return f"{key} = {value}"
    except Exception as exc:
        return f"Failed to get env: {exc}"


def system_list_env(prefix: str = "") -> str:
    """List environment variables, optionally filtered by prefix.

    Args:
        prefix: Optional filter (e.g. 'PATH', 'USER').
    """
    try:
        import os
        items = []
        for key, value in sorted(os.environ.items()):
            if prefix and prefix.upper() not in key.upper():
                continue
            disp = value[:80] + "..." if len(value) > 80 else value
            items.append(f"  {key}={disp}")
        if not items:
            return f"No env vars matching '{prefix}'."
        return f"Environment variables (filter: '{prefix}'):\n" + "\n".join(items[:30])
    except Exception as exc:
        return f"Failed to list env: {exc}"
