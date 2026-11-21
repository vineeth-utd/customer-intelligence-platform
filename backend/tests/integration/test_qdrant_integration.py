import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from app.config.settings import settings
from app.data_access.qdrant import KnowledgeRepository, get_qdrant_client


@pytest.fixture
async def live_qdrant_repository():
    """
    Connects to the real Qdrant service on localhost:6333 if reachable.
    Skips cleanly if Qdrant is not running, ensuring hermetic offline test suites.
    Cleans up the temporary test collection upon completion.
    """
    client = get_qdrant_client()
    test_collection = f"test_knowledge_{uuid.uuid4().hex[:8]}"

    try:
        # Check server health
        await client.get_collections()
    except Exception as exc:
        await client.close()
        pytest.skip(f"Live Qdrant server is not reachable at {settings.qdrant_host}:{settings.qdrant_port}: {exc}")

    repo = KnowledgeRepository(client=client, collection_name=test_collection)
    try:
        yield repo
    finally:
        try:
            await repo.delete_collection()
        except Exception:
            pass
        await client.close()


@pytest.mark.asyncio
async def test_live_qdrant_end_to_end_persistence(live_qdrant_repository: KnowledgeRepository):
    # 1. Initialize collection with 384 dimensions (BGE small)
    await live_qdrant_repository.ensure_collection(vector_size=384)

    # Verify collection exists on live server
    info = await live_qdrant_repository.client.get_collection(live_qdrant_repository.collection_name)
    assert info.config.params.vectors.size == 384

    # 2. Deterministic point upsert
    point_id = str(uuid.uuid4())
    vector = [0.01 * (i % 10) for i in range(384)]
    payload = {
        "point_id": point_id,
        "knowledge_type": "merchant_summary",
        "entity_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "is_current": True,
        "summary": "Integration test merchant summary text on live Qdrant.",
        "access_scope": "merchant",
    }

    await live_qdrant_repository.upsert_knowledge_point(
        point_id=point_id,
        vector=vector,
        payload=payload,
    )

    # 3. Retrieve point from live server
    record = await live_qdrant_repository.get_knowledge_point(point_id)
    assert record is not None
    assert record["point_id"] == point_id
    assert record["payload"]["summary"] == "Integration test merchant summary text on live Qdrant."
    assert record["payload"]["merchant_id"] == payload["merchant_id"]

    # 4. Delete point and verify removal
    deleted = await live_qdrant_repository.delete_knowledge_point(point_id)
    assert deleted is True

    record_after = await live_qdrant_repository.get_knowledge_point(point_id)
    assert record_after is None
