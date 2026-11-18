from app.config import settings


def post_audio(client, wav_bytes, language="zh", filename="test.wav"):
    return client.post(
        "/api/transcribe",
        data={"language": language},
        files={"file": (filename, wav_bytes, "audio/wav")},
    )


def test_transcribe_chinese_success(client, wav_bytes, fake_service):
    response = post_audio(client, wav_bytes, "zh")
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "你好，这是测试文本。"
    assert data["language"] == "zh"
    assert data["duration_seconds"] >= 1.0
    assert data["processing_seconds"] >= 0
    assert fake_service.calls[0][2] == "zh"


def test_transcribe_english_success(client, wav_bytes, fake_service):
    response = post_audio(client, wav_bytes, "en")
    assert response.status_code == 200
    assert response.json()["text"] == "Hello, this is a test."
    assert fake_service.calls[0][2] == "en"


def test_invalid_language_returns_400(client, wav_bytes):
    response = post_audio(client, wav_bytes, "fr")
    assert response.status_code == 400
    assert "language" in response.json()["detail"].lower()


def test_missing_file_returns_4xx(client):
    response = client.post("/api/transcribe", data={"language": "zh"})
    assert 400 <= response.status_code < 500


def test_empty_file_returns_400(client):
    response = post_audio(client, b"", "zh")
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_corrupt_audio_returns_400(client):
    response = post_audio(client, b"this is not audio", "zh")
    assert response.status_code == 400
    assert "audio" in response.json()["detail"].lower()


def test_unsupported_format_returns_415(client, wav_bytes):
    response = post_audio(client, wav_bytes, "zh", filename="notes.txt")
    assert response.status_code == 415


def test_oversized_file_returns_413(client, wav_bytes, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    response = post_audio(client, wav_bytes, "zh")
    assert response.status_code == 413


def test_model_failure_returns_500(client, wav_bytes, fake_service):
    fake_service.fail = True
    response = post_audio(client, wav_bytes, "zh")
    assert response.status_code == 500
    assert "detail" in response.json()
