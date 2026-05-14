"""
Nexus TTS Engine — Speech synthesis via edge-tts + Windows native MCI playback.

Flow:
    1. Receive text to speak.
    2. Generate MP3 via edge_tts.Communicate (async, Microsoft Edge neural voices).
    3. Play the MP3 via Windows MCI (winmm.dll) — zero external deps.
    4. Clean up the temp file after playback.
"""

import asyncio
import ctypes
import logging
import os
import time
import uuid
from ctypes import wintypes

import edge_tts

import config

logger = logging.getLogger("nexus.tts")

# ── Windows MCI (Media Control Interface) ───────────────────────────────────
# Uses winmm.dll which is part of every Windows install since Windows 95.
_winmm = ctypes.windll.winmm


def _play_mci(filepath: str) -> None:
    """Play an audio file synchronously via Windows MCI."""
    alias = "nexus_tts"
    open_cmd = f'open "{filepath}" type mpegvideo alias {alias}'
    play_cmd = f"play {alias} wait"
    close_cmd = f"close {alias}"

    buf = ctypes.create_unicode_buffer(256)

    result = _winmm.mciSendStringW(open_cmd, buf, len(buf), 0)
    if result != 0:
        _winmm.mciGetErrorStringW(result, buf, len(buf))
        raise RuntimeError(f"MCI open failed: {buf.value}")

    try:
        result = _winmm.mciSendStringW(play_cmd, buf, len(buf), 0)
        if result != 0:
            _winmm.mciGetErrorStringW(result, buf, len(buf))
            raise RuntimeError(f"MCI play failed: {buf.value}")
    finally:
        _winmm.mciSendStringW(close_cmd, None, 0, 0)


async def speak(text: str) -> None:
    """
    Synthesise *text* into speech and play it through the default speakers.
    The function blocks (async-awaits) until playback finishes.
    """
    if not text or not text.strip():
        return

    text = text.strip()
    if len(text) > 1500:
        text = text[:1497] + "..."
        logger.warning("TTS text truncated to 1500 chars.")

    temp_path = config.TEMP_AUDIO_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3"

    try:
        communicate = edge_tts.Communicate(
            text,
            voice=config.TTS_VOICE,
            rate=config.TTS_RATE,
            volume=config.TTS_VOLUME,
        )
        await communicate.save(str(temp_path))
        logger.info("TTS audio generated: %s", temp_path.name)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _play_mci, str(temp_path))

    except edge_tts.exceptions.NoAudioReceived:
        logger.error("Edge-TTS returned no audio for text: %.60s...", text)
    except Exception as exc:
        logger.error("TTS failed: %s", exc)
    finally:
        try:
            if temp_path.exists():
                os.remove(temp_path)
        except OSError:
            pass


async def stop_speaking() -> None:
    """Immediately stop any ongoing TTS playback."""
    try:
        _winmm.mciSendStringW("stop nexus_tts", None, 0, 0)
        _winmm.mciSendStringW("close nexus_tts", None, 0, 0)
        logger.info("TTS playback stopped.")
    except Exception as exc:
        logger.warning("Could not stop playback: %s", exc)
