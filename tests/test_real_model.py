"""Real local-model verification. Run with: pytest -m real_model -o addopts=''"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


@pytest.mark.real_model
@pytest.mark.parametrize(
    "filename,language,keyword",
    [
        ("chinese.wav", "zh", "欢迎"),
        ("english.wav", "en", "welcome"),
    ],
)
def test_real_model_transcribes_sample(filename, language, keyword):
    audio = (SAMPLES_DIR / filename).read_bytes()
    with TestClient(app) as client:
        response = client.post(
            "/api/transcribe",
            data={"language": language},
            files={"file": (filename, audio, "audio/wav")},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["language"] == language
    assert data["duration_seconds"] > 0
    assert data["processing_seconds"] > 0
    assert keyword.lower() in data["text"].lower(), data["text"]
