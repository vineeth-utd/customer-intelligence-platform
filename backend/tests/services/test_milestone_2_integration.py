import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.campaign import Campaign
from app.models.journey import MerchantJourney, ShopperJourney
from app.models.merchant import Merchant, MerchantFeature, SubscriptionPlan, Subscription
from app.models.metrics import MerchantMetricsDaily
from app.models.processing_state import EntityDomainActivity, EntityProcessingState
from app.models.product import Product, ProductVariant
from app.models.profile import MerchantProfile, ShopperProfile
from app.models.shopper import Shopper
from app.data_access.processing_state import get_eligible_entities, record_domain_activity
from app.scheduler.incremental import process_incremental_target
from app.scheduler.journey_job import run_shopper_journey_job
from app.scheduler.merchant_journey_job import run_merchant_journey_job
from app.scheduler.profile_job import run_merchant_profile_job, run_shopper_profile_job
from app.schemas.events.envelope import (
    CampaignEventEnvelope,
    MerchantEventEnvelope,
    ProductEventEnvelope,
    ShopperEventEnvelope,
)
from app.schemas.events.event_types import (
    CampaignEventType,
    MerchantEventType,
    ProductEventType,
    ShopperEventType,
)
from app.services.campaign import process_campaign_event
from app.services.journey import (
    get_merchant_journey,
    get_merchant_journeys_for_merchant,
    get_shopper_journey,
    get_shopper_journeys_for_shopper,
)
from app.services.merchant import process_merchant_event
from app.services.processing_state import get_eligible_entities_for_target
from app.services.product import process_product_event
from app.services.profile import get_merchant_profile, get_shopper_profile
from app.services.shopper import process_shopper_event


@pytest.fixture
async def session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")

    yield session
    await session.close()
    await engine.dispose()


@pytest.fixture
async def setup_entities(session: AsyncSession):
    """Setup base merchant, shopper, plan, and product for integration testing."""
    merchant_id = uuid.uuid4()
    merchant = Merchant(
        merchant_id=merchant_id,
        merchant_name="Milestone 2 Integration Store",
        email=f"integration_{merchant_id.hex[:8]}@store.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        shopify_store_id=f"integration-{merchant_id.hex[:8]}.myshopify.com",
        app_install_status="installed",
    )
    session.add(merchant)

    shopper_id = uuid.uuid4()
    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant_id,
        email="shopper_m2@test.com",
    )
    session.add(shopper)

    product_id = uuid.uuid4()
    product = Product(
        product_id=product_id,
        merchant_id=merchant_id,
        product_name="M2 Flagship Jacket",
        category="Apparel",
        status="active",
    )
    session.add(product)

    variant_id = uuid.uuid4()
    variant = ProductVariant(
        variant_id=variant_id,
        product_id=product_id,
        variant_name="Default",
        sku=f"SKU-{variant_id.hex[:6]}",
        price=120.0,
        size="L",
        inventory_quantity=50,
        status="active",
    )
    session.add(variant)

    await session.commit()
    return {
        "merchant_id": merchant_id,
        "shopper_id": shopper_id,
        "product_id": product_id,
        "variant_id": variant_id,
    }


@pytest.mark.asyncio
async def test_cross_domain_invalidation_and_target_eligibility(session: AsyncSession, setup_entities: dict):
    """
    Scenario 1: Verify operational event processing records EntityDomainActivity across all
    source domains (product, order, campaign, merchant, shopper) and properly marks all
    four derived products eligible for generation.
    """
    merchant_id = setup_entities["merchant_id"]
    shopper_id = setup_entities["shopper_id"]
    product_id = setup_entities["product_id"]
    variant_id = setup_entities["variant_id"]
    now = datetime.now(timezone.utc)

    # 1. Product event -> should record (merchant, "product")
    product_envelope = ProductEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        product_id=product_id,
        event_type=ProductEventType.PRODUCT_UPDATED,
        event_version=1,
        event_timestamp=now,
        payload={"changed_values": {"product_name": "Updated Jacket"}},
        source="catalog",
    )
    await process_product_event(session, product_envelope)

    # 2. Merchant lifecycle event -> should record (merchant, "merchant")
    merchant_envelope = MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        event_type=MerchantEventType.APP_INSTALLED,
        event_version=1,
        event_timestamp=now + timedelta(seconds=1),
        payload={"install_channel": "shopify_app_store"},
        source="shopify",
    )
    await process_merchant_event(session, merchant_envelope)

    # 3. Campaign interaction with shopper -> should record (merchant, "campaign") and (shopper, "campaign")
    campaign_id = uuid.uuid4()
    campaign_envelope = CampaignEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        campaign_id=campaign_id,
        shopper_id=shopper_id,
        event_type=CampaignEventType.EMAIL_CLICKED,
        event_version=1,
        event_timestamp=now + timedelta(seconds=2),
        payload={"url": "https://example.com/promo?utm_source=spring_sale"},
        source="email",
    )
    await process_campaign_event(session, campaign_envelope)

    # 4. Shopper purchase completed -> should record (shopper, "order"), (merchant, "order"),
    # (shopper, "shopper"), (merchant, "shopper")
    order_id = uuid.uuid4()
    shopper_envelope = ShopperEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PURCHASE_COMPLETED,
        event_version=1,
        event_timestamp=now + timedelta(seconds=3),
        payload={
            "order_id": str(order_id),
            "currency": "USD",
            "total_amount": 120.0,
            "items": [{"product_id": str(product_id), "variant_id": str(variant_id), "quantity": 1, "unit_price": 120.0}],
        },
        source="storefront",
    )
    await process_shopper_event(session, shopper_envelope)
    await session.commit()

    # Verify domain activities were recorded
    act_stmt = select(EntityDomainActivity.entity_type, EntityDomainActivity.entity_id, EntityDomainActivity.domain)
    res = await session.execute(act_stmt)
    activities = {(r[0], r[1], r[2]) for r in res.all()}

    assert ("merchant", merchant_id, "product") in activities
    assert ("merchant", merchant_id, "merchant") in activities
    assert ("merchant", merchant_id, "campaign") in activities
    assert ("merchant", merchant_id, "order") in activities
    assert ("shopper", shopper_id, "campaign") in activities
    assert ("shopper", shopper_id, "order") in activities
    assert ("shopper", shopper_id, "shopper") in activities

    # Verify all 4 derived products are eligible for generation
    eligible_m_profiles = await get_eligible_entities_for_target(session, "merchant", "merchant_profile")
    assert merchant_id in eligible_m_profiles

    eligible_s_profiles = await get_eligible_entities_for_target(session, "shopper", "shopper_profile")
    assert shopper_id in eligible_s_profiles

    eligible_s_journeys = await get_eligible_entities_for_target(session, "shopper", "shopper_journey")
    assert shopper_id in eligible_s_journeys

    eligible_m_journeys = await get_eligible_entities_for_target(session, "merchant", "merchant_journey")
    assert merchant_id in eligible_m_journeys


