"""
Nexus Orb Overlay — Floating transparent card with animated orb.

Built with PyQt6 for per-pixel alpha, smooth animations, and gradients.
State changes via thread-safe queue polling (QTimer).
"""

import logging
import math
import queue
import threading
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import (
    QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter,
    QPainterPath, QRadialGradient, QRegion,
)
from PyQt6.QtWidgets import (
    QApplication, QGraphicsDropShadowEffect, QGraphicsEllipseItem,
    QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

import config

logger = logging.getLogger("nexus.ui.overlay")

_CARD_W = 380
_CARD_H_IDLE = 195
_CARD_H_ACTIVE = 275

_COLORS = {
    "idle":      {"a": QColor(74, 222, 128), "b": QColor(134, 239, 172), "c": QColor(22, 101, 52)},
    "listening": {"a": QColor(96, 165, 250), "b": QColor(147, 197, 253), "c": QColor(30, 58, 95)},
    "transcribing": {"a": QColor(96, 165, 250), "b": QColor(147, 197, 253), "c": QColor(30, 58, 95)},
    "processing": {"a": QColor(167, 139, 250), "b": QColor(196, 181, 253), "c": QColor(59, 7, 100)},
    "speaking":  {"a": QColor(34, 211, 238), "b": QColor(103, 232, 249), "c": QColor(8, 51, 68)},
    "error":     {"a": QColor(248, 113, 113), "b": QColor(252, 165, 165), "c": QColor(69, 10, 10)},
}

_STATUS_TEXT = {
    "idle": "Nexus Ready",
    "listening": "Listening...",
    "transcribing": "Got it!",
    "processing": "Thinking...",
    "speaking": "Speaking...",
    "error": "Error",
}


class OrbView(QGraphicsView):
    """Canvas that draws the animated orb."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(110, 110)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.state = "idle"
        self.phase = 0
        self._items = []

    def set_state(self, state: str):
        self.state = state

    def tick(self):
        self.phase += 1
        self._scene.clear()
        self._draw(self.state, self.phase)

    def _draw(self, state: str, phase: int):
        pal = _COLORS.get(state, _COLORS["idle"])
        cx, cy = 55, 55
        t = phase * 0.06
        s = math.sin

        if state == "idle":
            pulse = 1 + 0.03 * s(t * 1.2)
            r = int(22 * pulse)
            self._circle(cx, cy, r + 14, pal["b"], 3, 60)
            self._circle(cx, cy, r + 7, pal["b"], 1, 40)
            self._circle(cx, cy, r, pal["a"], 0, 255)

        elif state in ("listening", "transcribing"):
            for i in range(4):
                offset = (phase + i * 15) % 50
                rr = 28 + offset * 1.8
                width = max(1, 4 - i)
                fade = max(0, 1 - offset / 50)
                if fade > 0.15:
                    c2 = QColor(pal["b"])
                    c2.setAlphaF(fade)
                    self._circle(cx, cy, rr, c2, int(width), 0)
            pulse = 1 + 0.06 * s(t * 3)
            r = int(28 * pulse)
            self._circle(cx, cy, r, pal["a"], 0, 255)
            self._circle(cx, cy, 6, QColor(255, 255, 255), 0, 200)

        elif state == "processing":
            for i in range(3):
                start = (phase * 4 + i * 120) / 57.3
                rr = 26 + 6 + 4 * s(t * 2 + i)
                self._arc(cx, cy, rr, start, 1.4, pal["b"])
            pulse = 1 + 0.04 * s(t * 2.5)
            r = int(26 * pulse)
            self._circle(cx, cy, r, pal["a"], 0, 255)

        elif state == "speaking":
            for i in range(6):
                angle = i * 1.047 + t * 2
                bar_len = 8 + 12 * abs(s(t * 4 + i * 0.8))
                bx = cx + math.cos(angle) * (28 + 8)
                by = cy + math.sin(angle) * (28 + 8)
                ex = cx + math.cos(angle) * (28 + 8 + bar_len)
                ey = cy + math.sin(angle) * (28 + 8 + bar_len)
                pen = self._scene.addLine(bx, by, ex, ey, pal["b"])
                pen.setPenWidth(3)
            pulse = 1 + 0.05 * s(t * 5)
            r = int(28 * pulse)
            self._circle(cx, cy, r, pal["a"], 0, 255)
            self._circle(cx, cy, 5, QColor(255, 255, 255), 0, 200)

        elif state == "error":
            pulse = 1 + 0.04 * s(t * 1.5)
            r = int(24 * pulse)
            self._circle(cx, cy, r + 8, pal["b"], 2, 60)
            self._circle(cx, cy, r, pal["a"], 0, 255)

    def _circle(self, cx, cy, r, color, border_width, alpha):
        c = QColor(color)
        if alpha < 255:
            c.setAlpha(alpha)
        item = self._scene.addEllipse(cx - r, cy - r, r * 2, r * 2, QBrush(c) if border_width == 0 else QBrush())
        if border_width > 0:
            item.setPen(c)
            item.setBrush(QBrush())
        else:
            item.setBrush(QBrush(c))

    def _arc(self, cx, cy, r, start_angle, extent, color):
        rect_size = r * 2
        item = self._scene.addArc(
            cx - r, cy - r, rect_size, rect_size,
            int(start_angle * 16 * 57.3),
            int(extent * 16 * 57.3),
            color,
        )
        item.setPenWidth(3)


class NexusOverlayWindow(QWidget):
    """Frameless, transparent, always-on-top overlay window."""

    def __init__(self, mic_callback=None, stop_callback=None):
        super().__init__()
        self._mic_callback = mic_callback or (lambda: None)
        self._stop_callback = stop_callback or (lambda: None)
        self._state = "idle"
        self._expanded = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._setup_ui()
        self._position(compact=True)
        self._show_stop_btn(False)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_orb)
        self._anim_timer.start(35)

    def set_mic_callback(self, cb):
        self._mic_callback = cb

    def set_stop_callback(self, cb):
        self._stop_callback = cb

    # ── UI building ─────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Orb
        self.orb = OrbView(self)
        layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status
        self.status_label = QLabel("Nexus Ready")
        self.status_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #e8e8f0;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Detail text
        self.text_label = QLabel("")
        self.text_label.setFont(QFont("Segoe UI", 9))
        self.text_label.setStyleSheet("color: #808098;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumWidth(_CARD_W - 48)
        layout.addWidget(self.text_label)

        layout.addSpacing(6)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(10)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(48, 40)
        self.mic_btn.setStyleSheet(self._btn_style("#1a1a2e", "#e8e8f0"))
        self.mic_btn.clicked.connect(self._on_mic_click)
        btn_row.addWidget(self.mic_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(48, 40)
        self.stop_btn.setStyleSheet(self._btn_style("#2a1a1a", "#f87171"))
        self.stop_btn.clicked.connect(self._on_stop_click)
        btn_row.addWidget(self.stop_btn)

        gear_btn = QPushButton("⚙️")
        gear_btn.setFixedSize(48, 40)
        gear_btn.setStyleSheet(self._btn_style("transparent", "#606080"))
        gear_btn.clicked.connect(self._on_gear_click)
        btn_row.addWidget(gear_btn)

        layout.addLayout(btn_row)
        layout.addSpacing(12)

    @staticmethod
    def _btn_style(bg, fg):
        return (
            f"QPushButton {{ background: {bg}; color: {fg}; font-size: 20px; "
            f"border-radius: 8px; padding: 0px; }}"
            f"QPushButton:hover {{ background: #2a2a3e; }}"
        )

    # ── Positioning ─────────────────────────────────────────────────────────

    def _position(self, compact: bool = True):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        h = _CARD_H_IDLE if compact else _CARD_H_ACTIVE
        x = (geo.width() - _CARD_W) // 2 + geo.x()
        y = geo.y() + 16
        self.setFixedSize(_CARD_W, h)
        self.move(x, y)
        self._expanded = not compact

        # Rounded corners mask
        path = QPainterPath()
        path.addRoundedRect(0, 0, _CARD_W, h, 18, 18)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    # ── State ───────────────────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def set_state(self, state: str, text: str = ""):
        self._state = state
        self.orb.set_state(state)

        expanded = state != "idle"
        if expanded != self._expanded:
            self.text_label.setVisible(expanded)
            self._position(compact=not expanded)

        pal = _COLORS.get(state, _COLORS["idle"])
        label = _STATUS_TEXT.get(state, "Nexus Ready")
        self.status_label.setText(label)
        self.status_label.setStyleSheet(f"color: {pal['a'].name()};")
        self.text_label.setText(text)
        self.text_label.setStyleSheet(
            f"color: {'#e8e8f0' if state == 'speaking' else '#808098'};"
        )

        self._show_stop_btn(state in ("listening", "transcribing", "processing", "speaking"))
        self.orb.tick()

    def _show_stop_btn(self, show: bool):
        self.stop_btn.setVisible(show)

    def _tick_orb(self):
        self.orb.tick()

    # ── Button handlers ─────────────────────────────────────────────────────

    def _on_mic_click(self):
        self.mic_btn.setStyleSheet(self._btn_style("#2563eb", "white"))
        QTimer.singleShot(200, lambda: self.mic_btn.setStyleSheet(self._btn_style("#1a1a2e", "#e8e8f0")))
        self._mic_callback()

    def _on_stop_click(self):
        self._stop_callback()
        self.set_state("idle", "Stopped")

    def _on_gear_click(self):
        import subprocess, sys
        subprocess.Popen(
            [sys.executable, "-m", "ui.setup_launcher"],
            cwd=str(config._PROJECT_ROOT),
        )


class NexusOverlay:
    """Thread-safe wrapper that runs the PyQt6 overlay in a daemon thread."""

    def __init__(self, mic_callback=None, stop_callback=None):
        self._cmd_queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._app: Optional[QApplication] = None
        self._window: Optional[NexusOverlayWindow] = None
        self._mic_callback = mic_callback
        self._stop_callback = stop_callback

    def set_mic_callback(self, cb):
        self._mic_callback = cb
        if self._window:
            self._window.set_mic_callback(cb)

    def set_stop_callback(self, cb):
        self._stop_callback = cb
        if self._window:
            self._window.set_stop_callback(cb)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="nexus-overlay")
        self._thread.start()
        logger.info("PyQt6 orb overlay started.")

    def stop(self):
        if self._app:
            self._app.quit()
        logger.info("Orb overlay stopped.")

    def set_state(self, state: str, text: str = ""):
        self._cmd_queue.put((state, text))

    def _run(self):
        self._app = QApplication([])
        self._app.setApplicationName("nexus-overlay")
        self._window = NexusOverlayWindow(self._mic_callback, self._stop_callback)
        self._window.set_state("idle", "")
        self._window.show()

        # Poll queue
        poll_timer = QTimer()
        poll_timer.timeout.connect(self._poll)
        poll_timer.start(100)

        self._app.exec()

    def _poll(self):
        if not self._window:
            return
        try:
            while True:
                state, text = self._cmd_queue.get_nowait()
                self._window.set_state(state, text)
        except queue.Empty:
            pass
