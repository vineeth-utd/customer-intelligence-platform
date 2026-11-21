from typing import Optional

from app.ai.embedding.base import (
    EmbeddingConfigurationError,
    EmbeddingError,
    EmbeddingProvider,
)
from app.ai.embedding.fake import FakeEmbeddingProvider
from app.ai.embedding.fastembed import FastEmbedProvider
from app.config.settings import Settings, settings as global_settings


def get_embedding_provider(settings: Optional[Settings] = None) -> EmbeddingProvider:
    """
    Factory for instantiating the configured EmbeddingProvider.
    Fails fast with EmbeddingConfigurationError if an unsupported provider is configured.
    """
    active_settings = settings or global_settings
    provider_name = active_settings.embedding_provider.lower().strip()

    if provider_name == "fastembed":
        return FastEmbedProvider(model_name=active_settings.embedding_model)
    elif provider_name == "fake":
        return FakeEmbeddingProvider(
            dimension=active_settings.embedding_dimension,
            model_name=active_settings.embedding_model,
        )
    else:
        raise EmbeddingConfigurationError(
            f"Unsupported embedding_provider: '{active_settings.embedding_provider}'. Supported: 'fastembed', 'fake'."
        )


__all__ = [
    "EmbeddingConfigurationError",
    "EmbeddingError",
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "FastEmbedProvider",
    "get_embedding_provider",
]
