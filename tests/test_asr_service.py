import pytest

import app.asr as asr_module
from app.errors import ModelError


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeWhisperModel:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append({"path": path, **kwargs})
        return iter([FakeSegment("Hello "), FakeSegment("world")]), None


def test_service_returns_joined_text_and_language(wav_bytes, monkeypatch):
    created = {}

    def factory(*args, **kwargs):
        created["model"] = FakeWhisperModel(*args, **kwargs)
        return created["model"]

    monkeypatch.setattr(asr_module, "WhisperModel", factory)

    service = asr_module.ASRService()
    text, elapsed = service.transcribe(wav_bytes, ".wav", "en")
    model = created["model"]

    assert text == "Hello world"
    assert elapsed >= 0
    assert model.calls[0]["language"] == "en"
    assert model.kwargs["device"] == "cpu"
    assert model.kwargs["compute_type"] == "int8"


def test_chinese_transcription_uses_simplified_prompt(wav_bytes, monkeypatch):
    created = {}

    def factory(*args, **kwargs):
        created["model"] = FakeWhisperModel(*args, **kwargs)
        return created["model"]

    monkeypatch.setattr(asr_module, "WhisperModel", factory)

    service = asr_module.ASRService()
    service.transcribe(wav_bytes, ".wav", "zh")

    assert created["model"].calls[0]["language"] == "zh"
    assert "简体中文" in created["model"].calls[0]["initial_prompt"]


def test_service_wraps_model_load_failure(monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("download failed")

    monkeypatch.setattr(asr_module, "WhisperModel", explode)
    service = asr_module.ASRService()

    with pytest.raises(ModelError):
        service.transcribe(b"data", ".wav", "zh")
