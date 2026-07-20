from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DOCS_DIR: Path = PROJECT_ROOT / "docs"
    ARTIFACTS_DIR: Path = PROJECT_ROOT / "data" / "artifacts"
    MODEL_DIR: Path = PROJECT_ROOT / "models" / "bge-large-en-v1.5"
    CORS_ORIGINS: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
