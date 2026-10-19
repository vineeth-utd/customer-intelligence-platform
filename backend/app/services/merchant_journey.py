import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant_journey import (
    delete_merchant_journeys,
    get_merchant_journey_by_id,
    get_merchant_journeys_by_merchant,
    get_qualifying_events_for_merchant,
)
from app.data_access.processing_state import record_domain_activity
from app.models.journey import MerchantJourney, MerchantJourneyEvent
from app.schemas.events.event_types import MerchantEventType


def _event_sort_key(
    row: tuple[str, uuid.UUID, uuid.UUID, str, datetime, dict],
) -> tuple[datetime, int, uuid.UUID]:
    _, source_id, _, event_type, event_timestamp, _ = row
    if event_timestamp.tzinfo is None:
        event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)

    # Priority tie-breaker when timestamps are identical:
    # 0 = APP_INSTALLED (starts a journey)
    # 1 = intermediate merchant / campaign events
    # 2 = APP_UNINSTALLED (closes a journey)
    if event_type == MerchantEventType.APP_INSTALLED.value:
        priority = 0
    elif event_type == MerchantEventType.APP_UNINSTALLED.value:
        priority = 2
    else:
        priority = 1

    return (event_timestamp, priority, source_id)


async def generate_merchant_journeys_for_merchant(
    session: AsyncSession, merchant_id: uuid.UUID
) -> None:
    """
    Deterministically regenerate all journeys for a merchant.

    Merchant Journeys are bounded by the merchant's platform lifecycle:
    - APP_INSTALLED starts a journey (status = OPEN).
    - APP_UNINSTALLED closes a journey (status = COMPLETED).
    - A subsequent APP_INSTALLED begins a new journey.
    """
    raw_events = await get_qualifying_events_for_merchant(session, merchant_id)
    if not raw_events:
        await delete_merchant_journeys(session, merchant_id)
        await record_domain_activity(session, "merchant", merchant_id, "journey", datetime.now(timezone.utc))
        return

    # Delete existing journeys for this merchant to ensure idempotent full regeneration
    await delete_merchant_journeys(session, merchant_id)

    sorted_events = sorted(raw_events, key=_event_sort_key)

    journeys_to_insert: list[MerchantJourney] = []
    events_to_insert: list[MerchantJourneyEvent] = []

    current_journey: MerchantJourney | None = None
    current_journey_events: list[MerchantJourneyEvent] = []
    generated_at = datetime.now(timezone.utc)

    for row in sorted_events:
        source_category, source_id, _m_id, event_type, event_timestamp, _payload = row

        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)

        if event_type == MerchantEventType.APP_INSTALLED.value:
            # If an existing journey was open, close it cleanly as COMPLETED
            if current_journey is not None:
                current_journey.journey_status = "COMPLETED"
                current_journey.ended_at = (
                    current_journey_events[-1].event_timestamp
                    if current_journey_events
                    else event_timestamp
                )
                journeys_to_insert.append(current_journey)
                events_to_insert.extend(current_journey_events)
                current_journey = None
                current_journey_events = []

            current_journey = MerchantJourney(
                merchant_journey_id=uuid.uuid4(),
                merchant_id=merchant_id,
                started_at=event_timestamp,
                ended_at=None,
                journey_status="OPEN",
                generated_at=generated_at,
            )

            journey_event = MerchantJourneyEvent(
                merchant_journey_event_id=uuid.uuid4(),
                merchant_journey_id=current_journey.merchant_journey_id,
                source_event_category=source_category,
                source_event_id=source_id,
                event_type=event_type,
                event_timestamp=event_timestamp,
                sequence_number=1,
            )
            current_journey_events.append(journey_event)

        else:
            if current_journey is None:
                # Events outside an active install lifecycle do not belong to a journey
                continue

            journey_event = MerchantJourneyEvent(
                merchant_journey_event_id=uuid.uuid4(),
                merchant_journey_id=current_journey.merchant_journey_id,
                source_event_category=source_category,
                source_event_id=source_id,
                event_type=event_type,
                event_timestamp=event_timestamp,
                sequence_number=len(current_journey_events) + 1,
            )
            current_journey_events.append(journey_event)

            if event_type == MerchantEventType.APP_UNINSTALLED.value:
                current_journey.journey_status = "COMPLETED"
                current_journey.ended_at = event_timestamp
                journeys_to_insert.append(current_journey)
                events_to_insert.extend(current_journey_events)
                current_journey = None
                current_journey_events = []

    # If the merchant is currently installed / active, the journey remains OPEN
    if current_journey is not None:
        current_journey.journey_status = "OPEN"
        current_journey.ended_at = None
        journeys_to_insert.append(current_journey)
        events_to_insert.extend(current_journey_events)

    if journeys_to_insert:
        session.add_all(journeys_to_insert)
    if events_to_insert:
        session.add_all(events_to_insert)

    await record_domain_activity(session, "merchant", merchant_id, "journey", generated_at)


async def get_merchant_journeys_for_merchant(
    session: AsyncSession, merchant_id: uuid.UUID, include_events: bool = False
) -> list[MerchantJourney]:
    """Retrieve all merchant journeys for a merchant, optionally including events."""
    return await get_merchant_journeys_by_merchant(session, merchant_id, include_events=include_events)


async def get_merchant_journey(
    session: AsyncSession, merchant_journey_id: uuid.UUID, include_events: bool = False
) -> MerchantJourney | None:
    """Retrieve a single merchant journey by ID, optionally including events."""
    return await get_merchant_journey_by_id(session, merchant_journey_id, include_events=include_events)

