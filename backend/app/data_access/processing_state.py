import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_state import EntityProcessingState


async def upsert_processing_state(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    target_type: str,
    status: str,
    error: str | None = None
) -> None:
    """Upsert a processing state record without updating last_generated_at."""
    stmt = (
        pg_insert(EntityProcessingState)
        .values(
            entity_type=entity_type,
            entity_id=entity_id,
            target_type=target_type,
            last_generation_status=status,
            last_error=error,
        )
        .on_conflict_do_update(
            index_elements=["entity_type", "entity_id", "target_type"],
            set_={
                "last_generation_status": status,
                "last_error": error,
            }
        )
    )
    await session.execute(stmt)


async def mark_processing_success(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    target_type: str,
    generated_at: datetime,
) -> None:
    """Update processing state upon successful generation, advancing last_generated_at."""
    stmt = (
        pg_insert(EntityProcessingState)
        .values(
            entity_type=entity_type,
            entity_id=entity_id,
            target_type=target_type,
            last_generated_at=generated_at,
            last_generation_status="SUCCESS",
            last_error=None,
        )
        .on_conflict_do_update(
            index_elements=["entity_type", "entity_id", "target_type"],
            set_={
                "last_generated_at": generated_at,
                "last_generation_status": "SUCCESS",
                "last_error": None,
            }
        )
    )
    await session.execute(stmt)
