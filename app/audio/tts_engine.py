"""Offline Text-to-Speech (TTS) engine with priority queuing and cooldown suppression."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
from typing import Any

from app.core.config import get_config
from app.core.logging import get_logger

logger = get_logger("app.audio.tts")


class TTSEngine:
    """Threaded offline speech synthesizer with priority preemption and anti-spam suppression."""

    def __init__(self) -> None:
        self._queue: queue.PriorityQueue[tuple[int, float, str]] = queue.PriorityQueue()
        self._is_running = False
        self._worker_thread: threading.Thread | None = None
        self._last_spoken_text = ""
        self._last_spoken_time = 0.0
        self._lock = threading.Lock()
        self._pyttsx3_engine: Any = None

    def initialize(self) -> bool:
        """Initialize TTS provider and commence worker thread."""
        if self._is_running:
            return True

        cfg = get_config()
        if not cfg.audio.voice_enabled:
            logger.info("Voice alerts disabled in configuration.")
            return True

        # Attempt to initialize pyttsx3
        try:
            import pyttsx3

            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", cfg.audio.rate)
            self._pyttsx3_engine.setProperty("volume", cfg.audio.volume)
            logger.info("pyttsx3 offline speech engine initialized.")
        except Exception as exc:
            logger.warning(
                "pyttsx3 initialization failed, using system CLI fallback", error=str(exc)
            )
            self._pyttsx3_engine = None

        self._is_running = True
        self._worker_thread = threading.Thread(
            target=self._speech_worker, name="TTSWorkerThread", daemon=True
        )
        self._worker_thread.start()
        return True

    @property
    def is_available(self) -> bool:
        """Check whether TTS service is operational."""
        return (
            self._is_running
            or self._pyttsx3_engine is not None
            or sys.platform in ("darwin", "win32")
        )

    def speak(self, text: str, priority: int = 3, force: bool = False) -> bool:
        """Enqueue speech utterance. Lower integer priority takes precedence."""
        if not self._is_running or not text.strip():
            return False

        cfg = get_config()
        if not cfg.audio.voice_enabled:
            return False

        now = time.monotonic()
        clean_text = text.strip()

        with self._lock:
            # Check duplicate suppression and cooldown
            if not force and clean_text == self._last_spoken_text:
                if (now - self._last_spoken_time) < cfg.audio.cooldown_seconds:
                    return False  # Suppress duplicate

        self._queue.put((priority, now, clean_text))
        return True

    def stop(self) -> None:
        """Halt worker thread."""
        self._is_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        self._pyttsx3_engine = None

    def _speech_worker(self) -> None:
        while self._is_running:
            try:
                priority, timestamp, text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            with self._lock:
                self._last_spoken_text = text
                self._last_spoken_time = time.monotonic()

            try:
                if self._pyttsx3_engine is not None:
                    self._pyttsx3_engine.say(text)
                    self._pyttsx3_engine.runAndWait()
                elif sys.platform == "darwin":
                    # macOS native speech command fallback
                    subprocess.run(
                        ["say", text],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif sys.platform == "win32":
                    # Windows PowerShell SAPI fallback
                    ps_cmd = f"Add-Type -AssemblyName System.speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"
                    subprocess.run(
                        ["powershell", "-Command", ps_cmd],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            except Exception as exc:
                logger.error("TTS pronunciation error", text=text, error=str(exc))
            finally:
                self._queue.task_done()


# Global TTS engine singleton
tts_engine = TTSEngine()