@pytest.mark.asyncio
async def test_derived_product_generation_and_downstream_retrieval(session: AsyncSession, setup_entities: dict):
    """
    Scenario 2: Run all four scheduled jobs, verify atomic EntityProcessingState advancement,
    and verify downstream Business Service retrieval capabilities with and without events.
    """
    merchant_id = setup_entities["merchant_id"]
    shopper_id = setup_entities["shopper_id"]
    variant_id = setup_entities["variant_id"]
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Setup events directly to seed state
    from app.models.event import MerchantEvent, ShopperEvent, CampaignEvent
    from app.data_access.order import create_order

    order_id = uuid.uuid4()
    await create_order(
        session=session,
        order_id=order_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        currency="USD",
        total_amount=120.0,
        placed_at=t0,
        completed_at=t0,
    )

    m_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=t0,
        payload={},
        source="shopify",
        processed=True,
    )
    s_event = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PURCHASE_COMPLETED.value,
        event_version=1,
        event_timestamp=t0 + timedelta(minutes=1),
        payload={"order_id": str(order_id)},
        source="storefront",
        processed=True,
    )
    c_event = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        campaign_id=uuid.uuid4(),
        shopper_id=shopper_id,
        event_type=CampaignEventType.EMAIL_CLICKED.value,
        event_version=1,
        event_timestamp=t0 + timedelta(minutes=2),
        payload={},
        source="email",
        processed=True,
    )
    session.add_all([m_event, s_event, c_event])

    # Record domain activities
    await record_domain_activity(session, "merchant", merchant_id, "merchant", t0)
    await record_domain_activity(session, "merchant", merchant_id, "shopper", t0)
    await record_domain_activity(session, "shopper", shopper_id, "shopper", t0)
    await record_domain_activity(session, "shopper", shopper_id, "campaign", t0)
    await session.commit()

    # 1. Run all 4 incremental jobs
    await run_merchant_profile_job()
    await run_shopper_profile_job()
    await run_shopper_journey_job()
    await run_merchant_journey_job()

    # 2. Verify EntityProcessingState for all 4 targets
    state_stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_id.in_([merchant_id, shopper_id])
    )
    res = await session.execute(state_stmt)
    states = {(s.entity_type, s.target_type): s.last_generation_status for s in res.scalars().all()}

    assert states.get(("merchant", "merchant_profile")) == "SUCCESS"
    assert states.get(("shopper", "shopper_profile")) == "SUCCESS"
    assert states.get(("shopper", "shopper_journey")) == "SUCCESS"
    assert states.get(("merchant", "merchant_journey")) == "SUCCESS"

    # 3. Verify downstream retrieval via Business Service capabilities
    # Merchant Profile
    m_profile = await get_merchant_profile(session, merchant_id)
    assert m_profile is not None
    assert m_profile.total_shoppers >= 1
    assert m_profile.total_orders >= 1

    # Shopper Profile
    s_profile = await get_shopper_profile(session, shopper_id)
    assert s_profile is not None
    assert s_profile.total_orders >= 1
    assert s_profile.campaign_engagement_count >= 1

    # Shopper Journeys (with and without events)
    s_journeys_no_events = await get_shopper_journeys_for_shopper(session, shopper_id, include_events=False)
    assert len(s_journeys_no_events) >= 1
    assert s_journeys_no_events[0].converted is True
    assert s_journeys_no_events[0].order_id == order_id

    s_journeys_with_events = await get_shopper_journeys_for_shopper(session, shopper_id, include_events=True)
    assert len(s_journeys_with_events) >= 1
    assert len(s_journeys_with_events[0].events) >= 1

    # Single journey by ID
    single_sj = await get_shopper_journey(session, s_journeys_with_events[0].journey_id, include_events=True)
    assert single_sj is not None
    assert single_sj.journey_id == s_journeys_with_events[0].journey_id

    # Merchant Journeys (with and without events)
    m_journeys_no_events = await get_merchant_journeys_for_merchant(session, merchant_id, include_events=False)
    assert len(m_journeys_no_events) >= 1
    assert m_journeys_no_events[0].journey_status == "OPEN"

    m_journeys_with_events = await get_merchant_journeys_for_merchant(session, merchant_id, include_events=True)
    assert len(m_journeys_with_events) >= 1
    assert len(m_journeys_with_events[0].events) >= 1

    # Single merchant journey by ID
    single_mj = await get_merchant_journey(session, m_journeys_with_events[0].merchant_journey_id, include_events=True)
    assert single_mj is not None
    assert single_mj.merchant_journey_id == m_journeys_with_events[0].merchant_journey_id


