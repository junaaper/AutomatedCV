from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/automatedcv"
    frontend_origin: str = "http://localhost:5173"

    jwt_secret: str = "dev-secret-change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 14

    llm_provider: Literal["groq", "gemini", "openrouter", "fake"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    embed_provider: Literal["gemini", "fake"] = "gemini"
    embed_model: str = "gemini-embedding-001"
    embed_dim: int = 768

    turnstile_secret_key: str = "1x0000000000000000000000000000000AA"
    daily_llm_runs_per_user: int = 20

    sentry_dsn: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
