"""Shared pytest fixtures. No real model or microphone is used by default."""

from __future__ import annotations

import io
import wave

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_asr_service


def make_wav_bytes(duration: float = 1.0, rate: int = 16000) -> bytes:
    """Generate a silent mono PCM WAV in memory."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * int(rate * duration))
    return buffer.getvalue()


class FakeASRService:
    """Deterministic stand-in for the real ASR service."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[bytes, str, str]] = []

    def transcribe(self, data: bytes, suffix: str, language: str) -> tuple[str, float]:
        self.calls.append((data, suffix, language))
        if self.fail:
            raise RuntimeError("simulated model failure")
        texts = {"zh": "你好，这是测试文本。", "en": "Hello, this is a test."}
        return texts[language], 0.01


@pytest.fixture
def wav_bytes() -> bytes:
    return make_wav_bytes()


@pytest.fixture
def fake_service() -> FakeASRService:
    return FakeASRService()


@pytest.fixture
def client(fake_service: FakeASRService):
    app.dependency_overrides[get_asr_service] = lambda: fake_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
