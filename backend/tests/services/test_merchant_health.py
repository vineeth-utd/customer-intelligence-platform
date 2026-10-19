import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text, delete

from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant, MerchantFeature, SubscriptionPlan, Subscription, PlatformFeature
from app.models.merchant_health import MerchantHealth
from app.models.profile import MerchantProfile
from app.models.metrics import MerchantMetricsDaily
from app.models.processing_state import EntityDomainActivity, EntityProcessingState
from app.data_access.merchant_health import (
    get_merchant_health,
    list_merchant_health_paginated,
)
from app.data_access.processing_state import record_domain_activity, mark_processing_success
from app.reference_data.plans import PlanKey
from app.scheduler.merchant_health_job import run_merchant_health_job
from app.services.merchant import initialize_reference_data
from app.services.merchant_health import (
    generate_merchant_health_callback,
    get_merchant_health_with_factors,
)
from app.services.processing_state import get_eligible_entities_for_target


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
async def setup_merchant_and_catalog(session):
    # Initialize plan/feature catalog
    await initialize_reference_data(session)
    await session.commit()

    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"health-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Health Test Store",
        email=f"health-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=60),
        last_active_at=now_utc - timedelta(days=2),
    )
    session.add(merchant)

    # Add an active subscription to GROWTH plan
    growth_plan = await session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.plan_key == PlanKey.GROWTH.value)
    )
    assert growth_plan is not None

    subscription = Subscription(
        subscription_id=uuid.uuid4(),
        merchant_id=merchant_id,
        plan_id=growth_plan.plan_id,
        status="active",
        billing_cycle="monthly",
        amount_paid=49.0,
        started_at=now_utc - timedelta(days=30),
    )
    session.add(subscription)

    # Enable 2 features for this merchant
    features = (await session.scalars(select(PlatformFeature).limit(2))).all()
    for feat in features:
        session.add(
            MerchantFeature(
                merchant_id=merchant_id,
                feature_id=feat.feature_id,
                is_enabled=True,
            )
        )

    # Seed daily metrics for recent 14 days and prior 14 days
    for day_offset in range(1, 28):
        m_date = (now_utc - timedelta(days=day_offset)).date()
        daily_metric = MerchantMetricsDaily(
            merchant_id=merchant_id,
            metric_date=m_date,
            order_count=5,
            session_count=100,
            converted_session_count=5,
            revenue=250.0,
            conversion_rate=0.05,
            average_order_value=50.0,
            unique_shoppers=20,
            new_shoppers=5,
            product_view_count=50,
            wishlist_add_count=2,
            save_for_later_count=1,
            add_to_cart_count=10,
            checkout_count=6,
            purchase_count=5,
            platform_login_count=1,
            campaign_created_count=0,
            feature_enable_count=0,
            feature_disable_count=0,
            generated_at=now_utc,
        )
        session.add(daily_metric)

    await session.commit()

    try:
        yield {
            "merchant_id": merchant_id,
            "growth_plan": growth_plan,
            "features": features,
        }
    finally:
        await session.execute(delete(MerchantHealth).where(MerchantHealth.merchant_id == merchant_id))
        await session.execute(delete(MerchantProfile).where(MerchantProfile.merchant_id == merchant_id))
        await session.execute(delete(MerchantMetricsDaily).where(MerchantMetricsDaily.merchant_id == merchant_id))
        await session.execute(delete(MerchantFeature).where(MerchantFeature.merchant_id == merchant_id))
        await session.execute(delete(Subscription).where(Subscription.merchant_id == merchant_id))
        await session.execute(delete(EntityDomainActivity).where(EntityDomainActivity.entity_id == merchant_id))
        await session.execute(delete(EntityProcessingState).where(EntityProcessingState.entity_id == merchant_id))
        await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
        await session.commit()


