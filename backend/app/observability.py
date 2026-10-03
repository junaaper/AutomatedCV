"""Optional error monitoring (Sentry) and agent tracing (LangSmith), enabled by env vars."""

import logging
import os

from app.config import Settings

log = logging.getLogger(__name__)


def init_observability(settings: Settings) -> None:
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            send_default_pii=False,  # CVs and postings are personal data; never ship them
        )
        log.info("Sentry enabled")

    if settings.langsmith_tracing and settings.langsmith_api_key:
        # LangChain reads these from the process environment, while pydantic-settings
        # only parsed them from .env, so export them explicitly.
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
        log.info("LangSmith tracing enabled (project %s)", os.environ["LANGSMITH_PROJECT"])
