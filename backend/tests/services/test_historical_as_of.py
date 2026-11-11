"""Unit tests for historical as-of evaluation across Journeys and Segments."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.schemas.events.event_types import ShopperEventType
from app.services.journey import generate_shopper_journeys_for_shopper
from app.services.merchant_journey import generate_merchant_journeys_for_merchant
from app.services.segment import refresh_shopper_segment_membership_callback


@pytest.mark.asyncio
async def test_shopper_journey_expires_to_non_converting_when_exceeding_window_at_as_of():
    session = AsyncMock()
    shopper_id = uuid.uuid4()
    merchant_id = uuid.uuid4()

    # Journey starts 10 days before as_of (exceeds max window of 7 days)
    as_of = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    t_start = as_of - timedelta(days=10)
    t_view = t_start + timedelta(minutes=15)

    raw_events = [
        ("shopper", uuid.uuid4(), merchant_id, ShopperEventType.SESSION_STARTED.value, t_start, {"referrer": "https://google.com"}),
        ("shopper", uuid.uuid4(), merchant_id, ShopperEventType.PRODUCT_VIEWED.value, t_view, {}),
    ]

    with (
        patch("app.services.journey.get_qualifying_events_for_shopper", return_value=raw_events),
        patch("app.services.journey.delete_shopper_journeys", new_callable=AsyncMock),
        patch("app.services.journey.record_domain_activity", new_callable=AsyncMock) as mock_record,
    ):
        await generate_shopper_journeys_for_shopper(session, shopper_id, as_of=as_of)

        assert session.add_all.called
        journeys = session.add_all.call_args_list[0][0][0]
        assert len(journeys) == 1
        journey = journeys[0]

        # Status must be NON_CONVERTING because 10 days > 7 days as of as_of
        assert journey.journey_status == "NON_CONVERTING"
        assert journey.converted is False
        assert journey.started_at == t_start
        assert journey.ended_at == t_view
        assert journey.generated_at == as_of
        mock_record.assert_called_once_with(session, "shopper", shopper_id, "journey", as_of)


@pytest.mark.asyncio
async def test_shopper_journey_remains_open_when_within_window_at_as_of():
    session = AsyncMock()
    shopper_id = uuid.uuid4()
    merchant_id = uuid.uuid4()

    # Journey starts 2 days before as_of (within 7 days)
    as_of = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    t_start = as_of - timedelta(days=2)
    t_cart = t_start + timedelta(minutes=5)

    raw_events = [
        ("shopper", uuid.uuid4(), merchant_id, ShopperEventType.SESSION_STARTED.value, t_start, {}),
        ("shopper", uuid.uuid4(), merchant_id, ShopperEventType.ADD_TO_CART.value, t_cart, {}),
    ]

    with (
        patch("app.services.journey.get_qualifying_events_for_shopper", return_value=raw_events),
        patch("app.services.journey.delete_shopper_journeys", new_callable=AsyncMock),
        patch("app.services.journey.record_domain_activity", new_callable=AsyncMock),
    ):
        await generate_shopper_journeys_for_shopper(session, shopper_id, as_of=as_of)

        assert session.add_all.called
        journeys = session.add_all.call_args_list[0][0][0]
        assert len(journeys) == 1
        journey = journeys[0]

        # Status must remain OPEN
        assert journey.journey_status == "OPEN"
        assert journey.converted is False
        assert journey.started_at == t_start
        assert journey.ended_at is None
        assert journey.generated_at == as_of


@pytest.mark.asyncio
async def test_shopper_journey_converts_immediately_on_purchase():
    session = AsyncMock()
    shopper_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    order_id = uuid.uuid4()

    as_of = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)
    t_start = as_of - timedelta(days=1)
    t_purchase = t_start + timedelta(minutes=20)

    raw_events = [
        ("shopper", uuid.uuid4(), merchant_id, ShopperEventType.SESSION_STARTED.value, t_start, {}),
        ("shopper", uuid.uuid4(), merchant_id, ShopperEventType.PURCHASE_COMPLETED.value, t_purchase, {"order_id": str(order_id)}),
    ]

    with (
        patch("app.services.journey.get_qualifying_events_for_shopper", return_value=raw_events),
        patch("app.services.journey.delete_shopper_journeys", new_callable=AsyncMock),
        patch("app.services.journey.record_domain_activity", new_callable=AsyncMock),
    ):
        await generate_shopper_journeys_for_shopper(session, shopper_id, as_of=as_of)

        journeys = session.add_all.call_args_list[0][0][0]
        assert len(journeys) == 1
        journey = journeys[0]

        assert journey.journey_status == "CONVERTED"
        assert journey.converted is True
        assert journey.order_id == order_id
        assert journey.ended_at == t_purchase


@pytest.mark.asyncio
async def test_segment_refresh_passes_as_of_to_rule_evaluation():
    session = AsyncMock()
    shopper_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    seg_id = uuid.uuid4()
    as_of = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_segment = MagicMock()
    mock_segment.segment_id = seg_id
    mock_segment.segment_definition = {"type": "rule", "name": "active_30d"}

    with (
        patch("app.services.segment.get_shopper_merchant_id", return_value=merchant_id),
        patch("app.services.segment.get_merchant_segments", return_value=[mock_segment]),
        patch("app.services.segment.evaluate_segment_rule", new_callable=AsyncMock) as mock_eval,
        patch("app.services.segment.sync_shopper_segment_memberships", new_callable=AsyncMock) as mock_sync,
    ):
        mock_eval.return_value = True

        await refresh_shopper_segment_membership_callback(session, shopper_id, as_of=as_of)

        mock_eval.assert_called_once_with(
            session=session,
            shopper_id=shopper_id,
            definition={"type": "rule", "name": "active_30d"},
            evaluation_time=as_of,
        )
        mock_sync.assert_called_once_with(session, shopper_id, {seg_id}, as_of)
