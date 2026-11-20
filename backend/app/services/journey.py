import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.data_access.journey import (
    delete_shopper_journeys,
    get_journey_source_events,
    get_qualifying_events_for_shopper,
    get_shopper_journey_by_id,
    get_shopper_journeys_by_shopper,
)
from app.data_access.processing_state import record_domain_activity
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.schemas.events.event_types import CampaignEventType, ShopperEventType
from app.services.merchant_journey import (
    generate_merchant_journeys_for_merchant,
    get_merchant_journey,
    get_merchant_journeys_for_merchant,
)


def generate_shopper_journey_id(
    shopper_id: uuid.UUID, source_event_category: str, source_event_id: uuid.UUID
) -> uuid.UUID:
    """
    Generate a stable, deterministic UUIDv5 for a ShopperJourney based on the
    shopper's identity and the canonical source identity of the opening event.
    """
    return uuid.uuid5(shopper_id, f"shopper_journey:{source_event_category}:{source_event_id}")


def generate_shopper_journey_event_id(
    journey_id: uuid.UUID, source_event_category: str, source_event_id: uuid.UUID
) -> uuid.UUID:
    """
    Generate a stable, deterministic UUIDv5 for a ShopperJourneyEvent based on the
    parent journey ID and the canonical source event identity.
    """
    return uuid.uuid5(journey_id, f"event:{source_event_category}:{source_event_id}")


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


async def generate_shopper_journeys_for_shopper(
    session: AsyncSession, shopper_id: uuid.UUID, as_of: datetime | None = None
) -> None:
    """
    Deterministically regenerate all journeys for a shopper.
    If as_of is provided, evaluate open journeys relative to as_of rather than current time.
    """
    eval_time = as_of or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    # 1. Fetch all chronological qualifying events
    raw_events = await get_qualifying_events_for_shopper(session, shopper_id)
    if not raw_events:
        # No eligible events, but we must ensure we delete existing journeys
        await delete_shopper_journeys(session, shopper_id)
        await record_domain_activity(session, "shopper", shopper_id, "journey", eval_time)
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

    generated_at = eval_time

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
            # Start a new journey with a stable deterministic ID
            journey_id = generate_shopper_journey_id(shopper_id, source_category, source_id)
            current_journey = ShopperJourney(
                journey_id=journey_id,
                merchant_id=merchant_id,
                shopper_id=shopper_id,
                started_at=event_timestamp,
                journey_status="OPEN",
                converted=False,
                order_id=None,
                entry_source=None,
                generated_at=generated_at,
            )

        # Append event with a stable deterministic ID
        journey_event_id = generate_shopper_journey_event_id(
            current_journey.journey_id, source_category, source_id
        )
        journey_event = ShopperJourneyEvent(
            journey_event_id=journey_event_id,
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

    # After loop, if there's an open journey, check if the evaluation time exceeds its window
    if current_journey:
        time_elapsed = eval_time - current_journey.started_at
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

    await record_domain_activity(session, "shopper", shopper_id, "journey", eval_time)


async def get_shopper_journeys_for_shopper(
    session: AsyncSession, shopper_id: uuid.UUID, include_events: bool = False
) -> list[ShopperJourney]:
    """Retrieve all shopper journeys for a shopper, optionally including events."""
    return await get_shopper_journeys_by_shopper(session, shopper_id, include_events=include_events)


async def get_shopper_journey(
    session: AsyncSession, journey_id: uuid.UUID, include_events: bool = False
) -> ShopperJourney | None:
    """Retrieve a single shopper journey by ID, optionally including events."""
    return await get_shopper_journey_by_id(session, journey_id, include_events=include_events)


async def get_shopper_journey_interaction_context(
    session: AsyncSession, journey_id: uuid.UUID
) -> dict[str, Any]:
    """
    Extracts deterministic, retrieval-oriented interaction context for a shopper journey
    (products viewed, searches, cart actions, checkout started) from underlying events
    while strictly minimizing data and excluding raw payloads / PII.
    """
    source_events = await get_journey_source_events(session, journey_id)
    products_viewed: list[str] = []
    seen_products: set[str] = set()
    search_queries: list[str] = []
    seen_searches: set[str] = set()
    cart_add_count = 0
    checkout_started = False

    for jevent, payload in source_events:
        payload = payload or {}
        etype = jevent.event_type
        if etype == ShopperEventType.PRODUCT_VIEWED.value:
            pid = payload.get("product_id")
            if pid:
                pid_str = str(pid)
                if pid_str not in seen_products:
                    seen_products.add(pid_str)
                    products_viewed.append(pid_str)
        elif etype == ShopperEventType.PRODUCT_SEARCHED.value:
            q = payload.get("search_query")
            if q and isinstance(q, str):
                q_clean = q.strip()
                if q_clean and q_clean not in seen_searches:
                    seen_searches.add(q_clean)
                    search_queries.append(q_clean)
        elif etype == ShopperEventType.ADD_TO_CART.value:
            cart_add_count += 1
        elif etype == ShopperEventType.CHECKOUT_STARTED.value:
            checkout_started = True

    return {
        "products_viewed": products_viewed,
        "search_queries": search_queries,
        "cart_add_count": cart_add_count,
        "checkout_started": checkout_started,
    }

