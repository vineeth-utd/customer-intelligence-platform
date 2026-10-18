import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.event import ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant
from app.models.processing_state import EntityDomainActivity, EntityProcessingState
from app.models.profile import ShopperProfile
from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import Shopper, ShopperSegment
from app.reference_data.segments import SEGMENT_CATALOG
from app.data_access.segment import (
    count_segment_members,
    get_merchant_segments,
    get_segment_members_paginated,
    get_shopper_segment_memberships,
)
from app.data_access.processing_state import record_domain_activity, get_eligible_entities
from app.scheduler.segment_job import run_shopper_segment_membership_job
from app.services.processing_state import get_eligible_entities_for_target
from app.services.segment import (
    initialize_merchant_segments,
    refresh_all_segments_for_merchant,
    refresh_segment_memberships_for_segment,
    refresh_shopper_segment_membership_callback,
    update_segment_definition,
    get_segments_for_shopper,
    get_members_for_segment,
)
from app.schemas.events.event_types import ShopperEventType


@pytest.fixture
async def session():
    await engine.dispose()
    s = AsyncSessionLocal()
    try:
        await s.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Database unavailable: {exc}")

    yield s
    await s.rollback()
    await s.close()
    await engine.dispose()


@pytest.fixture
async def setup_merchant_and_shoppers(session):
    merchant_id = uuid.uuid4()
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"seg-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Segment Test Store",
        email=f"seg-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )
    session.add(merchant)

    shopper_1 = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="shopper_1@test.com",
    )
    shopper_2 = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="shopper_2@test.com",
    )
    session.add_all([shopper_1, shopper_2])
    await session.commit()

    # Initialize canonical segments
    await initialize_merchant_segments(session, merchant_id)
    await session.commit()

    segments = await get_merchant_segments(session, merchant_id)
    seg_by_name = {s.segment_name: s for s in segments}

    return {
        "merchant_id": merchant_id,
        "shopper_1_id": shopper_1.shopper_id,
        "shopper_2_id": shopper_2.shopper_id,
        "segments": seg_by_name,
    }


@pytest.mark.asyncio
async def test_segment_membership_generation_and_idempotency(session, setup_merchant_and_shoppers):
    ctx = setup_merchant_and_shoppers
    shopper_1_id = ctx["shopper_1_id"]
    merchant_id = ctx["merchant_id"]
    seg_by_name = ctx["segments"]

    now = datetime.now(timezone.utc)

    # Shopper 1 qualifies for "All Active Shoppers" (has recent session)
    # and "High Value Customers" (total_spend >= 500)
    session_event = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_1_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=now - timedelta(days=2),
        payload={},
        source="storefront",
    )
    profile = ShopperProfile(
        shopper_id=shopper_1_id,
        total_orders=5,
        total_spend=650.0,
        average_order_value=130.0,
        wishlist_item_count=0,
        save_for_later_item_count=0,
        campaign_engagement_count=0,
        generated_at=now,
    )
    session.add_all([session_event, profile])
    await session.commit()

    # 1. Run refresh for shopper 1
    await refresh_shopper_segment_membership_callback(session, shopper_1_id)
    await session.commit()

    memberships = await get_segments_for_shopper(session, shopper_1_id)
    member_seg_names = {m.segment.segment_name for m in memberships}
    assert member_seg_names == {"All Active Shoppers", "High Value Customers"}
    assert len(memberships) == 2

    # 2. Idempotency: Run refresh again, verify no duplicates or errors
    await refresh_shopper_segment_membership_callback(session, shopper_1_id)
    await session.commit()

    memberships_repeat = await get_segments_for_shopper(session, shopper_1_id)
    assert len(memberships_repeat) == 2
    assert {m.segment.segment_name for m in memberships_repeat} == member_seg_names


@pytest.mark.asyncio
async def test_segment_membership_revocation_on_conversion(session, setup_merchant_and_shoppers):
    ctx = setup_merchant_and_shoppers
    shopper_2_id = ctx["shopper_2_id"]
    merchant_id = ctx["merchant_id"]
    seg_by_name = ctx["segments"]
    cart_seg = seg_by_name["Cart Abandoners"]

    now = datetime.now(timezone.utc)

    # 1. Create open journey with abandoned cart > 24 hours ago
    journey = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_2_id,
        started_at=now - timedelta(hours=30),
        journey_status="OPEN",
        converted=False,
        generated_at=now,
    )
    cart_event = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=journey.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type=ShopperEventType.ADD_TO_CART.value,
        event_timestamp=now - timedelta(hours=28),
        sequence_number=1,
    )
    session.add_all([journey, cart_event])
    await session.commit()

    # Generate membership
    await refresh_shopper_segment_membership_callback(session, shopper_2_id)
    await session.commit()

    memberships = await get_segments_for_shopper(session, shopper_2_id)
    assert any(m.segment_id == cart_seg.segment_id for m in memberships)

    # 2. Journey converts later -> shopper no longer qualifies as Cart Abandoner
    journey.converted = True
    journey.journey_status = "CONVERTED"
    journey.ended_at = now - timedelta(hours=1)
    await session.commit()

    # Refresh membership
    await refresh_shopper_segment_membership_callback(session, shopper_2_id)
    await session.commit()

    memberships_after = await get_segments_for_shopper(session, shopper_2_id)
    assert not any(m.segment_id == cart_seg.segment_id for m in memberships_after)


