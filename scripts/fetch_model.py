"""Pre-download the configured ASR model into the local models/ directory."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# This script is explicitly used for the one-time online download.
os.environ["LOCAL_FILES_ONLY"] = "0"

from app.asr import ASRService  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> None:
    print(
        f"Downloading model '{settings.model_size}' to {settings.model_dir} ...",
        flush=True,
    )
    ASRService().warmup(force_download=True)
    print("Model is ready. You can now run the server offline with LOCAL_FILES_ONLY=1.")


if __name__ == "__main__":
    main()
