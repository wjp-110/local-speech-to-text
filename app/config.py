"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Runtime settings with sensible CPU-friendly defaults."""

    def __init__(self) -> None:
        self.app_name = "Local Speech to Text"
        self.model_size = os.getenv("ASR_MODEL_SIZE", "small")
        self.model_dir = Path(os.getenv("ASR_MODEL_DIR", "models")).expanduser().resolve()
        self.local_files_only = os.getenv("LOCAL_FILES_ONLY", "0").lower() in {
            "1",
            "true",
            "yes",
        }
        self.device = os.getenv("ASR_DEVICE", "cpu")
        self.compute_type = os.getenv("ASR_COMPUTE_TYPE", "int8")
        self.cpu_threads = int(os.getenv("ASR_CPU_THREADS", "0"))
        self.max_upload_bytes = int(
            os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))
        )
        self.allowed_extensions = {
            ".wav",
            ".webm",
            ".ogg",
            ".mp3",
            ".m4a",
            ".flac",
        }
        self.allowed_languages = {"zh", "en"}
        self.max_record_seconds = 60

    def ensure_model_dir(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
