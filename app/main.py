"""FastAPI application: health check, transcription API and static Web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.asr import ASRService
from app.audio import probe_audio, validate_upload
from app.config import settings
from app.errors import AppError, InvalidLanguageError, ModelError
from app.schemas import TranscriptionResponse

app = FastAPI(title=settings.app_name, version="1.0.0")

_asr_service = ASRService()


def get_asr_service() -> ASRService:
    """Dependency override point for tests."""
    return _asr_service


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(...),
    service: ASRService = Depends(get_asr_service),
) -> TranscriptionResponse:
    if language not in settings.allowed_languages:
        raise InvalidLanguageError()

    data = await file.read()
    suffix = validate_upload(file.filename or "", data)
    duration_seconds = probe_audio(data, suffix)
    try:
        text, processing_seconds = service.transcribe(data, suffix, language)
    except AppError:
        raise
    except Exception as exc:
        raise ModelError("Speech recognition failed while processing the audio.") from exc

    return TranscriptionResponse(
        text=text,
        language=language,
        duration_seconds=round(duration_seconds, 3),
        processing_seconds=round(processing_seconds, 3),
    )


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
