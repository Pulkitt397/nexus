"""
Nexus Setup Wizard — API key entry & model selection in a clean GUI.

Auto-shown on first launch (no API key found) or via:
    python main.py --setup
"""

import logging
import os
import tkinter as tk
from tkinter import ttk
from pathlib import Path

logger = logging.getLogger("nexus.ui.setup")

# All models available on the Gemini API free tier (Google AI Studio)
# Sorted newest → oldest. No credit card needed for any of these.
AVAILABLE_MODELS = [
    # ── Gemma (open-weight, supports function calling) ──────────────────────
    ("gemma-4-31b-it",       "Gemma 4 31B — Open model, strong reasoning (1500 req/day, free)"),
    ("gemma-4-26b-a4b-it",   "Gemma 4 26B — Open MoE, fast & capable (1500 req/day, free)"),
    # ── Gemini 3 series ─────────────────────────────────────────────────────
    ("gemini-3-flash-preview",     "3 Flash Preview — Newest speed model (500 req/day, free)"),
    ("gemini-3.1-flash-lite-preview", "3.1 Flash-Lite Preview — Newest budget (1500 req/day, free)"),
    # ── Gemini 2.5 series (recommended) ─────────────────────────────────────
    ("gemini-2.5-flash",     "2.5 Flash — Best balance ★ (500 req/day, free)"),
    ("gemini-2.5-flash-lite", "2.5 Flash-Lite — Fastest (1500 req/day, free)"),
    ("gemini-2.5-pro",       "2.5 Pro — Most capable (25 req/day, free)"),
    # ── Gemini 2.0 series (legacy) ──────────────────────────────────────────
    ("gemini-2.0-flash",     "2.0 Flash — Legacy workhorse (1500 req/day, free)"),
    ("gemini-2.0-flash-lite", "2.0 Flash-Lite — Legacy budget (1500 req/day, free)"),
    # ── Gemini 1.5 series (legacy) ──────────────────────────────────────────
    ("gemini-1.5-flash",     "1.5 Flash — Legacy reliable (free)"),
    ("gemini-1.5-pro",       "1.5 Pro — Legacy capable (25 req/day, free)"),
]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"


