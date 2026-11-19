from datetime import date, datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.knowledge import (
    get_knowledge_processing_state,
    get_knowledge_processing_states_by_entity,
    get_knowledge_processing_states_by_merchant,
    get_knowledge_processing_states_by_type,
)
from app.models.knowledge import KnowledgeProcessingState
from app.models.merchant import Merchant
from app.schemas.knowledge import KnowledgeStatus, KnowledgeType
from app.services.knowledge import (
    generate_knowledge_point_id,
    get_knowledge_state,
    record_knowledge_attempt,
    record_knowledge_failure,
    record_knowledge_success,
)


@pytest.fixture
async def session(db_session):
    yield db_session


@pytest.fixture
async def merchant(session: AsyncSession) -> Merchant:
    merchant = Merchant(
        merchant_name="Knowledge State Test Merchant",
        email=f"knowledge-{uuid.uuid4().hex[:6]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        shopify_store_id=f"knowledge-{uuid.uuid4().hex[:8]}.myshopify.com",
        app_install_status="installed",
    )
    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)
    return merchant


@pytest.mark.asyncio
async def test_knowledge_processing_lifecycle_transitions(session: AsyncSession, merchant: Merchant):
    """
    Test full state transitions: PENDING -> PROCESSING -> SUCCESS.
    Verify watermark advancement, versioning provenance, and last_generated_at.
    """
    point_id = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant.merchant_id)
    watermark_t1 = datetime(2026, 11, 18, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Start generation attempt
    attempt_state = await record_knowledge_attempt(
        session=session,
        point_id=point_id,
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY.value,
        entity_type="merchant",
        entity_id=merchant.merchant_id,
        merchant_id=merchant.merchant_id,
        is_current=True,
    )
    await session.commit()

    assert attempt_state.point_id == point_id
    assert attempt_state.status == KnowledgeStatus.PROCESSING.value
    assert attempt_state.last_attempted_at is not None
    assert attempt_state.retry_count == 0
    assert attempt_state.source_watermark is None

    # 2. Complete generation successfully
    success_t1 = datetime(2026, 11, 18, 10, 0, 5, tzinfo=timezone.utc)
    success_state = await record_knowledge_success(
        session=session,
        point_id=point_id,
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY.value,
        entity_type="merchant",
        entity_id=merchant.merchant_id,
        merchant_id=merchant.merchant_id,
        source_watermark=watermark_t1,
        is_current=True,
        schema_version=1,
        prompt_version="merchant_summary_v1",
        embedding_model="BAAI/bge-large-en-v1.5",
        generated_at=success_t1,
    )
    await session.commit()

    assert success_state.status == KnowledgeStatus.SUCCESS.value
    assert success_state.source_watermark == watermark_t1
    assert success_state.last_generated_at == success_t1
    assert success_state.last_error is None
    assert success_state.schema_version == 1
    assert success_state.prompt_version == "merchant_summary_v1"
    assert success_state.embedding_model == "BAAI/bge-large-en-v1.5"
    assert success_state.retry_count == 0

    # 3. Verify retrieval via get_knowledge_state
    fetched = await get_knowledge_state(session, point_id)
    assert fetched is not None
    assert fetched.point_id == point_id
    assert fetched.status == KnowledgeStatus.SUCCESS.value


@pytest.mark.asyncio
async def test_knowledge_processing_failure_and_recovery(session: AsyncSession, merchant: Merchant):
    """
    Test failure recording: status FAILED, retry_count incremented, error recorded,
    and source_watermark preserved without advancement.
    Then test recovery on subsequent success.
    """
    point_id = generate_knowledge_point_id(KnowledgeType.SHOPPER_BEHAVIOUR, uuid.uuid4())
    shopper_id = uuid.uuid4()
    t_fail = datetime(2026, 11, 18, 11, 0, 0, tzinfo=timezone.utc)

    # 1. Failure attempt 1
    fail_state_1 = await record_knowledge_failure(
        session=session,
        point_id=point_id,
        knowledge_type=KnowledgeType.SHOPPER_BEHAVIOUR.value,
        entity_type="shopper",
        entity_id=shopper_id,
        merchant_id=merchant.merchant_id,
        error_message="Groq API Rate Limit Exceeded",
        is_current=True,
        failed_at=t_fail,
    )
    await session.commit()

    assert fail_state_1.status == KnowledgeStatus.FAILED.value
    assert fail_state_1.retry_count == 1
    assert fail_state_1.last_error == "Groq API Rate Limit Exceeded"
    assert fail_state_1.source_watermark is None
    assert fail_state_1.last_generated_at is None

    # 2. Failure attempt 2 (retry fails)
    fail_state_2 = await record_knowledge_failure(
        session=session,
        point_id=point_id,
        knowledge_type=KnowledgeType.SHOPPER_BEHAVIOUR.value,
        entity_type="shopper",
        entity_id=shopper_id,
        merchant_id=merchant.merchant_id,
        error_message="Timeout connecting to Qdrant",
        is_current=True,
        failed_at=t_fail + timedelta(minutes=5),
    )
    await session.commit()

    assert fail_state_2.status == KnowledgeStatus.FAILED.value
    assert fail_state_2.retry_count == 2
    assert fail_state_2.last_error == "Timeout connecting to Qdrant"
    assert fail_state_2.source_watermark is None

    # 3. Recovery: successful retry
    recovery_watermark = datetime(2026, 11, 18, 11, 10, 0, tzinfo=timezone.utc)
    recovered_state = await record_knowledge_success(
        session=session,
        point_id=point_id,
        knowledge_type=KnowledgeType.SHOPPER_BEHAVIOUR.value,
        entity_type="shopper",
        entity_id=shopper_id,
        merchant_id=merchant.merchant_id,
        source_watermark=recovery_watermark,
        is_current=True,
        schema_version=1,
        embedding_model="BAAI/bge-large-en-v1.5",
        generated_at=recovery_watermark,
    )
    await session.commit()

    assert recovered_state.status == KnowledgeStatus.SUCCESS.value
    assert recovered_state.source_watermark == recovery_watermark
    assert recovered_state.last_error is None
    # Retry count history preserved
    assert recovered_state.retry_count == 2


@pytest.mark.asyncio
async def test_historical_time_bounded_knowledge_state(session: AsyncSession, merchant: Merchant):
    """
    Test historical knowledge state for closed monthly performance periods and platform knowledge.
    Verify period_start, period_end, is_current=False, and nullable entity_id for platform.
    """
    d_start = date(2026, 10, 1)
    d_end = date(2026, 10, 31)

    # 1. Merchant monthly performance
    m_point_id = generate_knowledge_point_id(
        KnowledgeType.MERCHANT_PERFORMANCE,
        entity_id=merchant.merchant_id,
        period_start=d_start,
        period_end=d_end,
    )
    m_state = await record_knowledge_success(
        session=session,
        point_id=m_point_id,
        knowledge_type=KnowledgeType.MERCHANT_PERFORMANCE.value,
        entity_type="merchant",
        entity_id=merchant.merchant_id,
        merchant_id=merchant.merchant_id,
        period_start=d_start,
        period_end=d_end,
        is_current=False,
        source_watermark=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    await session.commit()

    assert m_state.is_current is False
    assert m_state.period_start == d_start
    assert m_state.period_end == d_end

    # 2. Platform monthly performance (entity_id and merchant_id are None)
    p_point_id = generate_knowledge_point_id(
        KnowledgeType.PLATFORM_PERFORMANCE,
        period_start=d_start,
        period_end=d_end,
    )
    p_state = await record_knowledge_success(
        session=session,
        point_id=p_point_id,
        knowledge_type=KnowledgeType.PLATFORM_PERFORMANCE.value,
        entity_type="platform",
        entity_id=None,
        merchant_id=None,
        period_start=d_start,
        period_end=d_end,
        is_current=False,
        source_watermark=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    await session.commit()

    assert p_state.is_current is False
    assert p_state.entity_id is None
    assert p_state.merchant_id is None
    assert p_state.period_start == d_start
    assert p_state.period_end == d_end


@pytest.mark.asyncio
async def test_knowledge_dal_query_primitives(session: AsyncSession, merchant: Merchant):
    """Test DAL lookup primitives by type, entity, and merchant."""
    point_id_1 = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant.merchant_id)
    await record_knowledge_success(
        session=session,
        point_id=point_id_1,
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY.value,
        entity_type="merchant",
        entity_id=merchant.merchant_id,
        merchant_id=merchant.merchant_id,
        source_watermark=datetime.now(timezone.utc),
        is_current=True,
    )

    campaign_id = uuid.uuid4()
    point_id_2 = generate_knowledge_point_id(KnowledgeType.CAMPAIGN_SUMMARY, campaign_id)
    await record_knowledge_failure(
        session=session,
        point_id=point_id_2,
        knowledge_type=KnowledgeType.CAMPAIGN_SUMMARY.value,
        entity_type="campaign",
        entity_id=campaign_id,
        merchant_id=merchant.merchant_id,
        error_message="Campaign not found",
        is_current=True,
    )
    await session.commit()

    # Query by type and status
    success_merchants = await get_knowledge_processing_states_by_type(
        session, KnowledgeType.MERCHANT_SUMMARY.value, status=KnowledgeStatus.SUCCESS.value
    )
    assert any(s.point_id == point_id_1 for s in success_merchants)

    failed_campaigns = await get_knowledge_processing_states_by_type(
        session, KnowledgeType.CAMPAIGN_SUMMARY.value, status=KnowledgeStatus.FAILED.value
    )
    assert any(s.point_id == point_id_2 for s in failed_campaigns)

    # Query by entity
    entity_states = await get_knowledge_processing_states_by_entity(session, "merchant", merchant.merchant_id)
    assert len(entity_states) >= 1
    assert entity_states[0].point_id == point_id_1

    # Query by merchant
    merchant_states = await get_knowledge_processing_states_by_merchant(session, merchant.merchant_id)
    merchant_point_ids = {s.point_id for s in merchant_states}
    assert point_id_1 in merchant_point_ids
    assert point_id_2 in merchant_point_ids
