"""Audio validation, duration probing and temporary file helpers."""

from __future__ import annotations

import io
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import av

from app.config import settings
from app.errors import (
    EmptyFileError,
    FileTooLargeError,
    InvalidAudioError,
    MissingFileError,
    UnsupportedFormatError,
)


def validate_upload(filename: str, data: bytes) -> str:
    """Validate the uploaded file and return its lowercase extension."""
    if not filename:
        raise MissingFileError()

    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise UnsupportedFormatError()

    if len(data) == 0:
        raise EmptyFileError()

    if len(data) > settings.max_upload_bytes:
        raise FileTooLargeError()

    return suffix


def probe_audio(data: bytes, suffix: str) -> float:
    """Return the audio duration in seconds using PyAV."""
    del suffix  # PyAV probes from content; suffix is kept for API symmetry.
    try:
        with av.open(io.BytesIO(data)) as container:
            if not container.streams.audio:
                raise InvalidAudioError("No audio stream found in the file.")

            duration = container.duration
            if duration is not None and duration > 0:
                return float(duration) / float(av.time_base)

            total = 0
            for frame in container.decode(audio=0):
                if frame.duration:
                    total += frame.duration
            if total > 0:
                return float(total) / float(av.time_base)
    except InvalidAudioError:
        raise
    except Exception as exc:
        raise InvalidAudioError("Unable to decode the uploaded audio.") from exc

    raise InvalidAudioError("Unable to determine audio duration.")


@contextmanager
def temp_audio_file(data: bytes, suffix: str) -> Iterator[str]:
    """Write bytes to a temporary file with a useful extension."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        yield path
    finally:
        Path(path).unlink(missing_ok=True)
