from typing import Optional

from app.ai.embedding import get_embedding_provider
from app.ai.embedding.base import EmbeddingProvider


async def embed_knowledge_summary(
    summary: str,
    provider: Optional[EmbeddingProvider] = None,
) -> list[float]:
    """
    Embeds a single generated semantic knowledge summary text using the configured EmbeddingProvider.
    Validates input text and executes document-level passage embedding.
    """
    cleaned = summary.strip() if summary else ""
    if not cleaned:
        raise ValueError("Cannot embed an empty or whitespace-only summary.")

    active_provider = provider or get_embedding_provider()
    vectors = await active_provider.embed_documents([cleaned])
    if not vectors or not vectors[0]:
        raise ValueError("Embedding provider returned empty vector for summary.")
    return vectors[0]