def load_env_key() -> str:
    """Read the current API key from .env if present."""
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("GEMINI_API_KEY=your_"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def load_env_model() -> str:
    """Read the current model from .env if present."""
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_MODEL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "gemini-2.5-flash"


def save_config(api_key: str, model: str) -> bool:
    """Write API key and model to .env, preserving other values."""
    try:
        lines = []
        if _ENV_PATH.exists():
            lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()

        key_written = False
        model_written = False
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("GEMINI_API_KEY=") and not key_written:
                new_lines.append(f'GEMINI_API_KEY={api_key}')
                key_written = True
            elif stripped.startswith("GEMINI_MODEL=") and not model_written:
                new_lines.append(f'GEMINI_MODEL={model}')
                model_written = True
            else:
                new_lines.append(line)

        if not key_written:
            new_lines.append(f'GEMINI_API_KEY={api_key}')
        if not model_written:
            new_lines.append(f'GEMINI_MODEL={model}')

        _ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        logger.error("Failed to save config: %s", exc)
        return False


def run_setup_dialog() -> bool:
    """
    Show the setup dialog. Returns True if config was saved, False if cancelled.
    """
    root = tk.Tk()
    root.title("Nexus Setup")
    root.configure(bg="#0f0f1a")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    window_w, window_h = 520, 420
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - window_w) // 2
    y = (screen_h - window_h) // 2
    root.geometry(f"{window_w}x{window_h}+{x}+{y}")

    result = False

    def on_save():
        nonlocal result
        key = key_var.get().strip()
        model = model_var.get()
        if not key:
            status_label.config(text="Please enter your API key.", fg="#f87171")
            return
        if not model:
            status_label.config(text="Please select a model.", fg="#f87171")
            return
        if save_config(key, model):
            result = True
            status_label.config(text="Saved! Closing...", fg="#4ade80")
            root.after(800, root.destroy)
        else:
            status_label.config(text="Failed to save. Check permissions.", fg="#f87171")

    def on_cancel():
        nonlocal result
        result = False
        root.destroy()

    def on_open_link():
        import webbrowser
        webbrowser.open("https://aistudio.google.com/apikey")

    # ── UI ──────────────────────────────────────────────────────────────────
    padding = {"padx": 24, "pady": 6}

    title = tk.Label(root, text="Nexus Setup", font=("Segoe UI", 20, "bold"),
                     fg="#e8e8f0", bg="#0f0f1a")
    title.pack(pady=(24, 4))

    subtitle = tk.Label(root, text="Connect your Google Gemini API key to get started.",
                        font=("Segoe UI", 10), fg="#808090", bg="#0f0f1a")
    subtitle.pack(pady=(0, 16))

    # ── API Key ─────────────────────────────────────────────────────────────
    tk.Label(root, text="Gemini API Key", font=("Segoe UI", 10, "bold"),
             fg="#c0c0d0", bg="#0f0f1a", anchor="w").pack(fill="x", **padding)

    key_var = tk.StringVar(value=load_env_key())
    key_entry = tk.Entry(root, textvariable=key_var, font=("Segoe UI", 11),
                         bg="#1a1a2e", fg="#e8e8f0", insertbackground="#e8e8f0",
                         relief="flat", bd=8, highlightthickness=1,
                         highlightbackground="#2a2a3e")
    key_entry.pack(fill="x", **padding)
    key_entry.focus()

    link_btn = tk.Label(root, text="Get a free API key →",
                        font=("Segoe UI", 9, "underline"), fg="#60a5fa",
                        bg="#0f0f1a", cursor="hand2")
    link_btn.pack(anchor="w", **padding)
    link_btn.bind("<Button-1>", lambda e: on_open_link())

    # ── Model ───────────────────────────────────────────────────────────────
    tk.Label(root, text="AI Model", font=("Segoe UI", 10, "bold"),
             fg="#c0c0d0", bg="#0f0f1a", anchor="w").pack(fill="x", **padding)

    model_var = tk.StringVar(value=load_env_model())
    model_menu = ttk.Combobox(root, textvariable=model_var,
                              values=[m[1] for m in AVAILABLE_MODELS],
                              state="readonly", font=("Segoe UI", 10),
                              height=12)
    model_menu.pack(fill="x", **padding)
    # Map display name → model id
    model_display_to_id = {m[1]: m[0] for m in AVAILABLE_MODELS}

    def on_model_select(event):
        display = model_menu.get()
        if display in model_display_to_id:
            model_var.set(model_display_to_id[display])

    model_menu.bind("<<ComboboxSelected>>", on_model_select)

    # Set default selection — must set model_var to the ID, not display string
    current_model = load_env_model()
    for mid, display in AVAILABLE_MODELS:
        if mid == current_model:
            model_menu.set(display)
            model_var.set(mid)
            break
    else:
        default_mid, default_display = AVAILABLE_MODELS[0]
        model_menu.set(default_display)
        model_var.set(default_mid)

    note = tk.Label(root,
                    text="All models above are free via Google AI Studio.\nNo credit card needed.",
                    font=("Segoe UI", 8), fg="#606070", bg="#0f0f1a", justify="left")
    note.pack(anchor="w", **padding)

    # ── Buttons ─────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, bg="#0f0f1a")
    btn_frame.pack(fill="x", pady=(20, 0), padx=24)

    cancel_btn = tk.Button(btn_frame, text="Cancel", command=on_cancel,
                           font=("Segoe UI", 10), bg="#1a1a2e", fg="#808090",
                           relief="flat", bd=0, padx=20, pady=6,
                           activebackground="#2a2a3e", activeforeground="#e8e8f0",
                           cursor="hand2")
    cancel_btn.pack(side="right", padx=(8, 0))

    save_btn = tk.Button(btn_frame, text="Save & Continue", command=on_save,
                         font=("Segoe UI", 10, "bold"), bg="#2563eb", fg="white",
                         relief="flat", bd=0, padx=20, pady=6,
                         activebackground="#1d4ed8", activeforeground="white",
                         cursor="hand2")
    save_btn.pack(side="right")

    # ── Status ──────────────────────────────────────────────────────────────
    status_label = tk.Label(root, text="", font=("Segoe UI", 9),
                            bg="#0f0f1a")
    status_label.pack(pady=(8, 0))

    # Handle Enter key
    root.bind("<Return>", lambda e: on_save())
    root.bind("<Escape>", lambda e: on_cancel())

    # Center on screen after rendering
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 2
    root.geometry(f"+{x}+{y}")

    root.mainloop()
    return result
