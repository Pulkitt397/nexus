import logging

logger = logging.getLogger("nexus.tools.registry")

_TOOL_REGISTRY = []

# Existing tools (always available)
from tools.app_manager import close_application, list_running_applications, open_application
from tools.brightness_control import change_brightness, get_brightness
from tools.file_ops import open_file, read_clipboard, search_files, write_clipboard
from tools.power_manager import system_power_action
from tools.system_info import get_current_time, get_ip_address, get_system_info
from tools.volume_control import change_volume, get_volume, toggle_mute
from tools.web_search import open_url, search_web

_TOOL_REGISTRY.extend([
    open_application, close_application, list_running_applications,
    change_volume, get_volume, toggle_mute,
    change_brightness, get_brightness,
    system_power_action,
    search_files, open_file, read_clipboard, write_clipboard,
    get_system_info, get_current_time, get_ip_address,
    open_url, search_web,
])

# Browser Control (Playwright)
try:
    from tools.browser_control import (
        browser_launch, browser_navigate, browser_click, browser_type,
        browser_type_text, browser_press_key, browser_get_text, browser_get_title,
        browser_get_url, browser_execute_js, browser_wait, browser_screenshot,
        browser_new_tab, browser_close_tab, browser_switch_tab, browser_list_tabs,
        browser_go_back, browser_go_forward, browser_refresh, browser_scroll,
        browser_close,
    )
    _TOOL_REGISTRY.extend([
        browser_launch, browser_navigate, browser_click, browser_type,
        browser_type_text, browser_press_key, browser_get_text, browser_get_title,
        browser_get_url, browser_execute_js, browser_wait, browser_screenshot,
        browser_new_tab, browser_close_tab, browser_switch_tab, browser_list_tabs,
        browser_go_back, browser_go_forward, browser_refresh, browser_scroll,
        browser_close,
    ])
    logger.info("Browser control tools loaded.")
except ImportError:
    logger.warning("Playwright not installed — browser control unavailable.")
except Exception as exc:
    logger.warning("Browser control failed to load: %s", exc)

# Mouse & Keyboard (PyAutoGUI)
try:
    from tools.mouse_keyboard import (
        mouse_move, mouse_click, mouse_double_click, mouse_right_click,
        mouse_drag, mouse_scroll, mouse_position,
        keyboard_type, keyboard_press, keyboard_hotkey,
        keyboard_hold, keyboard_release, keyboard_write_enter,
    )
    _TOOL_REGISTRY.extend([
        mouse_move, mouse_click, mouse_double_click, mouse_right_click,
        mouse_drag, mouse_scroll, mouse_position,
        keyboard_type, keyboard_press, keyboard_hotkey,
        keyboard_hold, keyboard_release, keyboard_write_enter,
    ])
    logger.info("Mouse & keyboard tools loaded.")
except ImportError:
    logger.warning("PyAutoGUI not installed — mouse/keyboard control unavailable.")
except Exception as exc:
    logger.warning("Mouse/keyboard failed to load: %s", exc)

# Screen Capture (mss + pytesseract)
try:
    from tools.screen_capture import (
        screen_capture, screen_capture_monitor, screen_capture_region,
        screen_get_text, screen_find_text, screen_get_color,
    )
    _TOOL_REGISTRY.extend([
        screen_capture, screen_capture_monitor, screen_capture_region,
        screen_get_text, screen_find_text, screen_get_color,
    ])
    logger.info("Screen capture tools loaded.")
except ImportError:
    logger.warning("mss not installed — screen capture unavailable.")
except Exception as exc:
    logger.warning("Screen capture failed to load: %s", exc)

# Media Control
try:
    from tools.media_control import media_play_pause, media_next, media_previous, media_stop
    _TOOL_REGISTRY.extend([media_play_pause, media_next, media_previous, media_stop])
    logger.info("Media control tools loaded.")
except Exception as exc:
    logger.warning("Media control failed to load: %s", exc)

# Window Manager (pywin32)
try:
    from tools.window_manager import (
        window_list, window_focus, window_minimize, window_maximize,
        window_restore, window_close, window_move, window_resize,
        window_get_info, window_get_active,
    )
    _TOOL_REGISTRY.extend([
        window_list, window_focus, window_minimize, window_maximize,
        window_restore, window_close, window_move, window_resize,
        window_get_info, window_get_active,
    ])
    logger.info("Window manager tools loaded.")
except ImportError:
    logger.warning("pywin32 not installed — window management unavailable.")
except Exception as exc:
    logger.warning("Window manager failed to load: %s", exc)

# File Manager (standard lib)
try:
    from tools.file_manager import (
        file_create, file_delete, file_delete_force, file_copy, file_move,
        file_rename, file_read, file_write, file_append, file_list,
        file_info, file_download,
    )
    _TOOL_REGISTRY.extend([
        file_create, file_delete, file_delete_force, file_copy, file_move,
        file_rename, file_read, file_write, file_append, file_list,
        file_info, file_download,
    ])
    logger.info("File manager tools loaded.")
except Exception as exc:
    logger.warning("File manager failed to load: %s", exc)

# Process Manager (psutil)
try:
    from tools.process_manager import (
        process_list, process_kill, process_force_kill,
        process_start, process_info, process_wait,
    )
    _TOOL_REGISTRY.extend([
        process_list, process_kill, process_force_kill,
        process_start, process_info, process_wait,
    ])
    logger.info("Process manager tools loaded.")
except Exception as exc:
    logger.warning("Process manager failed to load: %s", exc)

# System Tools
try:
    from tools.system_tools import (
        system_get_resolution, system_set_resolution, system_set_wallpaper,
        system_send_notification, system_get_network_info,
        system_wifi_connect, system_wifi_disconnect,
        system_list_drives, system_eject_drive, system_empty_recycle_bin,
        system_get_uptime, system_open_folder, system_open_with,
        system_get_env, system_list_env,
    )
    _TOOL_REGISTRY.extend([
        system_get_resolution, system_set_resolution, system_set_wallpaper,
        system_send_notification, system_get_network_info,
        system_wifi_connect, system_wifi_disconnect,
        system_list_drives, system_eject_drive, system_empty_recycle_bin,
        system_get_uptime, system_open_folder, system_open_with,
        system_get_env, system_list_env,
    ])
    logger.info("System tools loaded.")
except Exception as exc:
    logger.warning("System tools failed to load: %s", exc)

TOOL_REGISTRY = _TOOL_REGISTRY

logger.info("Tool registry ready: %d tools registered.", len(TOOL_REGISTRY))
