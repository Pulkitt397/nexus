"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          NEXUS — main.py                                     ║
║              Windows 11 AI Assistant • Core Orchestrator                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Architecture:
    Qt overlay runs on the MAIN thread (required by Windows).
    asyncio (Gemini, STT, TTS) runs in a background thread.
"""

import argparse
import asyncio
import logging
import sys
import threading
from typing import Optional

import config
from memory.episode_log import get_context_summary, log_episode
from tools import TOOL_REGISTRY
from ui.setup import run_setup_dialog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-22s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("nexus.core")

_BANNER = r"""
    +========================================+
    |     _   _                             |
    |    | \ | | _____  ___   _ ___         |
    |    |  \| |/ _ \ \/ / | | / __|        |
    |    | |\  |  __/>  <| |_| \__ \        |
    |    |_| \_|\___/_/\_\\__,_|___/        |
    |                                        |
    |    Windows 11 AI Assistant             |
    |    Privacy-First . Local . Autonomous  |
    +========================================+
"""

_client = None
_overlay = None  # set by main thread after Qt init
_stop_event: threading.Event = threading.Event()


def _get_client():
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            logger.critical("GEMINI_API_KEY is not set. Exiting.")
            sys.exit(1)
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
        logger.info("Gemini client initialised (model: %s).", config.GEMINI_MODEL)
    return _client


def _build_tool_map():
    tool_map = {}
    for func in TOOL_REGISTRY:
        if callable(func):
            tool_map[func.__name__] = func
    return tool_map


async def _process_message(user_text: str) -> str:
    from google.genai import types
    client = _get_client()
    context = get_context_summary(n=5)
    system_instruction = config.SYSTEM_PROMPT
    if context:
        system_instruction += f"\n\n{context}"

    generation_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=TOOL_REGISTRY,
        temperature=0.7,
        max_output_tokens=4096,
    )

    tool_map = _build_tool_map()
    contents: list = [user_text]
    all_tools_used: set[str] = set()

    for turn in range(config.MAX_FUNCTION_CALLING_TURNS):
        try:
            response = await client.aio.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=contents,
                config=generation_config,
            )
        except Exception as exc:
            error_msg = f"Gemini error: {exc}"
            logger.error(error_msg)
            log_episode(user_input=user_text, assistant_response=error_msg)
            if _overlay:
                _overlay.set_state("error", str(exc))
            return f"I hit an error: {exc}"

        function_calls = []
        text_parts = []
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)
                        if part.text:
                            text_parts.append(part.text)

        if not function_calls:
            reply = " ".join(text_parts) or response.text or ""
            log_episode(user_input=user_text, assistant_response=reply,
                        tools_used=list(all_tools_used) if all_tools_used else None)
            return reply

        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        func_response_parts = []
        for fc in function_calls:
            func_name = fc.name
            func_args = dict(fc.args) if fc.args else {}
            all_tools_used.add(func_name)
            logger.info("Tool call [turn %d]: %s(%s)", turn + 1, func_name, func_args)
            if _overlay and turn == 0:
                readable = func_name.replace("_", " ").title()
                _overlay.set_state("processing", f"{readable}... ({func_args})")
            if func_name in tool_map:
                try:
                    result = tool_map[func_name](**func_args)
                except Exception as exc:
                    result = f"Error executing {func_name}: {exc}"
                    logger.error(result)
            else:
                result = f"Unknown tool: {func_name}"
            func_response_parts.append(
                types.Part.from_function_response(name=func_name, response={"result": result})
            )
        contents.append(types.Content(role="function", parts=func_response_parts))

    msg = "I reached the maximum number of steps. Please check progress and ask me to continue if needed."
    log_episode(user_input=user_text, assistant_response=msg, tools_used=list(all_tools_used))
    return msg


# ── Async entry point (runs in background thread) ──────────────────────────

async def _async_main(args: argparse.Namespace):
    if args.text:
        await _single_shot(args.text)
    elif args.no_voice:
        await _text_loop()
    else:
        await _voice_loop()


async def _voice_loop():
    import keyboard as kb
    from perception.stt_engine import listen
    from perception.tts_engine import speak

    logger.info("Voice mode active. Press [%s] or click 🎤 to speak.", config.HOTKEY)
    if _overlay:
        _overlay.set_state("idle", "Click 🎤 or press hotkey to speak")
    await speak("Nexus online. Click the mic or press the hotkey when you need me.")

    loop = asyncio.get_running_loop()
    hotkey_event = asyncio.Event()

    def _trigger():
        loop.call_soon_threadsafe(hotkey_event.set)

    if _overlay:
        _overlay.set_mic_callback(_trigger)

    kb.add_hotkey(config.HOTKEY, _trigger, suppress=True)

    try:
        while True:
            hotkey_event.clear()
            await hotkey_event.wait()

            logger.info("Triggered - listening...")
            if _overlay:
                _overlay.set_state("listening", "")

            user_text = await listen()
            if _stop_event.is_set():
                _stop_event.clear()
                if _overlay:
                    _overlay.set_state("idle", "Stopped")
                continue

            if not user_text.strip():
                logger.info("No speech detected, ignoring.")
                if _overlay:
                    _overlay.set_state("idle", "No speech detected")
                continue

            if _overlay:
                _overlay.set_state("transcribing", user_text)
            logger.info("User said: %s", user_text)
            print(f"\n  [You]: {user_text}")

            if _overlay:
                _overlay.set_state("processing", f'Processing: "{user_text}"')

            reply = await _process_message(user_text)
            if _stop_event.is_set():
                _stop_event.clear()
                if _overlay:
                    _overlay.set_state("idle", "Stopped")
                continue

            print(f"  [Nexus]: {reply}\n")
            if _overlay:
                _overlay.set_state("speaking", reply)
            await speak(reply)
            if _stop_event.is_set():
                _stop_event.clear()
            if _overlay:
                _overlay.set_state("idle", "Click 🎤 or press hotkey to speak")
    finally:
        kb.remove_hotkey(config.HOTKEY)


async def _text_loop():
    try:
        from perception.tts_engine import speak
        await speak("Nexus online in text mode.")
        tts_available = True
    except Exception:
        tts_available = False

    logger.info("Text mode active. Type below. Ctrl+C to quit.")
    loop = asyncio.get_running_loop()
    if _overlay:
        _overlay.set_state("idle", "Text mode - type your message")

    while True:
        try:
            user_text = await loop.run_in_executor(None, lambda: input("\n  [You]: "))
        except (EOFError, KeyboardInterrupt):
            break
        user_text = user_text.strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit", "bye"}:
            farewell = "Nexus shutting down. Goodbye."
            print(f"  [Nexus]: {farewell}")
            if _overlay:
                _overlay.set_state("speaking", farewell)
            if tts_available:
                try:
                    await speak(farewell)
                except Exception:
                    pass
            break
        if _overlay:
            _overlay.set_state("processing", user_text)
        reply = await _process_message(user_text)
        print(f"  [Nexus]: {reply}")
        if _overlay:
            _overlay.set_state("speaking", reply)
        if tts_available:
            try:
                await speak(reply)
            except Exception:
                pass
        if _overlay:
            _overlay.set_state("idle", "Type your message")


async def _single_shot(text: str):
    logger.info("Single-shot: %.80s", text)
    if _overlay:
        _overlay.set_state("processing", text)
    reply = await _process_message(text)
    print(f"  [Nexus]: {reply}")
    if _overlay:
        _overlay.set_state("speaking", reply)
    try:
        from perception.tts_engine import speak
        await speak(reply)
    except Exception:
        pass
    if _overlay:
        _overlay.set_state("idle", "")


# ── Main entry (Qt on main thread) ─────────────────────────────────────────

def main():
    global _overlay

    parser = argparse.ArgumentParser(description="Nexus - Windows 11 AI Assistant")
    parser.add_argument("--text", type=str, default=None, help="Single text query.")
    parser.add_argument("--no-voice", action="store_true", help="Text-only mode.")
    parser.add_argument("--no-overlay", action="store_true", help="No overlay UI.")
    parser.add_argument("--setup", action="store_true", help="Settings window.")
    args = parser.parse_args()

    print(_BANNER)
    logger.info("Nexus initialising...")
    logger.info("Tool registry: %d tools available.", len(TOOL_REGISTRY))

    # ── Setup / API check ──────────────────────────────────────────────────
    if args.setup or not config.GEMINI_API_KEY or config.GEMINI_API_KEY.startswith("your_"):
        try:
            saved = run_setup_dialog()
            if not saved:
                logger.info("Setup cancelled.")
                return
            import importlib
            importlib.reload(config)
            if args.setup:
                logger.info("Configuration updated.")
                return
        except Exception as exc:
            if args.setup:
                logger.critical("Setup failed: %s", exc)
                return
            logger.warning("Setup failed: %s", exc)
            if not config.GEMINI_API_KEY:
                logger.critical("No GEMINI_API_KEY. Run with --setup")
                sys.exit(1)

    _stop_event.clear()

    def _on_stop():
        _stop_event.set()
        try:
            import ctypes
            ctypes.windll.winmm.mciSendStringW("stop nexus_tts", None, 0, 0)
            ctypes.windll.winmm.mciSendStringW("close nexus_tts", None, 0, 0)
        except Exception:
            pass

    # ── Start Qt overlay on MAIN thread ────────────────────────────────────
    if not args.no_overlay:
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.overlay import NexusOverlayWindow
            app = QApplication([])
            app.setApplicationName("nexus-overlay")

            def _mic_callback():
                pass  # wired later by async thread

            _overlay = NexusOverlayWindow(mic_callback=lambda: None, stop_callback=_on_stop)
            _overlay.set_state("idle", "Starting...")
            _overlay.show()
            logger.info("Orb overlay active.")
        except Exception as exc:
            logger.warning("Overlay failed: %s", exc)
            _overlay = None
            app = None
    else:
        app = None

    # ── Start asyncio in a background thread ───────────────────────────────
    async_exit = threading.Event()

    def _run_async():
        try:
            asyncio.run(_async_main(args))
        except Exception as exc:
            logger.critical("Async error: %s", exc, exc_info=True)
        finally:
            async_exit.set()

    async_thread = threading.Thread(target=_run_async, daemon=True, name="nexus-async")
    async_thread.start()

    # ── Qt event loop (main thread) ────────────────────────────────────────
    try:
        if app:
            app.exec()
        else:
            async_exit.wait()  # no overlay, just wait for async to finish
    except KeyboardInterrupt:
        print("\n")
        logger.info("Nexus terminated by user.")
    except Exception as exc:
        logger.critical("Fatal: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        if _overlay:
            _overlay.close()
        logger.info("Nexus shutdown complete.")


if __name__ == "__main__":
    main()
