"""
Nexus Orb Overlay — Transparent floating card with animated orb + mic button.

Appears at top-center of screen. Shows a live orb animation that changes
with Nexus state: idle → listening → processing → speaking.
Includes a clickable mic button and hotkey support.
"""

import logging
import math
import queue
import threading
import tkinter as tk
from typing import Optional

import config

logger = logging.getLogger("nexus.ui.overlay")

# ── Palette ──────────────────────────────────────────────────────────────────
_BG = "#0a0a14"
_FG = "#e8e8f0"
_FG_DIM = "#808098"
_FG_STATUS = "#606080"

_ORB_COLORS = {
    "idle":      {"a": "#4ade80", "b": "#86efac", "c": "#166534", "r": 22},
    "listening": {"a": "#60a5fa", "b": "#93c5fd", "c": "#1e3a5f", "r": 28},
    "processing": {"a": "#a78bfa", "b": "#c4b5fd", "c": "#3b0764", "r": 26},
    "speaking":  {"a": "#22d3ee", "b": "#67e8f9", "c": "#083344", "r": 28},
    "error":     {"a": "#f87171", "b": "#fca5a5", "c": "#450a0a", "r": 24},
}

_CARD_W = 380
_CARD_H_IDLE = 180
_CARD_H_ACTIVE = 260


