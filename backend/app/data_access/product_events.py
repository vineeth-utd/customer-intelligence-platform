import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import ProductEvent
from app.schemas.events.envelope import ProductEventEnvelope


async def insert_product_event(session: AsyncSession, envelope: ProductEventEnvelope) -> bool:
    """Persist a validated product event with its initial (unprocessed) state.

    Uses INSERT ... ON CONFLICT DO NOTHING on the event_id primary key so
    redelivery of an already-persisted event is ordinary idempotent
    behavior rather than exception-driven control flow. Returns True if a
    new row was inserted, False if the event was already persisted.
    """
    stmt = (
        pg_insert(ProductEvent)
        .values(
            event_id=envelope.event_id,
            merchant_id=envelope.merchant_id,
            product_id=envelope.product_id,
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


async def get_product_event(session: AsyncSession, event_id: uuid.UUID) -> ProductEvent | None:
    stmt = select(ProductEvent).where(ProductEvent.event_id == event_id).execution_options(populate_existing=True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def mark_product_event_processed(session: AsyncSession, event_id: uuid.UUID, processed_at: datetime) -> None:
    """Mark a product event as successfully processed. Does not commit."""
    stmt = update(ProductEvent).where(ProductEvent.event_id == event_id).values(processed=True, processed_at=processed_at)
    await session.execute(stmt)
