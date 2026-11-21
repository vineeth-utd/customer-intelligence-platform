import hashlib
import math
from typing import Any, Optional

from app.ai.embedding.base import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic fake embedding provider for hermetic testing.
    Produces predictable, normalized float vectors based on text hashing.
    Requires no disk model weights or network access.
    """

    def __init__(
        self,
        dimension: int = 384,
        model_name: str = "fake-bge-model",
    ):
        self._dimension = dimension
        self._model_name = model_name
        self.calls: list[dict[str, Any]] = []

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _generate_vector(self, text: str) -> list[float]:
        """Generate a deterministic unit-normalized float vector of length self._dimension."""
        if not text:
            raw = [0.0] * self._dimension
            raw[0] = 1.0
            return raw

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = []
        for i in range(self._dimension):
            byte_val = digest[i % len(digest)]
            # Pseudo-random float between -1.0 and 1.0
            val = ((byte_val / 255.0) * 2.0) - 1.0 + ((i % 17) * 0.05)
            raw.append(val)

        # Normalize to unit length (L2 norm) for cosine distance compatibility
        norm = math.sqrt(sum(x * x for x in raw))
        if norm > 0:
            return [round(x / norm, 6) for x in raw]
        return [0.0] * self._dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append({"type": "documents", "texts": texts})
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        self.calls.append({"type": "query", "query": query})
        return self._generate_vector(f"query:{query}")
