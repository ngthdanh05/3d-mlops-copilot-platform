"""Application settings loaded from environment variables / `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator
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
    llm_provider: Literal["fake", "ollama", "gemini"] = "fake"
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_timeout: float = Field(default=120, gt=0, le=600)
    llm_context: int = Field(default=12288, ge=2048)
    offline: bool = True

    @model_validator(mode="after")
    def validate_llm(self) -> Self:
        if self.offline and self.llm_provider == "gemini":
            raise ValueError("Gemini requires OFFLINE=false and LLM_PROVIDER=gemini")
        if self.llm_provider == "gemini" and not self.llm_api_key:
            raise ValueError("Gemini requires LLM_API_KEY")
        if self.llm_provider == "ollama":
            url = urlsplit(self.llm_base_url)
            if (
                url.scheme != "http"
                or url.hostname not in {"localhost", "127.0.0.1", "::1"}
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in {"", "/"}
            ):
                raise ValueError("Ollama requires an HTTP loopback base URL without credentials")
            if not self.llm_model or "cloud" in self.llm_model.lower():
                raise ValueError("Ollama requires a local LLM_MODEL (cloud tags are refused)")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
