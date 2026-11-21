import pytest

from app.ai.embedding.fake import FakeEmbeddingProvider
from app.services.embedding import embed_knowledge_summary


@pytest.mark.asyncio
async def test_embed_knowledge_summary_success():
    provider = FakeEmbeddingProvider(dimension=384)
    summary_text = "Apex Footwear has 1,200 orders and $150,000 total revenue."

    vector = await embed_knowledge_summary(summary_text, provider=provider)
    assert len(vector) == 384
    assert len(provider.calls) == 1
    assert provider.calls[0]["texts"] == [summary_text]


@pytest.mark.asyncio
async def test_embed_knowledge_summary_rejects_empty():
    provider = FakeEmbeddingProvider(dimension=384)

    with pytest.raises(ValueError, match="empty or whitespace-only"):
        await embed_knowledge_summary("", provider=provider)

    with pytest.raises(ValueError, match="empty or whitespace-only"):
        await embed_knowledge_summary("   ", provider=provider)
