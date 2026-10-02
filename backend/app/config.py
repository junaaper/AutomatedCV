from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-secret-change-me-in-production-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/automatedcv"
    frontend_origin: str = "http://localhost:5173"

    jwt_secret: str = _DEV_JWT_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 14

    llm_provider: Literal["groq", "gemini", "openrouter", "fake"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    embed_provider: Literal["gemini", "fake"] = "gemini"
    embed_model: str = "gemini-embedding-001"

    turnstile_secret_key: str = "1x0000000000000000000000000000000AA"
    daily_llm_runs_per_user: int = 20

    sentry_dsn: str = ""

    @model_validator(mode="after")
    def _require_real_secret_in_prod(self) -> "Settings":
        if self.environment == "prod" and (
            self.jwt_secret == _DEV_JWT_SECRET or len(self.jwt_secret) < 32
        ):
            raise ValueError("JWT_SECRET must be set to 32+ random bytes in production")
        return self

    # In prod the frontend (Cloudflare Pages) and API (Render) are different sites, so the
    # refresh cookie must be SameSite=None + Secure. Locally both are on localhost (same site).
    @property
    def cookie_secure(self) -> bool:
        return self.environment == "prod"

    @property
    def cookie_samesite(self) -> Literal["lax", "none"]:
        return "none" if self.environment == "prod" else "lax"


@lru_cache
def get_settings() -> Settings:
    return Settings()