@pytest.mark.asyncio
async def test_analytics_to_merchant_profile_dependency_flow(session: AsyncSession, setup_entities: dict):
    """
    Scenario 3: Verify the cross-product dependency flow where daily analytics metrics
    invalidation causes Merchant Profile to become eligible and recalculate conversion rate.
    """
    merchant_id = setup_entities["merchant_id"]
    metric_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    # Initial profile generation
    await run_merchant_profile_job()

    initial_profile = await get_merchant_profile(session, merchant_id)
    assert initial_profile is not None
    initial_conv_rate = float(initial_profile.conversion_rate)

    # Simulate Analytics job output: insert/update MerchantMetricsDaily with 50 sessions and 10 conversions (20%)
    daily_metric = MerchantMetricsDaily(
        merchant_id=merchant_id,
        metric_date=metric_date,
        revenue=120.0,
        order_count=10,
        unique_shoppers=10,
        new_shoppers=5,
        session_count=50,
        converted_session_count=10,
        product_view_count=100,
        wishlist_add_count=10,
        save_for_later_count=5,
        add_to_cart_count=20,
        checkout_count=15,
        purchase_count=10,
        conversion_rate=0.20,
        average_order_value=12.0,
        platform_login_count=1,
        campaign_created_count=0,
        feature_enable_count=0,
        feature_disable_count=0,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(daily_metric)

    # Analytics job records domain activity for domain="analytics"
    analytics_timestamp = datetime.now(timezone.utc)
    await record_domain_activity(session, "merchant", merchant_id, "analytics", analytics_timestamp)
    await session.commit()

    # Merchant Profile should now be eligible due to new analytics activity
    eligible = await get_eligible_entities_for_target(session, "merchant", "merchant_profile")
    assert merchant_id in eligible

    # Execute merchant profile job
    await run_merchant_profile_job()

    # Expire test session cache to see the freshly generated profile from DB
    session.expire_all()

    # Verify updated profile reflects the new conversion rate: 10 / 50 = 0.20
    updated_profile = await get_merchant_profile(session, merchant_id)
    assert updated_profile is not None
    assert float(updated_profile.conversion_rate) == pytest.approx(0.20, abs=1e-4)


@pytest.mark.asyncio
async def test_incremental_processing_safe_failure_and_retry(session: AsyncSession, setup_entities: dict):
    """
    Scenario 4: Verify safe failure, rollback, and non-blocking retry behavior:
    A failing generator does not corrupt state, records FAILED, and stays eligible for next run.
    """
    merchant_id = setup_entities["merchant_id"]
    t = datetime.now(timezone.utc)

    # Record activity to make merchant eligible for a test target
    await record_domain_activity(session, "merchant", merchant_id, "merchant", t)
    await session.commit()

    # Define a failing generator targeting this specific merchant
    async def failing_generator(s: AsyncSession, m_id: uuid.UUID):
        if m_id == merchant_id:
            raise RuntimeError("Simulated transient generator error")

    # Run processor
    await process_incremental_target(
        entity_type="merchant",
        target_type="merchant_journey",
        generator=failing_generator,
        batch_size=100,
    )

    # Verify failure state was committed
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_type == "merchant",
        EntityProcessingState.entity_id == merchant_id,
        EntityProcessingState.target_type == "merchant_journey",
    )
    res = await session.execute(stmt)
    state = res.scalar_one_or_none()
    assert state is not None
    assert state.last_generation_status == "FAILED"
    assert "Simulated transient generator error" in (state.last_error or "")
    assert state.last_generated_at is None

    # Verify entity is STILL eligible for retry on next run
    eligible = await get_eligible_entities_for_target(session, "merchant", "merchant_journey")
    assert merchant_id in eligible
