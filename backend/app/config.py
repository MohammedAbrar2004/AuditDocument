from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DOCS_DIR: Path = PROJECT_ROOT / "docs"
    ARTIFACTS_DIR: Path = PROJECT_ROOT / "data" / "artifacts"
    # Per-document upload scope (v2_phase5.md SS2/SS3) -- physically separate from
    # ARTIFACTS_DIR/phase{1,2,3,4}, which stay the untouched reference-corpus fixtures.
    UPLOAD_DIR: Path = PROJECT_ROOT / "data" / "artifacts" / "upload"
    MODEL_DIR: Path = PROJECT_ROOT / "models" / "bge-m3"
    CORS_ORIGINS: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
