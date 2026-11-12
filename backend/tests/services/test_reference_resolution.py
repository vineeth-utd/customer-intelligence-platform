"""Unit tests for configuration-driven reference resolution and campaign conversion retries."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.models.campaign import Campaign
from app.models.order import Order
from app.schemas.events.envelope import CampaignEventEnvelope
from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.payloads.campaign import CampaignConvertedPayload
from app.services.campaign import (
    AttributionError,
    UnresolvedReferenceError,
    _handle_campaign_converted,
)
from app.services.reference_resolver import resolve_reference
from scripts.reprocess_unprocessed_campaign_events import reprocess_unprocessed_campaign_events


@pytest.mark.asyncio
async def test_resolve_reference_immediate_hit():
    mock_lookup = AsyncMock(return_value="found_entity")
    res = await resolve_reference(mock_lookup, timeout=1.0, interval=0.05)
    assert res == "found_entity"
    assert mock_lookup.call_count == 1


@pytest.mark.asyncio
async def test_resolve_reference_delayed_hit():
    # Returns None twice, then returns the entity on the 3rd attempt
    mock_lookup = AsyncMock(side_effect=[None, None, "delayed_entity"])
    res = await resolve_reference(mock_lookup, timeout=2.0, interval=0.01)
    assert res == "delayed_entity"
    assert mock_lookup.call_count == 3


@pytest.mark.asyncio
async def test_resolve_reference_predicate_matching():
    # Returns a list that doesn't match predicate initially, then matches
    mock_lookup = AsyncMock(side_effect=[["a"], ["a", "b"], ["a", "b", "c"]])
    res = await resolve_reference(
        mock_lookup,
        timeout=1.0,
        interval=0.01,
        predicate=lambda items: "c" in items,
    )
    assert res == ["a", "b", "c"]
    assert mock_lookup.call_count == 3


@pytest.mark.asyncio
async def test_resolve_reference_timeout_exhausted():
    mock_lookup = AsyncMock(return_value=None)
    res = await resolve_reference(mock_lookup, timeout=0.05, interval=0.01)
    assert res is None
    assert mock_lookup.call_count >= 2


@pytest.mark.asyncio
async def test_campaign_converted_delayed_order_resolution():
    merchant_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    order_id = uuid.uuid4()

    fake_campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        segment_id=uuid.uuid4(),
        campaign_name="Test Promo",
        campaign_type="EMAIL",
        campaign_medium="email",
        status="ACTIVE",
        start_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    fake_order = Order(
        order_id=order_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        total_amount=Decimal("150.00"),
        placed_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    payload = CampaignConvertedPayload(order_id=order_id)
    envelope = CampaignEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CONVERTED,
        event_version=1,
        event_timestamp=datetime(2026, 8, 15, 12, 0, 1, tzinfo=timezone.utc),
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        payload=payload.model_dump(mode="json"),
        source="test",
    )

    session = AsyncMock()

    # get_order returns None on attempt 1, then fake_order on attempt 2
    with patch("app.services.campaign.get_campaign", AsyncMock(return_value=fake_campaign)), \
         patch("app.services.campaign.get_order", AsyncMock(side_effect=[None, fake_order])) as mock_get_order, \
         patch("app.services.campaign.is_order_attributed_to_campaign", AsyncMock(return_value=False)), \
         patch("app.services.reference_resolver.settings.reference_resolution_interval_seconds", 0.01), \
         patch("app.services.reference_resolver.settings.reference_resolution_timeout_seconds", 1.0):

        # Should succeed without raising UnresolvedReferenceError
        await _handle_campaign_converted(session, envelope)
        assert mock_get_order.call_count == 2


@pytest.mark.asyncio
async def test_campaign_converted_permanent_missing_order_raises():
    merchant_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    order_id = uuid.uuid4()

    fake_campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        segment_id=uuid.uuid4(),
        campaign_name="Test Promo",
        campaign_type="EMAIL",
        campaign_medium="email",
        status="ACTIVE",
        start_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    payload = CampaignConvertedPayload(order_id=order_id)
    envelope = CampaignEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CONVERTED,
        event_version=1,
        event_timestamp=datetime(2026, 8, 15, 12, 0, 1, tzinfo=timezone.utc),
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        payload=payload.model_dump(mode="json"),
        source="test",
    )

    session = AsyncMock()

    with patch("app.services.campaign.get_campaign", AsyncMock(return_value=fake_campaign)), \
         patch("app.services.campaign.get_order", AsyncMock(return_value=None)), \
         patch("app.services.reference_resolver.settings.reference_resolution_interval_seconds", 0.01), \
         patch("app.services.reference_resolver.settings.reference_resolution_timeout_seconds", 0.05):

        with pytest.raises(UnresolvedReferenceError, match=f"Order {order_id} not found"):
            await _handle_campaign_converted(session, envelope)


@pytest.mark.asyncio
async def test_campaign_converted_idempotent_when_already_attributed():
    merchant_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    order_id = uuid.uuid4()

    fake_campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        segment_id=uuid.uuid4(),
        campaign_name="Test Promo",
        campaign_type="EMAIL",
        campaign_medium="email",
        status="ACTIVE",
        start_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    fake_order = Order(
        order_id=order_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        total_amount=Decimal("150.00"),
        placed_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    payload = CampaignConvertedPayload(order_id=order_id)
    envelope = CampaignEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CONVERTED,
        event_version=1,
        event_timestamp=datetime(2026, 8, 15, 12, 0, 1, tzinfo=timezone.utc),
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        payload=payload.model_dump(mode="json"),
        source="test",
    )

    session = AsyncMock()

    with patch("app.services.campaign.get_campaign", AsyncMock(return_value=fake_campaign)), \
         patch("app.services.campaign.get_order", AsyncMock(return_value=fake_order)), \
         patch("app.services.campaign.is_order_attributed_to_campaign", AsyncMock(return_value=True)):

        # Should return cleanly without error
        await _handle_campaign_converted(session, envelope)


@pytest.mark.asyncio
async def test_reprocess_unprocessed_campaign_events_idempotent():
    with patch("scripts.reprocess_unprocessed_campaign_events.reprocess_domain", AsyncMock(return_value={"attempted": 1, "succeeded": 1, "failed": 0})) as mock_rep:
        stats = await reprocess_unprocessed_campaign_events()
        assert stats["attempted"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0
        mock_rep.assert_called_once_with("campaign")