class NexusOverlay:
    """
    Floating transparent card at top-center of screen with animated orb.

    States: idle | listening | transcribing | processing | speaking | error | hidden
    """

    def __init__(self, mic_callback=None, stop_callback=None):
        self._cmd_queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._mic_callback: callable = mic_callback or (lambda: None)
        self._stop_callback: callable = stop_callback or (lambda: None)
        self._state = "idle"
        self._text = ""
        self._anim_phase = 0
        self._expanded = False

        # Widgets
        self._frame = None
        self._orb_canvas: Optional[tk.Canvas] = None
        self._status_label: Optional[tk.Label] = None
        self._text_label: Optional[tk.Label] = None
        self._mic_btn: Optional[tk.Label] = None
        self._stop_btn: Optional[tk.Label] = None
        self._bottom_frame: Optional[tk.Frame] = None

    def set_mic_callback(self, cb: callable) -> None:
        self._mic_callback = cb

    def set_stop_callback(self, cb: callable) -> None:
        self._stop_callback = cb

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="nexus-overlay")
        self._thread.start()
        logger.info("Orb overlay started.")

    def stop(self) -> None:
        self._cmd_queue.put(("__exit__", ""))
        logger.info("Orb overlay stopped.")

    def set_state(self, state: str, text: str = "") -> None:
        self._cmd_queue.put((state, text))

    # ── Internal: tkinter loop ───────────────────────────────────────────────

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("nexus-overlay")
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.82)
        self._root.configure(bg=_BG)
        self._root.resizable(False, False)

        # Click-through
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "nexus-overlay")
            if hwnd:
                WS_EX_LAYERED = 0x80000
                WS_EX_TRANSPARENT = 0x20
                WS_EX_TOOLWINDOW = 0x80
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, -20, WS_EX_LAYERED | WS_EX_TOOLWINDOW
                )
        except Exception:
            pass

        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        self._position_window(compact=True)
        self._build_ui()
        self._set_state_internal("idle", "")
        self._animate()
        self._poll_queue()
        self._root.mainloop()

    def _position_window(self, compact: bool = True) -> None:
        if not self._root:
            return
        screen_w = self._root.winfo_screenwidth()
        h = _CARD_H_IDLE if compact else _CARD_H_ACTIVE
        x = (screen_w - _CARD_W) // 2
        y = 16
        self._root.geometry(f"{_CARD_W}x{h}+{x}+{y}")
        self._expanded = not compact

        # Rounded corners
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "nexus-overlay")
            if hwnd:
                rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, _CARD_W + 1, h + 1, 18, 18)
                ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._frame = tk.Frame(self._root, bg=_BG, highlightthickness=0)
        self._frame.pack(fill="both", expand=True)

        # ── Orb canvas ───────────────────────────────────────────────────────
        self._orb_canvas = tk.Canvas(
            self._frame, width=100, height=100,
            bg=_BG, highlightthickness=0,
        )
        self._orb_canvas.pack(pady=(12, 2))

        # ── Status text ──────────────────────────────────────────────────────
        self._status_label = tk.Label(
            self._frame, text="Nexus Ready",
            font=("Segoe UI", 13, "bold"), fg=_FG, bg=_BG,
        )
        self._status_label.pack()

        # ── Detail text ──────────────────────────────────────────────────────
        self._text_label = tk.Label(
            self._frame, text="",
            font=("Segoe UI", 9), fg=_FG_DIM, bg=_BG,
            wraplength=_CARD_W - 48, justify="center",
        )

        # ── Bottom row: mic + stop + gear ────────────────────────────────────
        self._bottom_frame = tk.Frame(self._frame, bg=_BG)
        self._bottom_frame.pack(side="bottom", pady=(0, 12))

        self._mic_btn = tk.Label(
            self._bottom_frame, text="🎤", font=("Segoe UI", 22),
            fg=_FG, bg="#1a1a2e", cursor="hand2",
            relief="flat", padx=10, pady=4,
        )
        self._mic_btn.pack(side="left", padx=6)
        self._mic_btn.bind("<Button-1>", lambda e: self._on_mic_click())
        self._mic_btn.bind("<Enter>", lambda e: self._mic_btn.configure(bg="#2a2a3e"))
        self._mic_btn.bind("<Leave>", lambda e: self._mic_btn.configure(bg="#1a1a2e"))

        self._stop_btn = tk.Label(
            self._bottom_frame, text="⏹", font=("Segoe UI", 16, "bold"),
            fg="#f87171", bg="#2a1a1a", cursor="hand2",
            relief="flat", padx=12, pady=4,
        )
        self._stop_btn.bind("<Button-1>", lambda e: self._on_stop_click())
        self._stop_btn.bind("<Enter>", lambda e: self._stop_btn.configure(bg="#3a1a1a"))
        self._stop_btn.bind("<Leave>", lambda e: self._stop_btn.configure(bg="#2a1a1a"))

        gear = tk.Label(
            self._bottom_frame, text="⚙️", font=("Segoe UI", 14),
            fg=_FG_DIM, bg=_BG, cursor="hand2",
        )
        gear.pack(side="left", padx=6)
        gear.bind("<Button-1>", lambda e: self._on_gear_click())
        gear.bind("<Enter>", lambda e: gear.configure(fg=_FG))
        gear.bind("<Leave>", lambda e: gear.configure(fg=_FG_DIM))

        # Collapsed by default
        self._text_label.pack_forget()

    # ── Mic button ───────────────────────────────────────────────────────────

    def _on_mic_click(self) -> None:
        self._flash_mic()
        self._mic_callback()

    def _flash_mic(self) -> None:
        """Briefly highlight the mic button."""
        try:
            self._mic_btn.configure(bg="#2563eb", fg="white")
            self._root.after(200, lambda: self._mic_btn.configure(bg="#1a1a2e", fg=_FG))
        except Exception:
            pass

    def _on_stop_click(self) -> None:
        self._stop_callback()

    def _toggle_stop_btn(self, state: str) -> None:
        """Show stop button only when active (listening/processing/speaking)."""
        if not self._stop_btn or not self._bottom_frame:
            return
        visible = state in ("listening", "transcribing", "processing", "speaking")
        if visible:
            self._stop_btn.pack(side="left", padx=6, before=self._bottom_frame.winfo_children()[-1])
        else:
            self._stop_btn.pack_forget()

    def _on_gear_click(self) -> None:
        """Open setup by launching a subprocess."""
        import subprocess
        import sys
        subprocess.Popen(
            [sys.executable, "-m", "ui.setup_launcher"],
            cwd=str(__import__("config")._PROJECT_ROOT),
        )

    # ── Orb animation ────────────────────────────────────────────────────────

    def _animate(self) -> None:
        if not self._root:
            return
        self._anim_phase += 1
        self._draw_orb(self._state, self._anim_phase)
        try:
            self._root.after(40, self._animate)
        except tk.TclError:
            pass

    def _draw_orb(self, state: str, phase: int) -> None:
        c = self._orb_canvas
        if not c:
            return
        c.delete("all")
        cx, cy = 50, 50
        pal = _ORB_COLORS.get(state, _ORB_COLORS["idle"])
        t = phase * 0.06
        sin = math.sin

        if state == "idle":
            pulse = 1 + 0.03 * sin(t * 1.2)
            r = int(pal["r"] * pulse)
            self._draw_glow(c, cx, cy, r + 12, pal["b"], 2)
            self._draw_glow(c, cx, cy, r + 6, pal["b"], 1)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["a"], outline="")

        elif state in ("listening", "transcribing"):
            # Radiating rings
            for i in range(4):
                offset = (phase + i * 15) % 50
                r = pal["r"] + offset * 1.8
                width = max(1, 4 - i)
                fade = 1 - offset / 50
                if fade > 0.15:
                    c.create_oval(
                        cx - r, cy - r, cx + r, cy + r,
                        outline=pal["b"], width=width,
                    )
            pulse = 1 + 0.06 * sin(t * 3)
            r = int(pal["r"] * pulse)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["a"], outline="")
            # Center bright spot
            c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="white", outline="")

        elif state == "processing":
            # Spinning arcs
            for i in range(3):
                start = (phase * 4 + i * 120) % 360
                r = pal["r"] + 6 + 4 * sin(t * 2 + i)
                c.create_arc(
                    cx - r, cy - r, cx + r, cy + r,
                    start=start, extent=80,
                    outline=pal["b"], width=3,
                )
            pulse = 1 + 0.04 * sin(t * 2.5)
            r = int(pal["r"] * pulse)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["a"], outline="")

        elif state == "speaking":
            # Wave bars around orb
            for i in range(6):
                angle = i * 1.047 + t * 2
                bar_len = 8 + 12 * abs(sin(t * 4 + i * 0.8))
                bx = cx + math.cos(angle) * (pal["r"] + 8)
                by = cy + math.sin(angle) * (pal["r"] + 8)
                ex = cx + math.cos(angle) * (pal["r"] + 8 + bar_len)
                ey = cy + math.sin(angle) * (pal["r"] + 8 + bar_len)
                c.create_line(bx, by, ex, ey, fill=pal["b"], width=3, capstyle="round")
            pulse = 1 + 0.05 * sin(t * 5)
            r = int(pal["r"] * pulse)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["a"], outline="")
            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="white", outline="")

        elif state == "error":
            pulse = 1 + 0.04 * sin(t * 1.5)
            r = int(pal["r"] * pulse)
            c.create_oval(cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8,
                          outline=pal["b"], width=2)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["a"], outline="")

    @staticmethod
    def _draw_glow(c: tk.Canvas, cx: int, cy: int, r: int, color: str, width: int) -> None:
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=width)

    # ── State machine ────────────────────────────────────────────────────────

    def _set_state_internal(self, state: str, text: str) -> None:
        self._state = state
        self._toggle_stop_btn(state)

        if state == "hidden":
            if self._root:
                self._root.withdraw()
            return

        if self._root:
            self._root.deiconify()

        expanded = state != "idle"

        if expanded != self._expanded:
            if expanded:
                self._text_label.pack(pady=(2, 0))
            else:
                self._text_label.pack_forget()
            self._position_window(compact=not expanded)

        pal = _ORB_COLORS.get(state, _ORB_COLORS["idle"])
        status_map = {
            "idle": "Nexus Ready",
            "listening": "Listening...",
            "transcribing": "Got it!",
            "processing": "Thinking...",
            "speaking": "Speaking...",
            "error": "Error",
        }
        label = status_map.get(state, "Nexus Ready")
        self._status_label.config(text=label, fg=pal["a"])
        self._text_label.config(text=text)

        # Mic button color
        mic_fg = pal["a"] if state != "idle" else _FG
        try:
            self._mic_btn.config(fg=mic_fg)
        except Exception:
            pass

        # Auto-idle after speaking
        if state == "speaking" and text:
            self._text_label.config(fg=_FG)

    # ── Queue polling ────────────────────────────────────────────────────────

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
