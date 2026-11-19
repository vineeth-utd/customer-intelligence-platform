from datetime import date, datetime
from typing import Any, Optional
import uuid

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeProcessingState


async def upsert_knowledge_processing_state(
    session: AsyncSession,
    point_id: uuid.UUID,
    knowledge_type: str,
    entity_type: str,
    status: str,
    entity_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    is_current: bool = False,
    last_error: Optional[str] = None,
    retry_count: int = 0,
    last_attempted_at: Optional[datetime] = None,
    source_watermark: Optional[datetime] = None,
    last_generated_at: Optional[datetime] = None,
    schema_version: int = 1,
    prompt_version: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> KnowledgeProcessingState:
    """Upsert a knowledge processing state record keyed deterministically by point_id."""
    insert_values: dict[str, Any] = {
        "point_id": point_id,
        "knowledge_type": knowledge_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "merchant_id": merchant_id,
        "period_start": period_start,
        "period_end": period_end,
        "is_current": is_current,
        "status": status,
        "last_error": last_error,
        "retry_count": retry_count,
        "last_attempted_at": last_attempted_at,
        "source_watermark": source_watermark,
        "last_generated_at": last_generated_at,
        "schema_version": schema_version,
        "prompt_version": prompt_version,
        "embedding_model": embedding_model,
    }

    update_set: dict[str, Any] = {
        "status": status,
        "last_error": last_error,
        "retry_count": retry_count,
        "last_attempted_at": last_attempted_at,
        "source_watermark": source_watermark,
        "last_generated_at": last_generated_at,
        "schema_version": schema_version,
        "prompt_version": prompt_version,
        "embedding_model": embedding_model,
        "is_current": is_current,
    }
    if entity_id is not None:
        update_set["entity_id"] = entity_id
    if merchant_id is not None:
        update_set["merchant_id"] = merchant_id
    if period_start is not None:
        update_set["period_start"] = period_start
    if period_end is not None:
        update_set["period_end"] = period_end

    stmt = (
        pg_insert(KnowledgeProcessingState)
        .values(**insert_values)
        .on_conflict_do_update(
            index_elements=["point_id"],
            set_=update_set,
        )
    )
    await session.execute(stmt)

    fetch_stmt = (
        select(KnowledgeProcessingState)
        .where(KnowledgeProcessingState.point_id == point_id)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(fetch_stmt)
    return result.scalar_one()


async def get_knowledge_processing_state(
    session: AsyncSession, point_id: uuid.UUID
) -> Optional[KnowledgeProcessingState]:
    """Retrieve a single knowledge processing state record by deterministic point_id."""
    stmt = (
        select(KnowledgeProcessingState)
        .where(KnowledgeProcessingState.point_id == point_id)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_knowledge_processing_states_by_type(
    session: AsyncSession,
    knowledge_type: str,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[KnowledgeProcessingState]:
    """Retrieve knowledge processing states filtered by knowledge type and optional status."""
    stmt = select(KnowledgeProcessingState).where(
        KnowledgeProcessingState.knowledge_type == knowledge_type
    )
    if status is not None:
        stmt = stmt.where(KnowledgeProcessingState.status == status)
    stmt = stmt.order_by(KnowledgeProcessingState.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_knowledge_processing_states_by_entity(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
) -> list[KnowledgeProcessingState]:
    """Retrieve all knowledge processing states associated with a specific entity."""
    stmt = (
        select(KnowledgeProcessingState)
        .where(
            and_(
                KnowledgeProcessingState.entity_type == entity_type,
                KnowledgeProcessingState.entity_id == entity_id,
            )
        )
        .order_by(KnowledgeProcessingState.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_knowledge_processing_states_by_merchant(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[KnowledgeProcessingState]:
    """Retrieve knowledge processing states scoped to a specific merchant."""
    stmt = (
        select(KnowledgeProcessingState)
        .where(KnowledgeProcessingState.merchant_id == merchant_id)
        .order_by(KnowledgeProcessingState.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
