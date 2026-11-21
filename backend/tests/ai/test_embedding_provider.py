import math

import pytest

from app.ai.embedding import (
    EmbeddingConfigurationError,
    FakeEmbeddingProvider,
    FastEmbedProvider,
    get_embedding_provider,
)
from app.config.settings import Settings


@pytest.mark.asyncio
async def test_fake_embedding_provider():
    provider = FakeEmbeddingProvider(dimension=384, model_name="test-fake-model")
    assert provider.dimension == 384
    assert provider.model_name == "test-fake-model"

    # Embed documents
    docs = ["First document text", "Second document text"]
    doc_vectors = await provider.embed_documents(docs)
    assert len(doc_vectors) == 2
    assert len(doc_vectors[0]) == 384
    assert len(doc_vectors[1]) == 384

    # Check normalization: L2 norm of generated vector should be ~1.0
    norm_0 = math.sqrt(sum(x * x for x in doc_vectors[0]))
    assert pytest.approx(norm_0, rel=1e-3) == 1.0

    # Embed query
    query_vector = await provider.embed_query("What is the revenue?")
    assert len(query_vector) == 384
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_fastembed_provider():
    provider = FastEmbedProvider(model_name="BAAI/bge-small-en-v1.5")
    assert provider.dimension == 384
    assert provider.model_name == "BAAI/bge-small-en-v1.5"

    # Test document passage embedding
    doc_vectors = await provider.embed_documents(["Apex Footwear generated $150,000 in revenue with 1,200 orders."])
    assert len(doc_vectors) == 1
    assert len(doc_vectors[0]) == 384

    # FastEmbed BGE vectors are unit-normalized cosine vectors
    norm = math.sqrt(sum(x * x for x in doc_vectors[0]))
    assert pytest.approx(norm, rel=1e-2) == 1.0

    # Test query embedding
    query_vector = await provider.embed_query("Apex Footwear revenue")
    assert len(query_vector) == 384


def test_get_embedding_provider_factory():
    fake_settings = Settings(
        embedding_provider="fake",
        embedding_dimension=128,
        embedding_model="custom-fake",
    )
    fake_provider = get_embedding_provider(fake_settings)
    assert isinstance(fake_provider, FakeEmbeddingProvider)
    assert fake_provider.dimension == 128

    fastembed_settings = Settings(
        embedding_provider="fastembed",
        embedding_model="BAAI/bge-small-en-v1.5",
    )
    fe_provider = get_embedding_provider(fastembed_settings)
    assert isinstance(fe_provider, FastEmbedProvider)
    assert fe_provider.dimension == 384

    invalid_settings = Settings(embedding_provider="unsupported-engine")
    with pytest.raises(EmbeddingConfigurationError) as exc_info:
        get_embedding_provider(invalid_settings)
    assert "Unsupported embedding_provider" in str(exc_info.value)
