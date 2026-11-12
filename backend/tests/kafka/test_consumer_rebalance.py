"""Unit tests for Kafka consumer rebalance handling, tuning configuration, and replay safety."""

from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from aiokafka.errors import CommitFailedError, IllegalStateError
from aiokafka.structs import ConsumerRecord, TopicPartition

from app.config.settings import settings
from app.kafka.consumer import BaseEventConsumer, LoggingRebalanceListener
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from app.schemas.events.payloads.merchant import MerchantCreatedPayload


@dataclass
class _FakeRecord:
    value: bytes
    topic: str = "cip.merchant.events"
    partition: int = 0
    offset: int = 100


class _TestEventRecord:
    def __init__(self, event_id: uuid.UUID, processed: bool = False) -> None:
        self.event_id = event_id
        self.processed = processed


def _make_test_envelope(event_id: uuid.UUID | None = None) -> MerchantEventEnvelope:
    eid = event_id or uuid.uuid4()
    mid = uuid.uuid4()
    payload = MerchantCreatedPayload(
        shopify_store_id="store-test-1",
        merchant_name="Test Store",
        email="test@store.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
    )
    return MerchantEventEnvelope(
        event_id=eid,
        event_type=MerchantEventType.MERCHANT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=mid,
        payload=payload.model_dump(mode="json"),
        source="test",
    )


def test_rebalance_listener_logs_partition_changes():
    listener = LoggingRebalanceListener(domain_name="shopper", group_id="cip-shopper-consumer")
    tp0 = TopicPartition("cip.shopper.events", 0)
    tp1 = TopicPartition("cip.shopper.events", 1)

    with patch("app.kafka.consumer.logger.info") as mock_log:
        listener.on_partitions_assigned([tp0, tp1])
        mock_log.assert_called_once()
        assert "cip.shopper.events[0]" in mock_log.call_args[0][3]

    with patch("app.kafka.consumer.logger.info") as mock_log:
        listener.on_partitions_revoked([tp0])
        mock_log.assert_called_once()
        assert "cip.shopper.events[0]" in mock_log.call_args[0][3]


@pytest.mark.asyncio
async def test_consumer_start_binds_tuning_settings_and_listener():
    mock_aiokafka = MagicMock()
    mock_aiokafka.start = AsyncMock()
    mock_aiokafka.stop = AsyncMock()

    with patch("app.kafka.consumer.AIOKafkaConsumer", return_value=mock_aiokafka) as mock_init:
        consumer = BaseEventConsumer[MerchantEventEnvelope](
            topic="cip.merchant.events",
            group_id="test-group",
            envelope_model=MerchantEventEnvelope,
            insert_event_fn=AsyncMock(),
            get_event_fn=AsyncMock(),
        )

        await consumer.start()

        # Verify AIOKafkaConsumer configured with tuning settings
        mock_init.assert_called_once()
        _, kwargs = mock_init.call_args
        assert kwargs["max_poll_interval_ms"] == settings.kafka_consumer_max_poll_interval_ms
        assert kwargs["session_timeout_ms"] == settings.kafka_consumer_session_timeout_ms
        assert kwargs["heartbeat_interval_ms"] == settings.kafka_consumer_heartbeat_interval_ms
        assert kwargs["max_poll_records"] == settings.kafka_consumer_max_poll_records

        # Verify subscribed with rebalance listener
        mock_aiokafka.subscribe.assert_called_once()
        topics_arg, sub_kwargs = mock_aiokafka.subscribe.call_args
        assert topics_arg[0] == ["cip.merchant.events"]
        assert isinstance(sub_kwargs["listener"], LoggingRebalanceListener)

        await consumer.stop()


