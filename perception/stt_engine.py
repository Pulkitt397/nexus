"""
Nexus STT Engine — Real-time microphone capture and transcription via faster-whisper.

Architecture:
    1. sounddevice.InputStream captures audio in a callback (separate thread).
    2. Audio frames are pushed into an asyncio.Queue bridging the callback → async world.
    3. A silence-detection loop accumulates frames and stops on sustained silence.
    4. The accumulated numpy buffer is fed to faster-whisper for transcription.
"""

import asyncio
import logging
import time
from typing import Optional

import numpy as np
import sounddevice as sd

import config

logger = logging.getLogger("nexus.stt")

# ---------------------------------------------------------------------------
# Lazy singleton for the Whisper model (heavy — only load once)
# ---------------------------------------------------------------------------
_model = None


def _get_model():
    """Load the faster-whisper model on first call, then cache it."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "Loading Whisper model '%s' on %s (%s)...",
                config.WHISPER_MODEL,
                config.WHISPER_DEVICE,
                config.WHISPER_COMPUTE_TYPE,
            )
            _model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)
            raise RuntimeError(f"Whisper model failed to load: {exc}") from exc
    return _model


# ---------------------------------------------------------------------------
# Audio recording with silence detection
# ---------------------------------------------------------------------------
async def record_audio() -> Optional[np.ndarray]:
    """
    Record audio from the default microphone until silence is detected.

    Returns:
        A 1-D numpy float32 array at 16 kHz, or None if recording failed.
    """
    loop = asyncio.get_running_loop()
    audio_queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

    def _audio_callback(indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("Audio stream status: %s", status)
        loop.call_soon_threadsafe(audio_queue.put_nowait, indata.copy())

    frames_collected: list[np.ndarray] = []
    silence_start: Optional[float] = None
    recording_start = time.monotonic()

    try:
        stream = sd.InputStream(
            samplerate=config.AUDIO_SAMPLE_RATE,
            channels=config.AUDIO_CHANNELS,
            blocksize=config.AUDIO_BLOCK_SIZE,
            dtype="float32",
            callback=_audio_callback,
        )
        with stream:
            logger.info("🎙️  Recording... speak now.")
            while True:
                try:
                    chunk = await asyncio.wait_for(audio_queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("Audio timeout — no data received.")
                    break

                frames_collected.append(chunk)
                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if rms < config.SILENCE_THRESHOLD:
                    if silence_start is None:
                        silence_start = time.monotonic()
                    elif (time.monotonic() - silence_start) >= config.SILENCE_DURATION:
                        logger.info("Silence detected — stopping recording.")
                        break
                else:
                    silence_start = None

                elapsed = time.monotonic() - recording_start
                if elapsed >= config.MAX_RECORDING_SECONDS:
                    logger.info("Max recording duration reached.")
                    break

    except sd.PortAudioError as exc:
        logger.error("Microphone error: %s", exc)
        return None
    except Exception as exc:
        logger.error("Recording failed: %s", exc)
        return None

    if not frames_collected:
        logger.warning("No audio frames captured.")
        return None

    audio = np.concatenate(frames_collected, axis=0).flatten()
    duration = len(audio) / config.AUDIO_SAMPLE_RATE
    logger.info("Captured %.1f seconds of audio.", duration)
    return audio


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
async def transcribe(audio: np.ndarray) -> str:
    """
    Transcribe a numpy audio array using faster-whisper.

    Args:
        audio: 1-D float32 array at 16 kHz.

    Returns:
        Transcribed text string, or empty string on failure.
    """
    loop = asyncio.get_running_loop()

    def _run_transcription() -> str:
        model = _get_model()
        segments, info = model.transcribe(
            audio,
            language="en",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(text_parts)

    try:
        text = await loop.run_in_executor(None, _run_transcription)
        logger.info("Transcription: %s", text)
        return text
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Convenience: record + transcribe in one call
# ---------------------------------------------------------------------------
async def listen() -> str:
    """Record from the microphone and return the transcribed text."""
    audio = await record_audio()
    if audio is None or len(audio) < config.AUDIO_SAMPLE_RATE * 0.3:
        return ""
    return await transcribe(audio)
