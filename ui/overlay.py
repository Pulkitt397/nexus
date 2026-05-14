"""
Nexus Transparent Overlay — Always-on-top floating card resembling Gemini Live.

Shows the assistant's status, transcriptions, and responses in a sleek
semi-transparent card that appears when the AI is active and stays out of the way.
"""

import logging
import queue
import threading
import tkinter as tk
from typing import Optional

logger = logging.getLogger("nexus.ui.overlay")

# ── Colour palette ───────────────────────────────────────────────────────────
_BG = "#0f0f1a"
_FG = "#e8e8f0"
_FG_DIM = "#808090"
_ACCENT_IDLE = "#4ade80"
_ACCENT_LISTEN = "#fbbf24"
_ACCENT_THINK = "#60a5fa"
_ACCENT_SPEAK = "#22d3ee"
_ACCENT_ERROR = "#f87171"

_WINDOW_WIDTH = 440
_WINDOW_HEIGHT = 48  # compact when idle; expands to ~130
_EXPANDED_HEIGHT = 130
_MARGIN = 20


class NexusOverlay:
    """
    A transparent, always-on-top overlay card displayed on screen.

    Usage
    -----
    overlay = NexusOverlay()
    overlay.start()           # launches the tkinter thread
    overlay.set_state("listening", "open browser")
    overlay.set_state("speaking", "I've opened the browser")
    overlay.stop()
    """

    def __init__(self):
        self._cmd_queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._expanded = False

        # Widget references (filled by _build_ui)
        self._frame = None
        self._dot = None
        self._status_label = None
        self._sep = None
        self._text_label = None

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the overlay in a daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="nexus-overlay")
        self._thread.start()
        logger.info("Overlay thread started.")

    def stop(self) -> None:
        """Signal the overlay to close."""
        self._cmd_queue.put(("__exit__", ""))
        logger.info("Overlay stop signalled.")

    def set_state(self, state: str, text: str = "") -> None:
        """Push a state update to the overlay.

        Parameters
        ----------
        state : str
            One of 'idle', 'listening', 'transcribing', 'processing', 'speaking',
            'error', or 'hidden'.
        text : str
            Optional transcription / response text to display.
        """
        self._cmd_queue.put((state, text))

    # ── Internal: tkinter event loop ────────────────────────────────────────

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("nexus-overlay")
        self._root.overrideredirect(True)           # no title bar
        self._root.attributes("-topmost", True)      # always on top
        self._root.attributes("-alpha", 0.92)        # semi-transparent
        self._root.configure(bg=_BG)
        self._root.resizable(False, False)

        # Make window click-through (mouse events pass to desktop)
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "nexus-overlay")
            if hwnd:
                WS_EX_LAYERED = 0x80000
                WS_EX_TRANSPARENT = 0x20
                WS_EX_TOOLWINDOW = 0x80
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, -20, WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW,
                )
        except Exception:
            pass

        # DPI awareness
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        self._position_window(compact=True)
        self._build_ui()
        self._set_state_internal("idle", "")

        # Poll command queue every 100 ms
        self._poll_queue()
        self._root.mainloop()

    def _position_window(self, compact: bool = True) -> None:
        if not self._root:
            return
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        w = _WINDOW_WIDTH
        h = _WINDOW_HEIGHT if compact else _EXPANDED_HEIGHT
        x = screen_w - w - _MARGIN
        y = screen_h - h - _MARGIN - 40  # above taskbar
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._expanded = not compact

        # Rounded corners via Win32 region
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "nexus-overlay")
            if hwnd:
                rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, 16, 16)
                ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

    def _build_ui(self) -> None:
        self._frame = tk.Frame(self._root, bg=_BG, highlightthickness=0)
        self._frame.pack(fill="both", expand=True, padx=16, pady=8)

        # ── Top row: dot + status ─────────────────────────────────────────
        top = tk.Frame(self._frame, bg=_BG)
        top.pack(fill="x", anchor="w")

        self._dot = tk.Label(top, text="●", font=("Segoe UI", 14), fg=_ACCENT_IDLE, bg=_BG)
        self._dot.pack(side="left")

        self._status_label = tk.Label(
            top, text="Nexus Ready", font=("Segoe UI", 12, "bold"),
            fg=_FG, bg=_BG,
        )
        self._status_label.pack(side="left", padx=(8, 0))

        # ── Separator ─────────────────────────────────────────────────────
        self._sep = tk.Frame(self._frame, height=1, bg="#2a2a3e")

        # ── Text area ─────────────────────────────────────────────────────
        self._text_label = tk.Label(
            self._frame, text="",
            font=("Segoe UI", 10), fg=_FG_DIM, bg=_BG,
            wraplength=_WINDOW_WIDTH - 40, justify="left", anchor="w",
        )

        # Initially collapsed — hide extra elements

    # ── Internal state machine ──────────────────────────────────────────────

    def _set_state_internal(self, state: str, text: str) -> None:
        if state == "hidden":
            if self._root:
                self._root.withdraw()
            return

        if self._root:
            self._root.deiconify()

        expanded = state != "idle"

        # Update compact ⇄ expanded layout
        if expanded != self._expanded:
            if expanded:
                if self._sep:
                    self._sep.pack(fill="x", pady=(6, 4))
                if self._text_label:
                    self._text_label.pack(fill="x")
            else:
                if self._sep:
                    self._sep.pack_forget()
                if self._text_label:
                    self._text_label.pack_forget()

            self._position_window(compact=not expanded)

        # Colour & text
        dot_colour = _ACCENT_IDLE
        status_text = "Nexus Ready"

        if state == "listening":
            dot_colour = _ACCENT_LISTEN
            status_text = "Listening..."
        elif state == "transcribing":
            dot_colour = _ACCENT_LISTEN
            status_text = "Transcribing..."
        elif state == "processing":
            dot_colour = _ACCENT_THINK
            status_text = "Thinking..."
        elif state == "speaking":
            dot_colour = _ACCENT_SPEAK
            status_text = "Speaking..."
        elif state == "error":
            dot_colour = _ACCENT_ERROR
            status_text = "Error"

        self._dot.config(fg=dot_colour)
        self._status_label.config(text=status_text)
        self._text_label.config(text=text)

    def _poll_queue(self) -> None:
        if not self._root:
            return
        try:
            while True:
                state, text = self._cmd_queue.get_nowait()
                if state == "__exit__":
                    self._root.quit()
                    self._root.destroy()
                    return
                self._set_state_internal(state, text)
        except queue.Empty:
            pass
        finally:
            try:
                self._root.after(100, self._poll_queue)
            except tk.TclError:
                pass
