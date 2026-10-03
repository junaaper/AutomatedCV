from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-secret-change-me-in-production-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/automatedcv"
    # Comma-separated. In production the frontend proxies /api to this service, so the
    # browser sees one origin and CORS mostly doesn't matter; it's kept for direct access.
    frontend_origin: str = "http://localhost:5173"

    jwt_secret: str = _DEV_JWT_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    # The refresh cookie is scoped to <prefix>/auth. Behind the Cloudflare Pages proxy the
    # browser sees /api/auth/..., so production sets COOKIE_PATH_PREFIX=/api.
    cookie_path_prefix: str = ""
    # "lax" works when frontend and API share a site (local dev, or the /api proxy).
    # Set to "none" only if the browser calls the API cross-site directly.
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    llm_provider: Literal["groq", "gemini", "openrouter", "fake"] = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    embed_provider: Literal["gemini", "fake"] = "gemini"
    embed_model: str = "gemini-embedding-001"
    # Read here (not by each SDK from os.environ) so values from .env are honoured too.
    groq_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    max_revisions: int = 3

    turnstile_secret_key: str = "1x0000000000000000000000000000000AA"
    daily_llm_runs_per_user: int = 20
    demo_daily_llm_runs: int = 3  # live runs only; replayed sample postings are free
    global_daily_llm_runs: int = 500  # protects the shared free-tier API key

    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "automatedcv"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, v: str) -> str:
        # Accept the plain URL Neon/Render show you (postgres:// or postgresql://).
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v.removeprefix(prefix)
        return v

    @model_validator(mode="after")
    def _require_real_secret_in_prod(self) -> "Settings":
        if self.environment == "prod" and (
            self.jwt_secret == _DEV_JWT_SECRET or len(self.jwt_secret) < 32
        ):
            raise ValueError("JWT_SECRET must be set to 32+ random bytes in production")
        return self

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "prod" or self.cookie_samesite == "none"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
