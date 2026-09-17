from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import MerchantEvent
from app.schemas.events.envelope import MerchantEventEnvelope


async def insert_merchant_event(session: AsyncSession, envelope: MerchantEventEnvelope) -> bool:
    """Persist a validated merchant event with its initial (unprocessed) state.

    Uses INSERT ... ON CONFLICT DO NOTHING on the event_id primary key so
    redelivery of an already-persisted event is ordinary idempotent
    behavior rather than exception-driven control flow. Returns True if a
    new row was inserted, False if the event was already persisted.
    """
    stmt = (
        pg_insert(MerchantEvent)
        .values(
            event_id=envelope.event_id,
            merchant_id=envelope.merchant_id,
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
