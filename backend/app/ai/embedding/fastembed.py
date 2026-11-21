import asyncio
import logging
from typing import Optional

from fastembed import TextEmbedding

from app.ai.embedding.base import EmbeddingError, EmbeddingProvider

logger = logging.getLogger(__name__)


class FastEmbedProvider(EmbeddingProvider):
    """
    Local embedding provider executing BGE models using FastEmbed / ONNX Runtime.
    Wraps synchronous CPU embedding computation in asyncio.to_thread to keep the event loop non-blocking.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        threads: Optional[int] = None,
    ):
        self._model_name = model_name
        self._threads = threads
        self._model: Optional[TextEmbedding] = None
        try:
            self._dimension = TextEmbedding.get_embedding_size(model_name)
        except Exception:
            self._dimension = 384

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            try:
                self._model = TextEmbedding(
                    model_name=self._model_name,
                    threads=self._threads,
                )
            except Exception as exc:
                raise EmbeddingError(f"Failed to initialize FastEmbed model '{self._model_name}': {exc}") from exc
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of document texts (e.g. knowledge summaries) as passages without instruction prefix.
        """
        if not texts:
            return []

        def _run():
            model = self._get_model()
            # passage_embed embeds passages without prefix in BGE v1.5
            embeddings = list(model.passage_embed(texts))
            return [vec.tolist() for vec in embeddings]

        return await asyncio.to_thread(_run)

    async def embed_query(self, query: str) -> list[float]:
        """
        Embed a search query, prepending the canonical retrieval instruction prefix.
        """
        if not query:
            return [0.0] * self._dimension

        def _run():
            model = self._get_model()
            # query_embed applies canonical BGE search instruction prefix
            embeddings = list(model.query_embed(query))
            if not embeddings:
                return [0.0] * self._dimension
            return embeddings[0].tolist()

        return await asyncio.to_thread(_run)
