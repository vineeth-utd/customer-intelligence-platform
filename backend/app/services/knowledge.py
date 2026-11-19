from datetime import date, datetime, timezone
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.knowledge import (
    get_knowledge_processing_state,
    upsert_knowledge_processing_state,
)
from app.models.knowledge import KnowledgeProcessingState
from app.schemas.knowledge import KnowledgeStatus, KnowledgeType

# Canonical RFC 4122 namespace for all CIP AI Knowledge Point IDs
CIP_KNOWLEDGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "knowledge.cip")


def generate_knowledge_point_id(
    knowledge_type: str | KnowledgeType,
    entity_id: Optional[uuid.UUID] = None,
    period_start: Optional[date | str] = None,
    period_end: Optional[date | str] = None,
) -> uuid.UUID:
    """
    Generate a deterministic RFC 4122 UUIDv5 point ID for a knowledge item
    matching the canonical CIP AI Knowledge identity rules.
    """
    k_type = knowledge_type.value if isinstance(knowledge_type, KnowledgeType) else knowledge_type

    if k_type == KnowledgeType.MERCHANT_SUMMARY.value:
        if entity_id is None:
            raise ValueError("merchant_summary requires merchant_id")
        name = f"merchant_summary:{entity_id}"
    elif k_type == KnowledgeType.SHOPPER_BEHAVIOUR.value:
        if entity_id is None:
            raise ValueError("shopper_behaviour requires shopper_id")
        name = f"shopper_behaviour:{entity_id}"
    elif k_type == KnowledgeType.SHOPPER_JOURNEY.value:
        if entity_id is None:
            raise ValueError("shopper_journey requires stable journey_id")
        name = f"shopper_journey:{entity_id}"
    elif k_type == KnowledgeType.CAMPAIGN_SUMMARY.value:
        if entity_id is None:
            raise ValueError("campaign_summary requires campaign_id")
        name = f"campaign_summary:{entity_id}"
    elif k_type == KnowledgeType.MERCHANT_PERFORMANCE.value:
        if entity_id is None or period_start is None or period_end is None:
            raise ValueError("merchant_performance requires merchant_id, period_start, and period_end")
        start_str = period_start.isoformat() if isinstance(period_start, date) else str(period_start)
        end_str = period_end.isoformat() if isinstance(period_end, date) else str(period_end)
        name = f"merchant_performance:{entity_id}:{start_str}:{end_str}"
    elif k_type == KnowledgeType.PLATFORM_PERFORMANCE.value:
        if period_start is None or period_end is None:
            raise ValueError("platform_performance requires period_start and period_end")
        start_str = period_start.isoformat() if isinstance(period_start, date) else str(period_start)
        end_str = period_end.isoformat() if isinstance(period_end, date) else str(period_end)
        name = f"platform_performance:{start_str}:{end_str}"
    else:
        raise ValueError(f"Unknown knowledge_type: {knowledge_type}")

    return uuid.uuid5(CIP_KNOWLEDGE_NAMESPACE, name)


async def record_knowledge_attempt(
    session: AsyncSession,
    point_id: uuid.UUID,
    knowledge_type: str,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    is_current: bool = False,
    attempt_time: Optional[datetime] = None,
) -> KnowledgeProcessingState:
    """
    Transition knowledge processing state to PROCESSING and record attempt timestamp.
    Preserves existing watermark and error state if previously present.
    """
    now = attempt_time or datetime.now(timezone.utc)
    existing = await get_knowledge_processing_state(session, point_id)
    retry_count = existing.retry_count if existing else 0
    source_watermark = existing.source_watermark if existing else None

    return await upsert_knowledge_processing_state(
        session,
        point_id=point_id,
        knowledge_type=knowledge_type,
        entity_type=entity_type,
        entity_id=entity_id,
        merchant_id=merchant_id,
        period_start=period_start,
        period_end=period_end,
        is_current=is_current,
        status=KnowledgeStatus.PROCESSING.value,
        retry_count=retry_count,
        last_attempted_at=now,
        source_watermark=source_watermark,
    )


async def record_knowledge_success(
    session: AsyncSession,
    point_id: uuid.UUID,
    knowledge_type: str,
    entity_type: str,
    source_watermark: datetime,
    entity_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    is_current: bool = False,
    schema_version: int = 1,
    prompt_version: Optional[str] = None,
    embedding_model: Optional[str] = None,
    generated_at: Optional[datetime] = None,
) -> KnowledgeProcessingState:
    """
    Record successful generation of a knowledge item.
    Sets status to SUCCESS, advances source_watermark, records last_generated_at and versioning provenance,
    and clears any previous error message.
    """
    now = generated_at or datetime.now(timezone.utc)
    existing = await get_knowledge_processing_state(session, point_id)
    retry_count = existing.retry_count if existing else 0

    return await upsert_knowledge_processing_state(
        session,
        point_id=point_id,
        knowledge_type=knowledge_type,
        entity_type=entity_type,
        entity_id=entity_id,
        merchant_id=merchant_id,
        period_start=period_start,
        period_end=period_end,
        is_current=is_current,
        status=KnowledgeStatus.SUCCESS.value,
        last_error=None,
        retry_count=retry_count,
        last_attempted_at=now,
        source_watermark=source_watermark,
        last_generated_at=now,
        schema_version=schema_version,
        prompt_version=prompt_version,
        embedding_model=embedding_model,
    )


async def record_knowledge_failure(
    session: AsyncSession,
    point_id: uuid.UUID,
    knowledge_type: str,
    entity_type: str,
    error_message: str,
    entity_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    is_current: bool = False,
    failed_at: Optional[datetime] = None,
) -> KnowledgeProcessingState:
    """
    Record failure of a knowledge generation attempt.
    Sets status to FAILED, records error message, increments retry_count, and preserves
    source_watermark without advancing it so subsequent retries remain eligible.
    """
    now = failed_at or datetime.now(timezone.utc)
    existing = await get_knowledge_processing_state(session, point_id)
    retry_count = (existing.retry_count + 1) if existing else 1
    source_watermark = existing.source_watermark if existing else None
    last_generated_at = existing.last_generated_at if existing else None

    return await upsert_knowledge_processing_state(
        session,
        point_id=point_id,
        knowledge_type=knowledge_type,
        entity_type=entity_type,
        entity_id=entity_id,
        merchant_id=merchant_id,
        period_start=period_start,
        period_end=period_end,
        is_current=is_current,
        status=KnowledgeStatus.FAILED.value,
        last_error=error_message,
        retry_count=retry_count,
        last_attempted_at=now,
        source_watermark=source_watermark,
        last_generated_at=last_generated_at,
    )


async def get_knowledge_state(
    session: AsyncSession, point_id: uuid.UUID
) -> Optional[KnowledgeProcessingState]:
    """Retrieve knowledge processing state for a given point ID."""
    return await get_knowledge_processing_state(session, point_id)
