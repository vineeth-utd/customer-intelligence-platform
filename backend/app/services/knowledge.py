from datetime import date, datetime, timezone
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.knowledge import (
    get_knowledge_processing_state,
    upsert_knowledge_processing_state,
)
from app.models.knowledge import KnowledgeProcessingState
from app.schemas.knowledge import (
    CIP_KNOWLEDGE_NAMESPACE,
    KnowledgeStatus,
    KnowledgeType,
    generate_knowledge_point_id,
)


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
    source_watermark: Optional[datetime] = None,
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
    Sets status to SUCCESS, updates source_watermark (if provided or preserves existing),
    records last_generated_at and versioning provenance, and clears any previous error message.
    """
    now = generated_at or datetime.now(timezone.utc)
    existing = await get_knowledge_processing_state(session, point_id)
    retry_count = existing.retry_count if existing else 0
    watermark_to_set = source_watermark if source_watermark is not None else (existing.source_watermark if existing else None)

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
        source_watermark=watermark_to_set,
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


__all__ = [
    "CIP_KNOWLEDGE_NAMESPACE",
    "generate_knowledge_point_id",
    "get_knowledge_state",
    "record_knowledge_attempt",
    "record_knowledge_failure",
    "record_knowledge_success",
]