@pytest.mark.asyncio
async def test_downstream_invalidation_and_eligibility(session, setup_merchant_and_shoppers):
    ctx = setup_merchant_and_shoppers
    shopper_1_id = ctx["shopper_1_id"]
    t0 = datetime.now(timezone.utc) - timedelta(minutes=10)

    # 1. Initial success state for segment_membership
    init_state = EntityProcessingState(
        entity_type="shopper",
        entity_id=shopper_1_id,
        target_type="segment_membership",
        last_generated_at=t0,
        last_generation_status="SUCCESS",
    )
    session.add(init_state)
    await session.commit()

    # Verify initially not eligible
    eligible = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_1_id not in eligible

    # 2. Downstream profile activity -> makes segment_membership eligible
    t1 = t0 + timedelta(minutes=2)
    await record_domain_activity(session, "shopper", shopper_1_id, "profile", t1)
    await session.commit()

    eligible = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_1_id in eligible

    # Advance watermark to t1
    init_state.last_generated_at = t1
    await session.commit()
    assert shopper_1_id not in await get_eligible_entities_for_target(session, "shopper", "segment_membership")

    # 3. Downstream journey activity -> makes segment_membership eligible
    t2 = t1 + timedelta(minutes=2)
    await record_domain_activity(session, "shopper", shopper_1_id, "journey", t2)
    await session.commit()

    eligible = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_1_id in eligible


@pytest.mark.asyncio
async def test_dal_retrieval_and_pagination(session, setup_merchant_and_shoppers):
    ctx = setup_merchant_and_shoppers
    shopper_1_id = ctx["shopper_1_id"]
    shopper_2_id = ctx["shopper_2_id"]
    seg_by_name = ctx["segments"]
    active_seg = seg_by_name["All Active Shoppers"]

    now = datetime.now(timezone.utc)

    # Add both shoppers as members of active_seg
    m1 = ShopperSegmentMember(segment_id=active_seg.segment_id, shopper_id=shopper_1_id, generated_at=now)
    m2 = ShopperSegmentMember(segment_id=active_seg.segment_id, shopper_id=shopper_2_id, generated_at=now - timedelta(seconds=10))
    session.add_all([m1, m2])
    await session.commit()

    # Test count
    count = await count_segment_members(session, active_seg.segment_id)
    assert count == 2

    # Test pagination
    members_page_1, total = await get_members_for_segment(session, active_seg.segment_id, limit=1, offset=0)
    assert total == 2
    assert len(members_page_1) == 1
    assert members_page_1[0].shopper_id == shopper_1_id
    assert members_page_1[0].shopper.email == "shopper_1@test.com"

    members_page_2, total = await get_members_for_segment(session, active_seg.segment_id, limit=1, offset=1)
    assert total == 2
    assert len(members_page_2) == 1
    assert members_page_2[0].shopper_id == shopper_2_id


@pytest.mark.asyncio
async def test_segment_definition_change_reevaluation(session, setup_merchant_and_shoppers):
    ctx = setup_merchant_and_shoppers
    shopper_1_id = ctx["shopper_1_id"]
    seg_by_name = ctx["segments"]
    high_value_seg = seg_by_name["High Value Customers"]

    now = datetime.now(timezone.utc)

    # Shopper 1 has total_spend = 300
    profile = ShopperProfile(
        shopper_id=shopper_1_id,
        total_orders=3,
        total_spend=300.0,
        average_order_value=100.0,
        wishlist_item_count=0,
        save_for_later_item_count=0,
        campaign_engagement_count=0,
        generated_at=now,
    )
    session.add(profile)
    await session.commit()

    # Shopper does NOT qualify under value=500
    await refresh_segment_memberships_for_segment(session, high_value_seg.segment_id)
    await session.commit()
    count = await count_segment_members(session, high_value_seg.segment_id)
    assert count == 0

    # Merchant lowers threshold to 250 -> definition change triggers immediate reevaluation
    new_def = {"type": "transactional", "metric": "total_spend", "operator": ">=", "value": 250}
    await update_segment_definition(session, high_value_seg.segment_id, new_def)
    await session.commit()

    # Shopper 1 now qualifies and is immediately present in memberships
    count_after = await count_segment_members(session, high_value_seg.segment_id)
    assert count_after == 1
    members = await get_segments_for_shopper(session, shopper_1_id)
    assert any(m.segment_id == high_value_seg.segment_id for m in members)


@pytest.mark.asyncio
async def test_scheduled_job_execution(session, setup_merchant_and_shoppers):
    ctx = setup_merchant_and_shoppers
    shopper_1_id = ctx["shopper_1_id"]
    now = datetime.now(timezone.utc)

    # Invalidate shopper 1 via activity ledger
    await record_domain_activity(session, "shopper", shopper_1_id, "profile", now)
    await session.commit()

    eligible = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_1_id in eligible

    # Run scheduled incremental job
    await run_shopper_segment_membership_job()

    # Verify processing state advanced to SUCCESS
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_type == "shopper",
        EntityProcessingState.entity_id == shopper_1_id,
        EntityProcessingState.target_type == "segment_membership",
    )
    res = await session.execute(stmt)
    state = res.scalar_one_or_none()
    assert state is not None
    assert state.last_generation_status == "SUCCESS"
    assert state.last_generated_at is not None
