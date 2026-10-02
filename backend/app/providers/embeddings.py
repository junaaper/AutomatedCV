"""Embedding providers, selected by EMBED_PROVIDER so swapping vendors is config-only.

Every provider returns vectors of length EMBED_DIM, the size of the cv_chunks column.
"""

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from pydantic import SecretStr

from app.config import get_settings
from app.cv.models import EMBED_DIM


class Embedder(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_queries(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbedder:
    def __init__(self, model: str, dim: int, api_key: SecretStr | None) -> None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        self._client = GoogleGenerativeAIEmbeddings(
            model=model, output_dimensionality=dim, google_api_key=api_key
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        # One batched call for all requirements instead of one request each (free-tier RPM).
        return await self._client.aembed_documents(texts, task_type="RETRIEVAL_QUERY")


_TOKEN = re.compile(r"[a-z0-9+#]+")


class HashingEmbedder:
    """Deterministic, offline bag-of-words embedder for tests and keyless local dev.

    Each token is hashed into a bucket, so texts sharing words get similar vectors, which
    is enough for retrieval tests to be meaningful without calling an API.
    """

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            vec[bucket] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embed_provider == "gemini":
        return GeminiEmbedder(settings.embed_model, EMBED_DIM, settings.google_api_key)
    return HashingEmbedder(EMBED_DIM)