@pytest.mark.asyncio
async def test_commit_message_catches_commit_failed_error_without_raising():
    mock_aiokafka = MagicMock()
    mock_aiokafka.commit = AsyncMock(side_effect=CommitFailedError("Rebalance occurred"))

    consumer = BaseEventConsumer[MerchantEventEnvelope](
        topic="cip.merchant.events",
        group_id="test-group",
        envelope_model=MerchantEventEnvelope,
        insert_event_fn=AsyncMock(),
        get_event_fn=AsyncMock(),
    )
    consumer._consumer = mock_aiokafka

    msg = _FakeRecord(value=b"test", topic="cip.merchant.events", partition=1, offset=42)

    with patch("app.kafka.consumer.logger.warning") as mock_warn:
        # Must return False rather than raising CommitFailedError
        result = await consumer._commit_message(msg)
        assert result is False
        mock_warn.assert_called_once()
        assert "Offset commit failed" in mock_warn.call_args[0][0]


@pytest.mark.asyncio
async def test_commit_message_catches_illegal_state_error_without_raising():
    mock_aiokafka = MagicMock()
    mock_aiokafka.commit = AsyncMock(side_effect=IllegalStateError("Partition is not assigned"))

    consumer = BaseEventConsumer[MerchantEventEnvelope](
        topic="cip.merchant.events",
        group_id="test-group",
        envelope_model=MerchantEventEnvelope,
        insert_event_fn=AsyncMock(),
        get_event_fn=AsyncMock(),
    )
    consumer._consumer = mock_aiokafka

    msg = _FakeRecord(value=b"test", topic="cip.merchant.events", partition=1, offset=42)

    with patch("app.kafka.consumer.logger.warning") as mock_warn:
        # Must return False rather than raising IllegalStateError
        result = await consumer._commit_message(msg)
        assert result is False
        mock_warn.assert_called_once()
        assert "Offset commit failed" in mock_warn.call_args[0][0]


@pytest.mark.asyncio
async def test_full_replay_path_after_commit_failed():
    """Explicitly verify the full replay path:
    1. First delivery: business processing succeeds, but commit raises CommitFailedError (rebalance).
       Consumer handles it without crashing.
    2. Replay delivery of same event: duplicate detected in DB, business logic is skipped,
       and subsequent commit succeeds.
    """
    event_id = uuid.uuid4()
    envelope = _make_test_envelope(event_id)
    raw_bytes = envelope.model_dump_json().encode("utf-8")
    msg = _FakeRecord(value=raw_bytes, topic="cip.merchant.events", partition=0, offset=500)

    # In-memory mock database state
    event_db: dict[uuid.UUID, _TestEventRecord] = {}
    business_action_count = 0

    async def mock_insert_event(session, env: MerchantEventEnvelope) -> bool:
        if env.event_id in event_db:
            return False
        event_db[env.event_id] = _TestEventRecord(env.event_id, processed=False)
        return True

    async def mock_get_event(session, eid: uuid.UUID):
        return event_db.get(eid)

    async def mock_process_event(session, env: MerchantEventEnvelope) -> None:
        nonlocal business_action_count
        business_action_count += 1

    async def mock_mark_processed(session, eid: uuid.UUID, at: datetime) -> None:
        rec = event_db.get(eid)
        if rec:
            rec.processed = True

    mock_aiokafka = MagicMock()
    # First commit fails due to rebalance; second commit (replay) succeeds
    mock_aiokafka.commit = AsyncMock(
        side_effect=[CommitFailedError("Group rebalanced while processing"), None]
    )

    consumer = BaseEventConsumer[MerchantEventEnvelope](
        topic="cip.merchant.events",
        group_id="test-group",
        envelope_model=MerchantEventEnvelope,
        insert_event_fn=mock_insert_event,
        get_event_fn=mock_get_event,
        process_event_fn=mock_process_event,
        mark_processed_fn=mock_mark_processed,
        domain_name="merchant",
    )
    consumer._consumer = mock_aiokafka

    # 1. First delivery
    await consumer._handle_message(msg)

    # Business processing executed once
    assert business_action_count == 1
    # DB recorded the event as processed
    assert event_db[event_id].processed is True
    # One commit attempt was made and raised CommitFailedError (caught internally)
    assert mock_aiokafka.commit.call_count == 1

    # 2. Replay delivery of the same message (e.g. by new partition owner or redelivery)
    await consumer._handle_message(msg)

    # Business processing was SKIPPED on replay (action count remains exactly 1)
    assert business_action_count == 1
    # Second commit was executed and succeeded
    assert mock_aiokafka.commit.call_count == 2
