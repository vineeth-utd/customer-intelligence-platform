from abc import ABC, abstractmethod


class EmbeddingError(Exception):
    """Base exception for all embedding provider errors."""
    pass


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when an embedding provider is misconfigured or has invalid settings."""
    pass


class EmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.
    Supports embedding document collections (such as knowledge summaries) as well as
    search queries with canonical retrieval prompts.
    """

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of document texts (e.g. knowledge summaries) without query instruction prefixes.

        Args:
            texts: List of document strings to embed.

        Returns:
            List of float vectors, each matching self.dimension.
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """
        Embed a single search query, applying any model-specific query instruction prefixes.

        Args:
            query: Query string to embed.

        Returns:
            A single float vector matching self.dimension.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality produced by this model (e.g. 384 for bge-small-en-v1.5)."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Canonical model identifier."""
        pass
