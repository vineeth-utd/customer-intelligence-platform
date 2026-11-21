from datetime import datetime, timezone
import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from app.data_access.qdrant import (
    KnowledgeRepository,
    KnowledgeRepositoryDimensionMismatchError,
)
from app.schemas.knowledge import KnowledgeQdrantPayload, KnowledgeType
from app.services.knowledge import generate_knowledge_point_id


@pytest.fixture
async def memory_repository():
    """Provides a hermetic in-memory Qdrant knowledge repository for testing."""
    client = AsyncQdrantClient(location=":memory:")
    repo = KnowledgeRepository(client=client, collection_name="test_knowledge")
    yield repo
    await client.close()


@pytest.mark.asyncio
async def test_ensure_collection_lifecycle_and_idempotency(memory_repository: KnowledgeRepository):
    # Initial creation
    await memory_repository.ensure_collection(vector_size=384)
    info = await memory_repository.client.get_collection(memory_repository.collection_name)
    assert info.config.params.vectors.size == 384

    # Idempotent re-run
    await memory_repository.ensure_collection(vector_size=384)


@pytest.mark.asyncio
async def test_ensure_collection_fails_on_dimension_mismatch(memory_repository: KnowledgeRepository):
    # Initialize with 384
    await memory_repository.ensure_collection(vector_size=384)

    # Re-initialization with incompatible dimension 768 must fail fast
    with pytest.raises(KnowledgeRepositoryDimensionMismatchError) as exc_info:
        await memory_repository.ensure_collection(vector_size=768)

    assert "has vector dimension 384, but configured dimension is 768" in str(exc_info.value)
    assert "recreation/re-indexing" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upsert_and_retrieve_knowledge_point(memory_repository: KnowledgeRepository):
    await memory_repository.ensure_collection(vector_size=4)

    merchant_id = uuid.uuid4()
    point_id = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, entity_id=merchant_id)

    payload = KnowledgeQdrantPayload(
        point_id=str(point_id),
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY.value,
        entity_type="merchant",
        entity_id=str(merchant_id),
        merchant_id=str(merchant_id),
        as_of=datetime.now(timezone.utc).isoformat(),
        is_current=True,
        summary="Apex Footwear has $150,000 total revenue.",
        access_scope="merchant",
        source_references=[{"source_type": "merchant_profile", "source_reference": {"merchant_id": str(merchant_id)}}],
        generated_at=datetime.now(timezone.utc).isoformat(),
        schema_version=1,
        embedding_model="BAAI/bge-small-en-v1.5",
    )

    vector = [0.1, 0.2, 0.3, 0.4]
    await memory_repository.upsert_knowledge_point(point_id=point_id, vector=vector, payload=payload)

    retrieved = await memory_repository.get_knowledge_point(point_id)
    assert retrieved is not None
    assert retrieved["point_id"] == str(point_id)
    assert retrieved["payload"]["merchant_id"] == str(merchant_id)
    assert retrieved["payload"]["summary"] == "Apex Footwear has $150,000 total revenue."
    assert retrieved["payload"]["is_current"] is True


