import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant
from app.models.shopper import ShopperSegment
from app.reference_data.segments import SEGMENT_CATALOG
from app.services.segment import initialize_merchant_segments
from app.data_access.segment import get_merchant_segments


@pytest.fixture
async def db_session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Database unavailable: {exc}")

    yield session

    # Transaction is typically rolled back in tests, but let's just make sure
    await session.rollback()
    await session.close()


@pytest.mark.asyncio
async def test_segment_initialization_flow(db_session):
    # Setup test merchants
    merchant_id_1 = uuid.uuid4()
    merchant_1 = Merchant(
        merchant_id=merchant_id_1,
        shopify_store_id=f"test-{merchant_id_1}.myshopify.com",
        merchant_name="Test Merchant 1",
        email=f"test-{merchant_id_1}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )
    
    merchant_id_2 = uuid.uuid4()
    merchant_2 = Merchant(
        merchant_id=merchant_id_2,
        shopify_store_id=f"test-{merchant_id_2}.myshopify.com",
        merchant_name="Test Merchant 2",
        email=f"test-{merchant_id_2}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )

    db_session.add_all([merchant_1, merchant_2])
    await db_session.commit()

    # 1. Initial Segment initialization
    await initialize_merchant_segments(db_session, merchant_id_1)
    await db_session.commit()

    segments_1 = await get_merchant_segments(db_session, merchant_id_1)
    assert len(segments_1) == len(SEGMENT_CATALOG)

    # 5. Exact correspondence with canonical reference definitions
    catalog_dict = {entry.segment_name: entry.segment_definition for entry in SEGMENT_CATALOG}
    for seg in segments_1:
        assert seg.segment_name in catalog_dict
        assert seg.segment_definition == catalog_dict[seg.segment_name]

    # 3. Merchant isolation (merchant 2 has no segments yet)
    segments_2 = await get_merchant_segments(db_session, merchant_id_2)
    assert len(segments_2) == 0

    # 2. Idempotent repeated initialization
    await initialize_merchant_segments(db_session, merchant_id_1)
    await db_session.commit()

    segments_1_after = await get_merchant_segments(db_session, merchant_id_1)
    assert len(segments_1_after) == len(SEGMENT_CATALOG)

    # Modify one to prove it gets updated back to canonical
    first_segment = segments_1_after[0]
    first_segment.segment_definition = {"type": "bogus"}
    await db_session.commit()

    await initialize_merchant_segments(db_session, merchant_id_1)
    await db_session.commit()

    segments_1_final = await get_merchant_segments(db_session, merchant_id_1)
    for seg in segments_1_final:
        assert seg.segment_definition == catalog_dict[seg.segment_name]

    # Cleanup handled by caller or fixture
