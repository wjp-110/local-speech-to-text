"""Local ASR service backed by faster-whisper (CTranslate2, CPU)."""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

from app.audio import temp_audio_file
from app.config import settings
from app.errors import ModelError

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:  # pragma: no cover - dependency is installed in normal use
    WhisperModel = None  # type: ignore


class ASRService:
    """Lazy, thread-safe singleton wrapper around the local ASR model."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._lock = Lock()

    def _load_model(self, force_download: bool = False) -> Any:
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            if WhisperModel is None:
                raise ModelError(
                    "faster-whisper is not installed. Run: pip install -r requirements.txt"
                )

            try:
                settings.ensure_model_dir()
                local_only = False if force_download else settings.local_files_only
                logger.info(
                    "Loading ASR model size=%s device=%s compute=%s local_only=%s",
                    settings.model_size,
                    settings.device,
                    settings.compute_type,
                    local_only,
                )
                self._model = WhisperModel(
                    settings.model_size,
                    device=settings.device,
                    compute_type=settings.compute_type,
                    cpu_threads=settings.cpu_threads,
                    download_root=str(settings.model_dir),
                    local_files_only=local_only,
                )
            except Exception as exc:
                logger.exception("Failed to load ASR model")
                raise ModelError(
                    "Failed to load the local ASR model. "
                    "Run scripts/fetch_model.py once with internet access, "
                    "or check ASR_MODEL_SIZE / ASR_MODEL_DIR."
                ) from exc

            return self._model

    def warmup(self, force_download: bool = False) -> None:
        """Load the model ahead of time (used by the fetch script)."""
        self._load_model(force_download=force_download)

    def transcribe(self, data: bytes, suffix: str, language: str) -> tuple[str, float]:
        """Transcribe audio bytes and return (text, processing_seconds)."""
        model = self._load_model()
        started = time.perf_counter()
        try:
            transcribe_kwargs = {
                "language": language,
                "beam_size": 5,
                "condition_on_previous_text": False,
                "vad_filter": False,
            }
            if language == "zh":
                # Encourage Simplified Chinese output for Mandarin transcription.
                transcribe_kwargs["initial_prompt"] = "请用简体中文转写普通话。"

            with temp_audio_file(data, suffix) as path:
                segments, _info = model.transcribe(path, **transcribe_kwargs)
                text = "".join(segment.text for segment in segments).strip()
            return text, time.perf_counter() - started
        except ModelError:
            raise
        except Exception as exc:
            logger.exception("ASR inference failed")
            raise ModelError("Speech recognition failed while processing the audio.") from exc
