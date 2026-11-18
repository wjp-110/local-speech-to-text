"""Domain errors and their HTTP status mappings."""


class AppError(Exception):
    status_code = 500
    detail = "Internal server error."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class InvalidLanguageError(AppError):
    status_code = 400
    detail = "Unsupported language. Use 'zh' or 'en'."


class MissingFileError(AppError):
    status_code = 400
    detail = "No audio file was provided."


class EmptyFileError(AppError):
    status_code = 400
    detail = "The uploaded file is empty."


class InvalidAudioError(AppError):
    status_code = 400
    detail = "The uploaded file is not a valid audio file."


class UnsupportedFormatError(AppError):
    status_code = 415
    detail = "Unsupported audio format."


class FileTooLargeError(AppError):
    status_code = 413
    detail = "Audio file is too large (limit is 10 MB)."


class ModelError(AppError):
    status_code = 500
    detail = "ASR model is unavailable. Please try again later."
