import pytest

from app.audio import probe_audio, validate_upload
from app.errors import (
    EmptyFileError,
    FileTooLargeError,
    InvalidAudioError,
    UnsupportedFormatError,
)
from app.config import settings


def test_validate_upload_accepts_wav(wav_bytes):
    assert validate_upload("clip.wav", wav_bytes) == ".wav"


def test_validate_upload_rejects_unsupported_extension(wav_bytes):
    with pytest.raises(UnsupportedFormatError):
        validate_upload("clip.txt", wav_bytes)


def test_validate_upload_rejects_empty_file():
    with pytest.raises(EmptyFileError):
        validate_upload("clip.wav", b"")


def test_validate_upload_rejects_large_file(wav_bytes, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    with pytest.raises(FileTooLargeError):
        validate_upload("clip.wav", wav_bytes)


def test_probe_audio_returns_duration(wav_bytes):
    duration = probe_audio(wav_bytes, ".wav")
    assert 0.9 <= duration <= 1.1


def test_probe_audio_rejects_corrupt_data():
    with pytest.raises(InvalidAudioError):
        probe_audio(b"not an audio file", ".wav")
