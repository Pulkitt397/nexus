<div align="center">

```
  _   _                          
 | \ | | _____  ___   _ ___      
 |  \| |/ _ \ \/ / | | / __|     
 | |\  |  __/>  <| |_| \__ \     
 |_| \_|\___/_/\_\\__,_|___/     
                                   
 Windows 11 AI Assistant
 Privacy-First · Local · Autonomous
```

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Gemini_2.5_Flash-orange?logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/flash/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows_11-0078D4?logo=windows&logoColor=white)](https://www.microsoft.com/windows)

**Nexus** is an always-on, voice-activated Windows 11 AI assistant that can control your entire PC.  
Press a hotkey, speak naturally, and watch it execute multi-step tasks autonomously.

</div>

---

## ✨ What It Can Do

| Category | Capabilities |
|----------|-------------|
| 🌐 **Browser Automation** | Launch browser, navigate sites, click elements, type text, search YouTube, scrape content, manage tabs — full Playwright-powered web control |
| 🖱️ **Mouse & Keyboard** | Move, click, drag, scroll, type text, press hotkeys (`Ctrl+C`, `Alt+Tab`, `Win+R`, etc.) — simulates real user input anywhere |
| 🖥️ **Screen Awareness** | Take screenshots, OCR visible text, find text on screen with coordinates, read pixel colors |
| 📂 **File Operations** | Create, read, write, copy, move, rename, delete files and folders; download from URLs; list directories |
| 🔍 **App Management** | Open/close any app (browser, notepad, vscode, spotify, etc.), list running processes |
| 🪟 **Window Control** | Focus, minimize, maximize, restore, move, resize, close any window; get active window info |
| 🔄 **Process Management** | List, kill, force-kill, start processes; get detailed process info and resource usage |
| 🔊 **System Control** | Change volume, brightness, screen resolution; toggle mute; play/pause media |
| ⚡ **Power Management** | Lock, sleep, restart, shut down the PC |
| 🌡️ **System Info** | CPU, RAM, disk, battery, OS version, IP address, uptime, current time |
| 📋 **Clipboard** | Read and write clipboard content |
| 🌍 **Web Search** | Open URLs and perform Google searches in default browser |
| 📡 **Network** | WiFi connect/disconnect, get network status and SSID |
| ⚙️ **Settings** | Set wallpaper, send toast notifications, list drives, eject media, empty recycle bin, read environment variables |
| 🎙️ **Voice I/O** | Speech-to-text (faster-whisper) + natural TTS (Edge neural voices) |

---

## 🚀 Quick Start

### Prerequisites

- **Windows 11**
- **Python 3.11+**
- **A Gemini API key** — get one free at [Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```powershell
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/nexus.git
cd nexus

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your API key (opens a GUI window)
python main.py --setup

# 4. (Optional) Install Tesseract OCR for screen text reading
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Run

```powershell
# Voice mode — press Ctrl+Shift+N to speak
python main.py

# Text-only mode (no microphone needed)
python main.py --no-voice

# Single command
python main.py --text "open browser and go to youtube.com"

# Without the transparent overlay
python main.py --no-overlay
```

---

## 🎮 Usage Examples

Just speak or type naturally:

| You Say | Nexus Does |
|---------|-----------|
| *"Open Chrome and go to YouTube"* | Launches browser, navigates to YouTube |
| *"Search for Mr Who Is The Boss and play the latest video"* | Types search, finds video, clicks to play |
| *"What's my CPU and RAM usage?"* | Reads system stats and speaks them back |
| *"Turn the volume to 50%"* | Adjusts system volume |
| *"Create a file called notes.txt with my shopping list"* | Creates file with content |
| *"Kill Chrome, it's lagging"* | Terminates all Chrome processes |
| *"Take a screenshot and tell me what you see"* | Captures screen and OCRs the text |
| *"Lock my PC"* | Locks workstation immediately |
| *"Dim the screen to 30%"* | Reduces display brightness |

### Complex Multi-Step Task

**"Open browser, go to YouTube, search for Mr Who Is The Boss, and play the latest video"**

Nexus chains: `browser_launch → browser_navigate → browser_type → browser_press_key(Enter) → browser_get_text → browser_click` — all autonomously in one request.

---

## 🏗 Architecture

```
nexus/
├── main.py              # Orchestrator — voice/text loops + multi-turn function calling
├── config.py            # Central configuration (API keys, paths, system prompt)
├── requirements.txt     # Python dependencies
├── .env.example         # Template for API keys
│
├── tools/               # Tool functions exposed to Gemini
│   ├── __init__.py         # Registry — auto-loads all tools with graceful fallback
│   ├── app_manager.py      # Open/close/list applications
│   ├── browser_control.py  # Full web automation (Playwright)
│   ├── mouse_keyboard.py   # Desktop input simulation (PyAutoGUI)
│   ├── screen_capture.py   # Screenshots + OCR
│   ├── media_control.py    # Play/pause/next/previous media
│   ├── window_manager.py   # Window positioning & focus (win32)
│   ├── file_manager.py     # File create/read/write/copy/move/delete/download
│   ├── process_manager.py  # Process list/kill/start/info
│   ├── system_tools.py     # Resolution, wallpaper, WiFi, notifications, drives
│   ├── file_ops.py         # Legacy file operations (search, clipboard)
│   ├── volume_control.py   # System volume via pycaw
│   ├── brightness_control.py # Screen brightness
│   ├── power_manager.py    # Lock/sleep/restart/shutdown
│   ├── system_info.py      # CPU, RAM, disk, battery, IP, time
│   └── web_search.py       # Open URLs, web search
│
├── perception/           # Speech I/O
│   ├── stt_engine.py        # Speech-to-text via faster-whisper
│   └── tts_engine.py        # Text-to-speech via edge-tts (Windows MCI playback)
│
├── memory/               # Conversation memory
│   └── episode_log.py       # JSONL episodic memory with context injection
│
└── ui/                   # Visual overlay
    └── overlay.py           # Transparent floating card (Gemini Live-style)
```

### How Multi-Step Tasks Work

Nexus uses **automatic multi-turn function calling**:

1. User speaks/type: *"Open browser and go to YouTube"*
2. Gemini receives the request + tool schemas
3. Gemini returns a `function_call` → `open_application("browser")`
4. Nexus executes the function, returns result to Gemini
5. Gemini returns another `function_call` → `browser_navigate("youtube.com")`
6. Nexus executes, returns result
7. Gemini returns final text response: *"Done! Browser is open at YouTube."*
8. Nexus speaks the response aloud

This loop handles unlimited chained tool calls (up to 30 turns by default).

---

## 🎨 Transparent Overlay

When active, Nexus displays a Gemini Live-style floating card in the bottom-right corner:

- **Idle** → Compact pill: `● Nexus Ready` (green)
- **Listening** → Expands, yellow dot + `Listening...`
- **Processing** → Blue dot + shows what tool is being called
- **Speaking** → Cyan dot + shows the response text

Always-on-top, semi-transparent (92%), rounded corners, click-through.

---

## 🔒 Privacy

- **Everything runs locally** on your machine
- The only external API call is to **Gemini** for LLM inference
- Conversation history is stored as a local JSONL file (never uploaded)
- No telemetry, no tracking, no cloud dependencies except the LLM provider

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Gemini 2.5 Flash LLM with function calling |
| `faster-whisper` | Local speech-to-text (runs on CPU) |
| `edge-tts` | Microsoft Edge neural voices for TTS |
| `playwright` | Full browser automation engine |
| `pyautogui` | Mouse & keyboard simulation |
| `mss` | High-speed screen capture |
| `pytesseract` | OCR (requires separate Tesseract install) |
| `pywin32` | Windows API bindings (windows, processes) |
| `psutil` | System resource monitoring |
| `pycaw` | Windows audio/volume control |
| `screen-brightness-control` | Display brightness |
| `pyperclip` | Clipboard access |
| `sounddevice` | Microphone capture for STT |
| `keyboard` | Global hotkey listener |

---

## 🧪 Running After Setup

```powershell
# Verify all tools load correctly
python -c "from tools import TOOL_REGISTRY; print(f'{len(TOOL_REGISTRY)} tools registered')"

# Quick test with a single command
python main.py --text "what time is it"

# Full voice mode
python main.py
```

---

## 📄 License

MIT — do whatever you want, just don't blame us.

---

<div align="center">
  <sub>Built with ❤️ for Windows 11 · Powered by Gemini 2.5 Flash</sub>
</div>
