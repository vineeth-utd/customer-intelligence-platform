"""Tests verifying that daily new_shoppers calculation uses Shopper.first_seen_at.

Verifies:
1. Daily new_shoppers is determined by authoritative first_seen_at rather than created_at.
2. A shopper whose earlier historical event is replayed out-of-order has their acquisition
   date attributed to the true first_seen_at date, without shifting on subsequent events.
3. On dates with activity where first_seen_at is earlier, the shopper is counted as returning
   and active, but new_shoppers remains 0.
4. Analytics range backfill is strictly idempotent.
"""

from datetime import date, datetime, timezone
import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.shopper import upsert_shopper
from app.models.event import ShopperEvent
from app.models.merchant import Merchant
from app.models.metrics import MerchantMetricsDaily
from app.models.shopper import Shopper
from app.scheduler.analytics_job import run_analytics_job
from app.services.analytics import generate_daily_metrics, get_shopper_behavior_analytics


@pytest.fixture
async def merchant(db_session: AsyncSession) -> Merchant:
    merchant_id = uuid.uuid4()
    await db_session.execute(
        pg_insert(Merchant).values(
            merchant_id=merchant_id,
            shopify_store_id=f"store-{merchant_id}",
            merchant_name="FirstSeen Test Merchant",
            email=f"merchant-{merchant_id}@example.com",
            country="US",
            timezone="UTC",
            store_currency="USD",
            app_install_status="installed",
        )
    )
    await db_session.commit()
    return (
        await db_session.execute(select(Merchant).where(Merchant.merchant_id == merchant_id))
    ).scalar_one()


