"""Application settings loaded from environment variables / `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "3D-MLOps Copilot API"
    app_version: str = "0.1.0"
    debug: bool = False

    # SQLite database (async driver). Relative paths resolve against backend/.
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'mlops.db').as_posix()}"

    # Frontend dev servers allowed by CORS (Vite: 5173, fallback: 3000).
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # LLM settings (used in Phase 3). Never exposed to the frontend.
    llm_api_key: str | None = None
    llm_model: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
