"""Unit tests for the generic reprocess_unprocessed_events recovery utility."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.schemas.events.event_types import (
    CampaignEventType,
    MerchantEventType,
    ProductEventType,
    ShopperEventType,
)
from scripts.reprocess_unprocessed_events import (
    DEPENDENCY_ORDER,
    DOMAIN_REPROCESSORS,
    reprocess_all_domains,
    reprocess_domain,
)


def test_domain_reprocessors_and_dependency_order():
    """Verify all four domains are registered and dependency order is Merchant -> Product -> Shopper -> Campaign."""
    assert DEPENDENCY_ORDER == ("merchant", "product", "shopper", "campaign")
    for domain in DEPENDENCY_ORDER:
        assert domain in DOMAIN_REPROCESSORS
        reprocessor = DOMAIN_REPROCESSORS[domain]
        assert reprocessor.domain == domain
        assert callable(reprocessor.get_fn)
        assert callable(reprocessor.mark_fn)
        assert callable(reprocessor.process_fn)
        assert callable(reprocessor.to_envelope)


def test_envelope_converters_produce_valid_envelopes():
    """Verify each domain's to_envelope lambda correctly converts a database record to an envelope."""
    # 1. Merchant
    rec_m = MagicMock(
        event_id=uuid.uuid4(),
        event_type=MerchantEventType.MERCHANT_CREATED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        payload={"merchant_name": "Test"},
        source="test",
    )
    env_m = DOMAIN_REPROCESSORS["merchant"].to_envelope(rec_m)
    assert env_m.event_id == rec_m.event_id
    assert env_m.event_type == MerchantEventType.MERCHANT_CREATED

    # 2. Product
    rec_p = MagicMock(
        event_id=uuid.uuid4(),
        event_type=ProductEventType.PRODUCT_CREATED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        payload={"title": "Widget"},
        source="test",
    )
    env_p = DOMAIN_REPROCESSORS["product"].to_envelope(rec_p)
    assert env_p.event_id == rec_p.event_id
    assert env_p.product_id == rec_p.product_id

    # 3. Shopper
    rec_s = MagicMock(
        event_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        shopper_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        payload={},
        source="test",
    )
    env_s = DOMAIN_REPROCESSORS["shopper"].to_envelope(rec_s)
    assert env_s.event_id == rec_s.event_id
    assert env_s.shopper_id == rec_s.shopper_id

    # 4. Campaign
    rec_c = MagicMock(
        event_id=uuid.uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CONVERTED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        campaign_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        shopper_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        payload={"order_id": str(uuid.uuid4())},
        source="test",
    )
    env_c = DOMAIN_REPROCESSORS["campaign"].to_envelope(rec_c)
    assert env_c.event_id == rec_c.event_id
    assert env_c.campaign_id == rec_c.campaign_id


@pytest.mark.asyncio
async def test_reprocess_domain_success_and_idempotent_skip():
    event_id = uuid.uuid4()
    mock_event = MagicMock(
        event_id=event_id,
        event_type=MerchantEventType.MERCHANT_CREATED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        payload={"merchant_name": "Test Store"},
        source="test",
        processed=False,
    )

    mock_read_session = AsyncMock()
    mock_read_session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[mock_event])))

    mock_write_session = AsyncMock()
    mock_existing = MagicMock(
        event_id=event_id,
        event_type=MerchantEventType.MERCHANT_CREATED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        payload={"merchant_name": "Test Store"},
        source="test",
        processed=False,
    )

    with patch("scripts.reprocess_unprocessed_events.AsyncSessionLocal") as mock_session_cls, \
         patch.object(DOMAIN_REPROCESSORS["merchant"], "get_fn", AsyncMock(return_value=mock_existing)), \
         patch.object(DOMAIN_REPROCESSORS["merchant"], "process_fn", AsyncMock()) as mock_process, \
         patch.object(DOMAIN_REPROCESSORS["merchant"], "mark_fn", AsyncMock()) as mock_mark:

        mock_session_cls.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=mock_read_session), __aexit__=AsyncMock()),
            AsyncMock(__aenter__=AsyncMock(return_value=mock_write_session), __aexit__=AsyncMock()),
        ]

        stats = await reprocess_domain("merchant")
        assert stats["attempted"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0
        mock_process.assert_called_once()
        mock_mark.assert_called_once()
        mock_write_session.commit.assert_called_once()

    # Second execution: existing record is now marked processed -> skipped idempotently
    mock_existing.processed = True
    with patch("scripts.reprocess_unprocessed_events.AsyncSessionLocal") as mock_session_cls, \
         patch.object(DOMAIN_REPROCESSORS["merchant"], "get_fn", AsyncMock(return_value=mock_existing)), \
         patch.object(DOMAIN_REPROCESSORS["merchant"], "process_fn", AsyncMock()) as mock_process:

        mock_session_cls.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=mock_read_session), __aexit__=AsyncMock()),
            AsyncMock(__aenter__=AsyncMock(return_value=mock_write_session), __aexit__=AsyncMock()),
        ]

        stats = await reprocess_domain("merchant")
        assert stats["attempted"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0
        mock_process.assert_not_called()


@pytest.mark.asyncio
async def test_reprocess_domain_failure_rolls_back_and_leaves_unprocessed():
    event_id = uuid.uuid4()
    mock_event = MagicMock(
        event_id=event_id,
        event_type=ShopperEventType.PURCHASE_COMPLETED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        shopper_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        payload={"order_id": str(uuid.uuid4())},
        source="test",
        processed=False,
    )

    mock_read_session = AsyncMock()
    mock_read_session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[mock_event])))

    mock_write_session = AsyncMock()
    mock_existing = MagicMock(
        event_id=event_id,
        event_type=MerchantEventType.MERCHANT_CREATED.value,
        event_version=1,
        event_timestamp=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        merchant_id=uuid.uuid4(),
        payload={"merchant_name": "Test Store"},
        source="test",
        processed=False,
    )

    with patch("scripts.reprocess_unprocessed_events.AsyncSessionLocal") as mock_session_cls, \
         patch.object(DOMAIN_REPROCESSORS["shopper"], "get_fn", AsyncMock(return_value=mock_existing)), \
         patch.object(DOMAIN_REPROCESSORS["shopper"], "process_fn", AsyncMock(side_effect=RuntimeError("Inventory exhausted"))), \
         patch.object(DOMAIN_REPROCESSORS["shopper"], "mark_fn", AsyncMock()) as mock_mark:

        mock_session_cls.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=mock_read_session), __aexit__=AsyncMock()),
            AsyncMock(__aenter__=AsyncMock(return_value=mock_write_session), __aexit__=AsyncMock()),
        ]

        stats = await reprocess_domain("shopper")
        assert stats["attempted"] == 1
        assert stats["succeeded"] == 0
        assert stats["failed"] == 1
        mock_mark.assert_not_called()
        mock_write_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_reprocess_all_domains_executes_in_dependency_order():
    call_order = []

    async def fake_reprocess(domain):
        call_order.append(domain)
        return {"attempted": 0, "succeeded": 0, "failed": 0}

    with patch("scripts.reprocess_unprocessed_events.reprocess_domain", side_effect=fake_reprocess):
        results = await reprocess_all_domains()
        assert call_order == ["merchant", "product", "shopper", "campaign"]
        assert list(results.keys()) == ["merchant", "product", "shopper", "campaign"]