@pytest.mark.asyncio
async def test_merchant_health_generation_and_idempotency(session, setup_merchant_and_catalog):
    ctx = setup_merchant_and_catalog
    merchant_id = ctx["merchant_id"]
    now_utc = datetime.now(timezone.utc)

    # Initial generation
    await generate_merchant_health_callback(session, merchant_id, now_utc)
    await session.commit()

    health = await get_merchant_health(session, merchant_id)
    assert health is not None
    assert health.merchant_id == merchant_id
    assert 0.0 <= health.health_score <= 100.0
    assert 0.0 <= health.churn_risk_score <= 100.0
    assert float(health.churn_risk_score) == pytest.approx(round(100.0 - float(health.health_score), 2), abs=0.01)
    assert health.health_status in ["HEALTHY", "NEEDS_ATTENTION", "AT_RISK"]
    assert 0.0 <= health.feature_adoption_score <= 100.0
    assert 0.0 <= health.engagement_score <= 100.0
    assert 0.0 <= health.business_performance_score <= 100.0

    # Idempotent re-generation
    await generate_merchant_health_callback(session, merchant_id, now_utc)
    await session.commit()

    updated_health = await get_merchant_health(session, merchant_id)
    assert updated_health is not None
    assert updated_health.health_score == health.health_score
    assert updated_health.churn_risk_score == health.churn_risk_score

    # Confirm only one record exists in DB for this merchant
    records = (
        await session.scalars(select(MerchantHealth).where(MerchantHealth.merchant_id == merchant_id))
    ).all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_merchant_health_downstream_invalidation(session, setup_merchant_and_catalog):
    ctx = setup_merchant_and_catalog
    merchant_id = ctx["merchant_id"]
    now_utc = datetime.now(timezone.utc)

    # 1. Test invalidation via "merchant" domain activity
    await record_domain_activity(session, "merchant", merchant_id, "merchant", now_utc)
    await session.commit()

    eligible = await get_eligible_entities_for_target(
        session, entity_type="merchant", target_type="merchant_health"
    )
    assert merchant_id in eligible

    # Mark as successfully processed
    await mark_processing_success(
        session, "merchant", merchant_id, "merchant_health", now_utc
    )
    await session.commit()

    eligible_after = await get_eligible_entities_for_target(
        session, entity_type="merchant", target_type="merchant_health"
    )
    assert merchant_id not in eligible_after

    # 2. Test invalidation via "profile" domain activity
    later_1 = now_utc + timedelta(minutes=5)
    await record_domain_activity(session, "merchant", merchant_id, "profile", later_1)
    await session.commit()

    eligible_profile = await get_eligible_entities_for_target(
        session, entity_type="merchant", target_type="merchant_health"
    )
    assert merchant_id in eligible_profile

    await mark_processing_success(
        session, "merchant", merchant_id, "merchant_health", later_1
    )
    await session.commit()

    # 3. Test invalidation via "journey" domain activity
    later_2 = now_utc + timedelta(minutes=10)
    await record_domain_activity(session, "merchant", merchant_id, "journey", later_2)
    await session.commit()

    eligible_journey = await get_eligible_entities_for_target(
        session, entity_type="merchant", target_type="merchant_health"
    )
    assert merchant_id in eligible_journey

    await mark_processing_success(
        session, "merchant", merchant_id, "merchant_health", later_2
    )
    await session.commit()

    # 4. Test invalidation via "analytics" domain activity
    later_3 = now_utc + timedelta(minutes=15)
    await record_domain_activity(session, "merchant", merchant_id, "analytics", later_3)
    await session.commit()

    eligible_analytics = await get_eligible_entities_for_target(
        session, entity_type="merchant", target_type="merchant_health"
    )
    assert merchant_id in eligible_analytics


@pytest.mark.asyncio
async def test_merchant_health_dal_and_factors(session, setup_merchant_and_catalog):
    ctx = setup_merchant_and_catalog
    merchant_id = ctx["merchant_id"]
    now_utc = datetime.now(timezone.utc)

    # Generate health
    await generate_merchant_health_callback(session, merchant_id, now_utc)
    await session.commit()

    # Direct DAL retrieval
    health = await get_merchant_health(session, merchant_id)
    assert health is not None
    assert health.merchant_id == merchant_id

    # Retrieval with contributing factors
    health_with_factors = await get_merchant_health_with_factors(session, merchant_id)
    assert health_with_factors is not None
    assert health_with_factors["merchant_id"] == merchant_id
    assert "contributing_factors" in health_with_factors

    factors = health_with_factors["contributing_factors"]
    assert "feature_adoption" in factors
    assert "engagement" in factors
    assert "business_performance" in factors
    assert "subscription" in factors

    # Paginated listing
    paginated_all, total_all = await list_merchant_health_paginated(
        session, limit=1000, offset=0
    )
    assert total_all >= 1
    assert any(h.merchant_id == merchant_id for h in paginated_all)

    # Filter by matching status
    paginated_status, total_status = await list_merchant_health_paginated(
        session, status_filter=health.health_status, limit=1000, offset=0
    )
    assert total_status >= 1
    assert any(h.merchant_id == merchant_id for h in paginated_status)

    # Filter by non-matching status
    other_status = "AT_RISK" if health.health_status != "AT_RISK" else "HEALTHY"
    paginated_other, _ = await list_merchant_health_paginated(
        session, status_filter=other_status, limit=1000, offset=0
    )
    assert not any(h.merchant_id == merchant_id for h in paginated_other)


@pytest.mark.asyncio
async def test_run_merchant_health_job(session, setup_merchant_and_catalog):
    ctx = setup_merchant_and_catalog
    merchant_id = ctx["merchant_id"]
    now_utc = datetime.now(timezone.utc)

    # Record domain activity
    await record_domain_activity(session, "merchant", merchant_id, "merchant", now_utc)
    await session.commit()

    # Run the scheduled job
    await run_merchant_health_job()

    # Check that EntityProcessingState has been updated to SUCCESS
    state = await session.scalar(
        select(EntityProcessingState).where(
            EntityProcessingState.entity_type == "merchant",
            EntityProcessingState.entity_id == merchant_id,
            EntityProcessingState.target_type == "merchant_health",
        )
    )
    assert state is not None
    assert state.last_generation_status == "SUCCESS"

    # Check that MerchantHealth was created
    health = await get_merchant_health(session, merchant_id)
    assert health is not None
