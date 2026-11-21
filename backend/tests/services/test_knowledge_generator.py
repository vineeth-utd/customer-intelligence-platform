from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select

from app.ai.embedding.fake import FakeEmbeddingProvider
from app.ai.llm.base import LLMTransientError
from app.ai.llm.fake import FakeLLMProvider
from app.data_access.knowledge import get_knowledge_processing_state
from app.data_access.qdrant import KnowledgeRepository
from app.models.campaign import Campaign
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant, Subscription, SubscriptionPlan
from app.models.merchant_health import MerchantHealth
from app.models.metrics import MerchantMetricsDaily, PlatformMetricsDaily
from app.models.profile import MerchantProfile, ShopperProfile
from app.models.shopper import Shopper
from app.reference_data.plans import PlanKey
from app.schemas.events.event_types import ShopperEventType
from app.schemas.knowledge import (
    KnowledgeStatus,
    KnowledgeType,
    KnowledgeWorkItem,
)
from app.services.knowledge import generate_knowledge_point_id
from app.services.knowledge_generator import generate_knowledge_item
from app.services.merchant import initialize_reference_data
from tests.database import TestAsyncSessionLocal


@pytest.fixture
async def session(db_session):
    yield db_session


@pytest.fixture
async def sample_merchant(session):
    await initialize_reference_data(session)
    await session.commit()

    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"gen-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Generator Test Store",
        email=f"gen-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=30),
        last_active_at=now_utc,
    )
    session.add(merchant)

    growth_plan = await session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.plan_key == PlanKey.GROWTH.value)
    )
    sub = Subscription(
        merchant_id=merchant_id,
        plan_id=growth_plan.plan_id,
        status="ACTIVE",
        billing_cycle="MONTHLY",
        amount_paid=Decimal("99.00"),
        started_at=now_utc - timedelta(days=30),
        renewal_at=now_utc + timedelta(days=30),
    )
    session.add(sub)

    profile = MerchantProfile(
        merchant_id=merchant_id,
        total_shoppers=100,
        total_products=15,
        total_orders=120,
        total_revenue=Decimal("15000.00"),
        average_order_value=Decimal("125.00"),
        conversion_rate=Decimal("0.05"),
        total_campaigns=2,
        active_campaign_count=1,
        enabled_feature_count=3,
        last_order_at=now_utc - timedelta(days=1),
        last_campaign_at=now_utc - timedelta(days=2),
        generated_at=now_utc,
    )
    session.add(profile)

    health = MerchantHealth(
        merchant_id=merchant_id,
        health_score=75.0,
        health_status="Good",
        churn_risk_score=20.0,
        engagement_score=80.0,
        feature_adoption_score=70.0,
        business_performance_score=75.0,
        calculated_at=now_utc,
    )
    session.add(health)
    await session.commit()
    return merchant


@pytest.fixture
async def in_memory_qdrant():
    client = AsyncQdrantClient(location=":memory:")
    repo = KnowledgeRepository(client=client, collection_name="test_generator_knowledge")
    yield repo
    await client.close()


@pytest.fixture
def fake_llm():
    return FakeLLMProvider(
        responses="Generator Test Store has 15 products, 120 orders, and $15000.00 total revenue."
    )


@pytest.fixture
def fake_embedding():
    return FakeEmbeddingProvider(dimension=384)


@pytest.mark.asyncio
async def test_generate_knowledge_item_merchant_summary_success(
    session, sample_merchant, in_memory_qdrant, fake_llm, fake_embedding
):
    watermark = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    work_item = KnowledgeWorkItem(
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY,
        entity_id=sample_merchant.merchant_id,
        source_watermark=watermark,
    )

    result = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TestAsyncSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=fake_llm,
        embedding_provider=fake_embedding,
    )

    # 1. Assert Result
    assert result.status == KnowledgeStatus.SUCCESS
    assert result.point_id == work_item.point_id
    assert result.source_watermark == watermark
    assert result.summary is not None
    assert "Generator Test Store" in result.summary

    # 2. Assert PostgreSQL state
    async with TestAsyncSessionLocal() as db:
        state = await get_knowledge_processing_state(db, work_item.point_id)
        assert state is not None
        assert state.status == KnowledgeStatus.SUCCESS.value
        assert state.source_watermark == watermark
        assert state.last_error is None
        assert state.schema_version == 1
        assert state.embedding_model == fake_embedding.model_name
        assert state.last_generated_at is not None

    # 3. Assert Qdrant persistence
    q_point = await in_memory_qdrant.get_knowledge_point(work_item.point_id)
    assert q_point is not None
    assert q_point["point_id"] == str(work_item.point_id)
    assert len(q_point["vector"]) == 384
    assert q_point["payload"]["merchant_id"] == str(sample_merchant.merchant_id)
    assert q_point["payload"]["is_current"] is True


