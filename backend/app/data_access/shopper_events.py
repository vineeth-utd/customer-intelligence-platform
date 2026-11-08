import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import ShopperEvent
from app.schemas.events.envelope import ShopperEventEnvelope


async def insert_shopper_event(session: AsyncSession, envelope: ShopperEventEnvelope) -> bool:
    """Persist a validated shopper event with its initial (unprocessed) state.

    Uses INSERT ... ON CONFLICT DO NOTHING on the event_id primary key so
    redelivery of an already-persisted event is ordinary idempotent
    behavior rather than exception-driven control flow. Returns True if a
    new row was inserted, False if the event was already persisted.
    """
    stmt = (
        pg_insert(ShopperEvent)
        .values(
            event_id=envelope.event_id,
            merchant_id=envelope.merchant_id,
            shopper_id=envelope.shopper_id,
            session_id=envelope.session_id,
            event_type=envelope.event_type.value,
            event_version=envelope.event_version,
            event_timestamp=envelope.event_timestamp,
            payload=envelope.payload,
            source=envelope.source,
            processed=False,
            processed_at=None,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def get_shopper_event(session: AsyncSession, event_id: uuid.UUID) -> ShopperEvent | None:
    stmt = select(ShopperEvent).where(ShopperEvent.event_id == event_id).execution_options(populate_existing=True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def mark_shopper_event_processed(session: AsyncSession, event_id: uuid.UUID, processed_at: datetime) -> None:
    """Mark a shopper event as successfully processed. Does not commit."""
    stmt = update(ShopperEvent).where(ShopperEvent.event_id == event_id).values(processed=True, processed_at=processed_at)
    await session.execute(stmt)


async def list_shopper_events_paginated(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    shopper_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[ShopperEvent], int]:
    """Retrieve raw events for a shopper under a merchant with optional time bounds and pagination."""
    filters = [
        ShopperEvent.merchant_id == merchant_id,
        ShopperEvent.shopper_id == shopper_id,
    ]
    if start_time is not None:
        filters.append(ShopperEvent.event_timestamp >= start_time)
    if end_time is not None:
        filters.append(ShopperEvent.event_timestamp <= end_time)

    count_stmt = select(func.count(ShopperEvent.event_id)).where(*filters)
    total = await session.scalar(count_stmt)

    stmt = (
        select(ShopperEvent)
        .where(*filters)
        .order_by(ShopperEvent.event_timestamp.desc(), ShopperEvent.event_id.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())
    return items, total or 0
