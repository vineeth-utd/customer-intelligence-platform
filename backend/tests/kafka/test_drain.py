"""Unit tests for Kafka consumer drain and verification."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiokafka.structs import OffsetAndMetadata, TopicPartition
import pytest

from app.config.settings import settings
from app.kafka.drain import (
    DOMAIN_KAFKA_MAPPING,
    check_consumer_offsets,
    verify_no_unprocessed_events,
    wait_for_drain,
)


@pytest.mark.asyncio
async def test_check_consumer_offsets_calculates_lag():
    merchant_topic = settings.kafka_merchant_events_topic
    target_offsets = {
        merchant_topic: {0: 100, 1: 50},
    }

    mock_admin = AsyncMock()
    # Partition 0 committed 90 (lag 10), Partition 1 committed 50 (lag 0)
    mock_admin.list_consumer_group_offsets.return_value = {
        TopicPartition(merchant_topic, 0): OffsetAndMetadata(90, ""),
        TopicPartition(merchant_topic, 1): OffsetAndMetadata(50, ""),
    }

    with patch("app.kafka.drain.AIOKafkaAdminClient", return_value=mock_admin):
        is_drained, lag_by_domain = await check_consumer_offsets(target_offsets)
        assert is_drained is False
        assert lag_by_domain["merchant"] == 10


@pytest.mark.asyncio
async def test_check_consumer_offsets_drained_when_all_committed():
    merchant_topic = settings.kafka_merchant_events_topic
    target_offsets = {
        merchant_topic: {0: 100},
    }

    mock_admin = AsyncMock()
    mock_admin.list_consumer_group_offsets.return_value = {
        TopicPartition(merchant_topic, 0): OffsetAndMetadata(100, ""),
    }

    with patch("app.kafka.drain.AIOKafkaAdminClient", return_value=mock_admin):
        is_drained, lag_by_domain = await check_consumer_offsets(target_offsets)
        assert is_drained is True
        assert lag_by_domain["merchant"] == 0


@pytest.mark.asyncio
async def test_verify_no_unprocessed_events():
    session = AsyncMock()
    # 0 unprocessed for all 4 domains
    session.scalar.side_effect = [0, 0, 0, 0]
    is_clean, counts = await verify_no_unprocessed_events(session)
    assert is_clean is True
    assert all(c == 0 for c in counts.values())

    # 1 unprocessed for shopper
    session.scalar.side_effect = [0, 0, 1, 0]
    is_clean, counts = await verify_no_unprocessed_events(session)
    assert is_clean is False
    assert counts["shopper"] == 1


@pytest.mark.asyncio
async def test_wait_for_drain_succeeds_when_offsets_and_database_clean():
    target_offsets = {"topic-a": {0: 10}}

    with (
        patch("app.kafka.drain.check_consumer_offsets", new_callable=AsyncMock) as mock_check,
        patch("app.kafka.drain.verify_no_unprocessed_events", new_callable=AsyncMock) as mock_verify,
        patch("app.kafka.drain.AsyncSessionLocal") as mock_session_local,
    ):
        mock_check.return_value = (True, {"merchant": 0})
        mock_verify.return_value = (True, {"merchant": 0})
        mock_session_local.return_value.__aenter__.return_value = AsyncMock()

        await wait_for_drain(target_offsets=target_offsets, timeout=5.0)
        assert mock_check.called
        assert mock_verify.called


@pytest.mark.asyncio
async def test_wait_for_drain_fails_if_unprocessed_events_remain():
    target_offsets = {"topic-a": {0: 10}}

    with (
        patch("app.kafka.drain.check_consumer_offsets", new_callable=AsyncMock) as mock_check,
        patch("app.kafka.drain.verify_no_unprocessed_events", new_callable=AsyncMock) as mock_verify,
        patch("app.kafka.drain.AsyncSessionLocal") as mock_session_local,
    ):
        mock_check.return_value = (True, {"merchant": 0})
        mock_verify.return_value = (False, {"shopper": 2})
        mock_session_local.return_value.__aenter__.return_value = AsyncMock()

        with pytest.raises(RuntimeError, match="unprocessed events: {'shopper': 2}"):
            await wait_for_drain(target_offsets=target_offsets, timeout=5.0)