@pytest.mark.asyncio
async def test_generate_knowledge_item_historical_platform_performance(
    session, in_memory_qdrant, fake_llm, fake_embedding
):
    # Historical items typically have no upstream activity watermark (source_watermark=None)
    fake_llm.responses = [
        "Platform performance for January 2026: gross revenue was $250000.00 with 1500 total orders."
    ]
    p_start = date(2026, 1, 1)
    p_end = date(2026, 1, 31)

    work_item = KnowledgeWorkItem(
        knowledge_type=KnowledgeType.PLATFORM_PERFORMANCE,
        period_start=p_start,
        period_end=p_end,
        source_watermark=None,
    )

    result = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TestAsyncSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=fake_llm,
        embedding_provider=fake_embedding,
    )

    assert result.status == KnowledgeStatus.SUCCESS
    assert result.source_watermark is None

    async with TestAsyncSessionLocal() as db:
        state = await get_knowledge_processing_state(db, work_item.point_id)
        assert state is not None
        assert state.status == KnowledgeStatus.SUCCESS.value
        assert state.is_current is False
        assert state.period_start == p_start
        assert state.period_end == p_end

    q_point = await in_memory_qdrant.get_knowledge_point(work_item.point_id)
    assert q_point is not None
    assert q_point["payload"]["is_current"] is False


@pytest.mark.asyncio
async def test_generate_knowledge_item_failure_and_idempotent_retry(
    session, sample_merchant, in_memory_qdrant, fake_embedding
):
    """
    Simulate LLM failure: state must transition to FAILED, record last_error, increment retry_count,
    and preserve prior watermark. Subsequent retry with succeeding LLM must idempotently overwrite
    Qdrant point and record SUCCESS.
    """
    failing_llm = FakeLLMProvider(
        failures=LLMTransientError("Groq 429 rate limit exceeded. Retry later.")
    )

    watermark = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    work_item = KnowledgeWorkItem(
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY,
        entity_id=sample_merchant.merchant_id,
        source_watermark=watermark,
    )

    # 1. First execution fails
    result_fail = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TestAsyncSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=failing_llm,
        embedding_provider=fake_embedding,
    )

    assert result_fail.status == KnowledgeStatus.FAILED
    assert "rate limit exceeded" in result_fail.error_message
    assert result_fail.retry_count == 1

    async with TestAsyncSessionLocal() as db:
        state = await get_knowledge_processing_state(db, work_item.point_id)
        assert state is not None
        assert state.status == KnowledgeStatus.FAILED.value
        assert state.retry_count == 1
        assert "rate limit exceeded" in state.last_error

    # Qdrant must not contain this point yet
    assert await in_memory_qdrant.get_knowledge_point(work_item.point_id) is None

    # 2. Second execution succeeds (idempotent retry)
    succeeding_llm = FakeLLMProvider(
        responses="Generator Test Store has 15 products, 120 orders, and $15000.00 total revenue."
    )

    result_retry = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TestAsyncSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=succeeding_llm,
        embedding_provider=fake_embedding,
    )

    assert result_retry.status == KnowledgeStatus.SUCCESS
    assert result_retry.retry_count == 1  # preserved from previous retry attempt

    async with TestAsyncSessionLocal() as db:
        state_after = await get_knowledge_processing_state(db, work_item.point_id)
        assert state_after is not None
        assert state_after.status == KnowledgeStatus.SUCCESS.value
        assert state_after.last_error is None  # cleared on success
        assert state_after.source_watermark == watermark

    # Qdrant now contains the point
    q_point = await in_memory_qdrant.get_knowledge_point(work_item.point_id)
    assert q_point is not None
    assert q_point["payload"]["summary"] == "Generator Test Store has 15 products, 120 orders, and $15000.00 total revenue."


