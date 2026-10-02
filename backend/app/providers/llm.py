"""Chat model factory. LLM_PROVIDER + LLM_MODEL select the vendor, so when a free tier
shrinks, switching (e.g. Groq -> OpenRouter free models) is a config change only."""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.config import Settings, get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def build_chat_model(settings: Settings) -> BaseChatModel:
    common = {"temperature": 0.2, "max_retries": 2, "timeout": 60}
    match settings.llm_provider:
        case "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(model=settings.llm_model, api_key=settings.groq_api_key, **common)
        case "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.llm_model, google_api_key=settings.google_api_key, **common
            )
        case "openrouter":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.llm_model,
                base_url=OPENROUTER_BASE_URL,
                api_key=settings.openrouter_api_key,
                **common,
            )
        case "fake":
            from app.providers.fake_llm import OfflineChatModel

            return OfflineChatModel()


@lru_cache
def get_llm() -> BaseChatModel:
    return build_chat_model(get_settings())
