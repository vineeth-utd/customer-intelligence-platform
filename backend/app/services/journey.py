import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.data_access.journey import delete_shopper_journeys, get_qualifying_events_for_shopper
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.schemas.events.event_types import CampaignEventType, ShopperEventType
from app.services.merchant_journey import generate_merchant_journeys_for_merchant


def _extract_domain(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        return parsed.netloc or None
    except Exception:
        return None


def _extract_utm_source(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        sources = qs.get("utm_source")
        if sources:
            return sources[0]
        return None
    except Exception:
        return None


def _derive_entry_source(events: list[ShopperJourneyEvent], payload_map: dict[uuid.UUID, dict]) -> str:
    for event in events:
        payload = payload_map.get(event.journey_event_id, {})
        if event.event_type == ShopperEventType.SESSION_STARTED.value:
            referrer = payload.get("referrer")
            if referrer:
                domain = _extract_domain(referrer)
                if domain:
                    return domain
        elif event.event_type in (
            CampaignEventType.EMAIL_CLICKED.value,
            CampaignEventType.SMS_CLICKED.value,
            CampaignEventType.AD_CLICKED.value,
        ):
            url = payload.get("url")
            if url:
                utm = _extract_utm_source(url)
                if utm:
                    return utm
                domain = _extract_domain(url)
                if domain:
                    return domain
    return "direct"


async def generate_shopper_journeys_for_shopper(session: AsyncSession, shopper_id: uuid.UUID) -> None:
    """
    Deterministically regenerate all journeys for a shopper.
    """
    # 1. Fetch all chronological qualifying events
    raw_events = await get_qualifying_events_for_shopper(session, shopper_id)
    if not raw_events:
        # No eligible events, but we must ensure we delete existing journeys
        await delete_shopper_journeys(session, shopper_id)
        return

    # 2. Delete existing journeys for this shopper
    await delete_shopper_journeys(session, shopper_id)

    # 3. Construct journeys
    journeys_to_insert = []
    events_to_insert = []

    max_window = timedelta(days=settings.journey_max_window_days)

    current_journey = None
    current_journey_events = []
    current_payload_map = {}

    generated_at = datetime.now(timezone.utc)

    for row in raw_events:
        source_category, source_id, merchant_id, event_type, event_timestamp, payload = row

        # Ensure event_timestamp is timezone aware for comparison
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)

        # Determine if we need to close the current journey due to window expiration
        if current_journey:
            time_elapsed = event_timestamp - current_journey.started_at
            if time_elapsed > max_window:
                # Close current journey as non_converting
                current_journey.journey_status = "NON_CONVERTING"
                current_journey.ended_at = current_journey_events[-1].event_timestamp
                current_journey.entry_source = _derive_entry_source(current_journey_events, current_payload_map)

                journeys_to_insert.append(current_journey)
                events_to_insert.extend(current_journey_events)

                current_journey = None
                current_journey_events = []
                current_payload_map = {}

        if not current_journey:
            # Start a new journey
            current_journey = ShopperJourney(
                journey_id=uuid.uuid4(),
                merchant_id=merchant_id,
                shopper_id=shopper_id,
                started_at=event_timestamp,
                journey_status="OPEN",
                converted=False,
                order_id=None,
                entry_source=None,
                generated_at=generated_at,
            )

        # Append event
        journey_event = ShopperJourneyEvent(
            journey_event_id=uuid.uuid4(),
            journey_id=current_journey.journey_id,
            source_event_category=source_category,
            source_event_id=source_id,
            event_type=event_type,
            event_timestamp=event_timestamp,
            sequence_number=len(current_journey_events) + 1,
        )
        current_journey_events.append(journey_event)
        current_payload_map[journey_event.journey_event_id] = payload

        # If event is a conversion, close immediately
        if event_type == ShopperEventType.PURCHASE_COMPLETED.value:
            current_journey.journey_status = "CONVERTED"
            current_journey.converted = True
            current_journey.ended_at = event_timestamp

            order_id_str = payload.get("order_id")
            if order_id_str:
                current_journey.order_id = uuid.UUID(order_id_str)

            current_journey.entry_source = _derive_entry_source(current_journey_events, current_payload_map)

            journeys_to_insert.append(current_journey)
            events_to_insert.extend(current_journey_events)

            current_journey = None
            current_journey_events = []
            current_payload_map = {}

    # After loop, if there's an open journey, check if the current time exceeds its window
    if current_journey:
        time_elapsed = generated_at - current_journey.started_at
        if time_elapsed > max_window:
            current_journey.journey_status = "NON_CONVERTING"
            current_journey.ended_at = current_journey_events[-1].event_timestamp
        else:
            current_journey.journey_status = "OPEN"

        current_journey.entry_source = _derive_entry_source(current_journey_events, current_payload_map)
        journeys_to_insert.append(current_journey)
        events_to_insert.extend(current_journey_events)

    # 4. Insert records
    if journeys_to_insert:
        session.add_all(journeys_to_insert)
    if events_to_insert:
        session.add_all(events_to_insert)