@pytest.mark.asyncio
async def test_current_state_knowledge_overwrites_existing_point(memory_repository: KnowledgeRepository):
    """
    Current-state knowledge items (e.g. merchant summary) overwrite the existing point in place
    when refreshed, preventing obsolete duplicates from lingering in Qdrant.
    """
    await memory_repository.ensure_collection(vector_size=4)

    merchant_id = uuid.uuid4()
    point_id = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, entity_id=merchant_id)

    # Initial current-state upsert
    payload_v1 = KnowledgeQdrantPayload(
        point_id=str(point_id),
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY.value,
        entity_type="merchant",
        entity_id=str(merchant_id),
        merchant_id=str(merchant_id),
        as_of=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        is_current=True,
        summary="Apex Footwear v1 summary.",
        access_scope="merchant",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
    )
    await memory_repository.upsert_knowledge_point(point_id=point_id, vector=[0.1, 0.1, 0.1, 0.1], payload=payload_v1)

    # Updated current-state upsert (e.g. after new merchant activity)
    payload_v2 = KnowledgeQdrantPayload(
        point_id=str(point_id),
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY.value,
        entity_type="merchant",
        entity_id=str(merchant_id),
        merchant_id=str(merchant_id),
        as_of=datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        is_current=True,
        summary="Apex Footwear v2 refreshed summary with higher order volume.",
        access_scope="merchant",
        generated_at=datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
    )
    await memory_repository.upsert_knowledge_point(point_id=point_id, vector=[0.2, 0.2, 0.2, 0.2], payload=payload_v2)

    retrieved = await memory_repository.get_knowledge_point(point_id)
    assert retrieved is not None
    assert retrieved["point_id"] == str(point_id)
    assert retrieved["payload"]["summary"] == "Apex Footwear v2 refreshed summary with higher order volume."
    assert retrieved["payload"]["as_of"] == datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_historical_knowledge_points_are_distinct(memory_repository: KnowledgeRepository):
    """
    Historical knowledge items (e.g. merchant monthly performance scorecards) receive distinct stable point IDs
    and do not collide or overwrite one another.
    """
    await memory_repository.ensure_collection(vector_size=4)

    merchant_id = uuid.uuid4()
    point_jan = generate_knowledge_point_id(
        KnowledgeType.MERCHANT_PERFORMANCE,
        entity_id=merchant_id,
        period_start="2026-01-01",
        period_end="2026-01-31",
    )
    point_feb = generate_knowledge_point_id(
        KnowledgeType.MERCHANT_PERFORMANCE,
        entity_id=merchant_id,
        period_start="2026-02-01",
        period_end="2026-02-28",
    )

    assert point_jan != point_feb

    payload_jan = KnowledgeQdrantPayload(
        point_id=str(point_jan),
        knowledge_type=KnowledgeType.MERCHANT_PERFORMANCE.value,
        entity_type="merchant",
        entity_id=str(merchant_id),
        merchant_id=str(merchant_id),
        as_of="2026-02-01T00:00:00Z",
        period_start="2026-01-01",
        period_end="2026-01-31",
        is_current=False,
        summary="January performance summary.",
        access_scope="merchant",
        generated_at="2026-02-01T01:00:00Z",
    )
    payload_feb = KnowledgeQdrantPayload(
        point_id=str(point_feb),
        knowledge_type=KnowledgeType.MERCHANT_PERFORMANCE.value,
        entity_type="merchant",
        entity_id=str(merchant_id),
        as_of="2026-03-01T00:00:00Z",
        period_start="2026-02-01",
        period_end="2026-02-28",
        is_current=False,
        summary="February performance summary.",
        access_scope="merchant",
        generated_at="2026-03-01T01:00:00Z",
    )

    await memory_repository.upsert_knowledge_point(point_id=point_jan, vector=[0.1, 0.1, 0.1, 0.1], payload=payload_jan)
    await memory_repository.upsert_knowledge_point(point_id=point_feb, vector=[0.2, 0.2, 0.2, 0.2], payload=payload_feb)

    rec_jan = await memory_repository.get_knowledge_point(point_jan)
    rec_feb = await memory_repository.get_knowledge_point(point_feb)

    assert rec_jan is not None and rec_feb is not None
    assert rec_jan["payload"]["summary"] == "January performance summary."
    assert rec_feb["payload"]["summary"] == "February performance summary."


@pytest.mark.asyncio
async def test_delete_knowledge_point(memory_repository: KnowledgeRepository):
    await memory_repository.ensure_collection(vector_size=4)

    point_id = uuid.uuid4()
    await memory_repository.upsert_knowledge_point(
        point_id=point_id,
        vector=[0.1, 0.2, 0.3, 0.4],
        payload={"merchant_id": "test", "is_current": True},
    )

    assert await memory_repository.get_knowledge_point(point_id) is not None

    deleted = await memory_repository.delete_knowledge_point(point_id)
    assert deleted is True

    assert await memory_repository.get_knowledge_point(point_id) is None