@pytest.mark.asyncio
async def test_generate_knowledge_item_shopper_behaviour_success(
    session, sample_merchant, in_memory_qdrant, fake_embedding
):
    merchant = sample_merchant
    shopper_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant.merchant_id,
        email="gen_shopper@test.com",
        first_seen_at=now_utc - timedelta(days=20),
        last_seen_at=now_utc,
    )
    session.add(shopper)

    profile = ShopperProfile(
        shopper_id=shopper_id,
        total_orders=5,
        total_spend=500.00,
        average_order_value=100.00,
        wishlist_item_count=3,
        save_for_later_item_count=1,
        campaign_engagement_count=8,
        preferred_category="Apparel",
        preferred_size="M",
        last_purchase_at=now_utc - timedelta(days=2),
        generated_at=now_utc,
    )
    session.add(profile)
    await session.commit()

    fake_llm = FakeLLMProvider(
        responses="Shopper has placed 5 orders totaling $500.00 with average order value $100.00."
    )

    work_item = KnowledgeWorkItem(
        knowledge_type=KnowledgeType.SHOPPER_BEHAVIOUR,
        entity_id=shopper_id,
        merchant_id=merchant.merchant_id,
        source_watermark=now_utc,
    )

    result = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TestAsyncSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=fake_llm,
        embedding_provider=fake_embedding,
    )

    assert result.status == KnowledgeStatus.SUCCESS
    assert result.point_id == work_item.point_id
    assert result.source_watermark == now_utc

    q_point = await in_memory_qdrant.get_knowledge_point(work_item.point_id)
    assert q_point is not None
    assert q_point["payload"]["shopper_id"] == str(shopper_id)
    assert q_point["payload"]["merchant_id"] == str(merchant.merchant_id)


@pytest.mark.asyncio
async def test_generate_knowledge_item_transaction_isolation(
    session, sample_merchant, in_memory_qdrant, fake_embedding
):
    """
    Verify that external LLM operations are strictly decoupled from PostgreSQL:
    the database session is not held open during LLM invocation.
    """
    db_session_active = False

    class TrackingSessionLocal:
        def __init__(self):
            self._real_session = None

        async def __aenter__(self):
            nonlocal db_session_active
            db_session_active = True
            self._real_session = TestAsyncSessionLocal()
            return await self._real_session.__aenter__()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            nonlocal db_session_active
            result = await self._real_session.__aexit__(exc_type, exc_val, exc_tb)
            db_session_active = False
            return result

    class VerifyingLLMProvider(FakeLLMProvider):
        async def complete(self, messages, temperature=0.0, max_tokens=512):
            # Assert that no database session is active during LLM computation
            assert not db_session_active, "PostgreSQL transaction/session must not be held during LLM call"
            return await super().complete(messages, temperature, max_tokens)

    verifying_llm = VerifyingLLMProvider(
        responses="Generator Test Store has 15 products, 120 orders, and $15000.00 total revenue."
    )

    work_item = KnowledgeWorkItem(
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY,
        entity_id=sample_merchant.merchant_id,
    )

    result = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TrackingSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=verifying_llm,
        embedding_provider=fake_embedding,
    )

    assert result.status == KnowledgeStatus.SUCCESS
    assert not db_session_active


@pytest.mark.asyncio
async def test_generate_knowledge_item_fails_on_missing_entity(
    session, in_memory_qdrant, fake_llm, fake_embedding
):
    missing_id = uuid.uuid4()
    work_item = KnowledgeWorkItem(
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY,
        entity_id=missing_id,
    )

    result = await generate_knowledge_item(
        work_item=work_item,
        session_factory=TestAsyncSessionLocal,
        qdrant_repo=in_memory_qdrant,
        llm_provider=fake_llm,
        embedding_provider=fake_embedding,
    )

    assert result.status == KnowledgeStatus.FAILED
    assert result.error_message is not None