@pytest.mark.asyncio
async def test_new_shoppers_uses_first_seen_at_and_handles_out_of_order_replay(
    db_session: AsyncSession, merchant: Merchant
):
    m_id = merchant.merchant_id
    day1 = date(2026, 9, 1)
    day2 = date(2026, 9, 2)
    day3 = date(2026, 9, 3)

    shopper_a_id = uuid.uuid4()
    shopper_b_id = uuid.uuid4()

    # 1. Day 1: Shopper A appears with their first event
    ts_a_day1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    await upsert_shopper(db_session, m_id, shopper_a_id, ts_a_day1)
    ev_a1 = ShopperEvent(
        event_id=uuid.uuid4(),
        shopper_id=shopper_a_id,
        merchant_id=m_id,
        session_id=uuid.uuid4(),
        event_type="PRODUCT_VIEWED",
        event_version=1,
        event_timestamp=ts_a_day1,
        source="web",
        payload={},
    )
    db_session.add(ev_a1)

    # 2. Day 3: Shopper B initially arrives out-of-order on Day 3
    ts_b_day3 = datetime(2026, 9, 3, 14, 0, 0, tzinfo=timezone.utc)
    await upsert_shopper(db_session, m_id, shopper_b_id, ts_b_day3)
    ev_b3 = ShopperEvent(
        event_id=uuid.uuid4(),
        shopper_id=shopper_b_id,
        merchant_id=m_id,
        session_id=uuid.uuid4(),
        event_type="PURCHASE_COMPLETED",
        event_version=1,
        event_timestamp=ts_b_day3,
        source="web",
        payload={},
    )
    db_session.add(ev_b3)
    await db_session.commit()

    # Generate metrics for Day 1 and Day 3
    await generate_daily_metrics(db_session, day1)
    await generate_daily_metrics(db_session, day3)
    await db_session.commit()

    # Verify Day 1: Shopper A is new
    stmt_d1 = select(MerchantMetricsDaily).where(
        MerchantMetricsDaily.merchant_id == m_id,
        MerchantMetricsDaily.metric_date == day1,
    )
    mm_d1 = (await db_session.execute(stmt_d1)).scalar_one()
    assert mm_d1.new_shoppers == 1
    assert mm_d1.unique_shoppers == 1

    # Verify Day 3 initially: Shopper B is new (prior to replay)
    stmt_d3 = select(MerchantMetricsDaily).where(
        MerchantMetricsDaily.merchant_id == m_id,
        MerchantMetricsDaily.metric_date == day3,
    )
    mm_d3 = (await db_session.execute(stmt_d3)).scalar_one()
    assert mm_d3.new_shoppers == 1
    assert mm_d3.unique_shoppers == 1

    # 3. Day 2: Shopper A returns with another event
    ts_a_day2 = datetime(2026, 9, 2, 11, 0, 0, tzinfo=timezone.utc)
    await upsert_shopper(db_session, m_id, shopper_a_id, ts_a_day2)
    ev_a2 = ShopperEvent(
        event_id=uuid.uuid4(),
        shopper_id=shopper_a_id,
        merchant_id=m_id,
        session_id=uuid.uuid4(),
        event_type="ADD_TO_CART",
        event_version=1,
        event_timestamp=ts_a_day2,
        source="web",
        payload={},
    )
    db_session.add(ev_a2)
    await db_session.commit()

    await generate_daily_metrics(db_session, day2)
    await db_session.commit()

    stmt_d2 = select(MerchantMetricsDaily).where(
        MerchantMetricsDaily.merchant_id == m_id,
        MerchantMetricsDaily.metric_date == day2,
    )
    mm_d2 = (await db_session.execute(stmt_d2)).scalar_one()
    # Shopper A is returning, so new_shoppers must be 0
    assert mm_d2.new_shoppers == 0
    assert mm_d2.unique_shoppers == 1

    # Behavior analytics also verifies returning vs new
    behavior_d2 = await get_shopper_behavior_analytics(db_session, m_id, day2, day2)
    assert behavior_d2 is not None
    assert behavior_d2.new_shoppers == 0
    assert behavior_d2.returning_shoppers == 1
    assert behavior_d2.total_active_shoppers == 1

    # 4. Out-of-order replay: an earlier event for Shopper B on Day 1 is now replayed!
    ts_b_day1 = datetime(2026, 9, 1, 8, 30, 0, tzinfo=timezone.utc)
    # upsert_shopper updates first_seen_at via func.least
    await upsert_shopper(db_session, m_id, shopper_b_id, ts_b_day1)
    ev_b1 = ShopperEvent(
        event_id=uuid.uuid4(),
        shopper_id=shopper_b_id,
        merchant_id=m_id,
        session_id=uuid.uuid4(),
        event_type="PRODUCT_VIEWED",
        event_version=1,
        event_timestamp=ts_b_day1,
        source="web",
        payload={},
    )
    db_session.add(ev_b1)
    await db_session.commit()

    # Recheck Shopper B record: first_seen_at must be Day 1
    shopper_b = (
        await db_session.execute(select(Shopper).where(Shopper.shopper_id == shopper_b_id))
    ).scalar_one()
    assert shopper_b.first_seen_at == ts_b_day1

    # 5. Backfill/re-run daily metrics across the entire range [day1, day3]
    await run_analytics_job(start_date=day1, end_date=day3)

    # Day 1: Both Shopper A and Shopper B are new shoppers
    res_d1 = (await db_session.execute(stmt_d1.execution_options(populate_existing=True))).scalar_one()
    assert res_d1.new_shoppers == 2
    assert res_d1.unique_shoppers == 2

    # Day 2: Shopper A is returning, no other shoppers active
    res_d2 = (await db_session.execute(stmt_d2.execution_options(populate_existing=True))).scalar_one()
    assert res_d2.new_shoppers == 0
    assert res_d2.unique_shoppers == 1

    # Day 3: Shopper B was acquired on Day 1, so on Day 3 new_shoppers must now be 0!
    res_d3 = (await db_session.execute(stmt_d3.execution_options(populate_existing=True))).scalar_one()
    assert res_d3.new_shoppers == 0
    assert res_d3.unique_shoppers == 1

    # 6. Out-of-order replay does not shift acquisition date when later events arrive
    ts_b_day4 = datetime(2026, 9, 4, 15, 0, 0, tzinfo=timezone.utc)
    await upsert_shopper(db_session, m_id, shopper_b_id, ts_b_day4)
    shopper_b_after = (
        await db_session.execute(select(Shopper).where(Shopper.shopper_id == shopper_b_id))
    ).scalar_one()
    assert shopper_b_after.first_seen_at == ts_b_day1

    # 7. Idempotency verification: re-running range backfill gives identical numbers
    await run_analytics_job(start_date=day1, end_date=day3)
    res_d1_second = (await db_session.execute(stmt_d1.execution_options(populate_existing=True))).scalar_one()
    res_d2_second = (await db_session.execute(stmt_d2.execution_options(populate_existing=True))).scalar_one()
    res_d3_second = (await db_session.execute(stmt_d3.execution_options(populate_existing=True))).scalar_one()

    assert res_d1_second.new_shoppers == 2
    assert res_d2_second.new_shoppers == 0
    assert res_d3_second.new_shoppers == 0
