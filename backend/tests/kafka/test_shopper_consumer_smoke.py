"""Integration smoke test against live local Kafka + Postgres for the shopper event consumer.

Requires `docker-compose up kafka postgres` running locally. Skips itself if
either is unreachable, mirroring the other tests/kafka smoke tests.
"""

import uuid
from datetime import datetime, timezone

import pytest
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition
from sqlalchemy import delete, select, text

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.kafka.consumer import ShopperEventConsumer
from app.kafka.producer import EventProducer
from app.models.event import ShopperEvent
from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.payloads.shopper import SessionStartedPayload


@pytest.fixture
async def started_producer():
    producer = EventProducer()
    try:
        await producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield producer
    await producer.stop()


@pytest.fixture
async def consumer():
    # A unique group_id per test avoids interference from other tests'/runs'
    # committed offsets on the shared topic - with auto_offset_reset="earliest"
    # a brand-new group always starts from the beginning of the topic.
    instance = ShopperEventConsumer(group_id=f"consumer-smoke-test-{uuid.uuid4()}")
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield instance
    await instance.stop()


@pytest.fixture
async def db_session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")
    yield session
    await session.close()


async def _drain_until_event(consumer: ShopperEventConsumer, event_id: uuid.UUID, max_messages: int = 5000):
    for _ in range(max_messages):
        message = await consumer._consumer.getone()
        envelope = consumer._validate(message)
        if envelope is not None and envelope.event_id == event_id:
            return message
        # Interim: Valid messages don't commit, poison ones do. We just check until we find ours.
    raise AssertionError(f"event {event_id} not found within {max_messages} messages")


def _session_envelope(
    merchant_id: uuid.UUID, shopper_id: uuid.UUID, event_id: uuid.UUID | None = None
) -> ShopperEventEnvelope:
    return ShopperEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        payload=SessionStartedPayload(referrer="test", email="test@test.com").model_dump(mode="json"),
        source="consumer-smoke-test",
    )


async def test_consumer_starts_and_stops_against_live_kafka():
    instance = ShopperEventConsumer()
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    assert instance.is_started is True
    await instance.stop()
    assert instance.is_started is False


async def test_successful_event_is_persisted_but_not_processed_or_offset_committed(
    started_producer: EventProducer, consumer: ShopperEventConsumer, db_session
):
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    try:
        envelope = _session_envelope(merchant_id, shopper_id)
        await started_producer.publish(
            settings.kafka_shopper_events_topic, envelope, key=f"{merchant_id}:{shopper_id}"
        )

        message = await _drain_until_event(consumer, envelope.event_id)
        topic_partition = TopicPartition(message.topic, message.partition)
        committed_before = await consumer._consumer.committed(topic_partition)

        await consumer._handle_message(message)

        # Interim Unit 3.6C rules: Persisted, processed=False, NO offset commit
        row = await db_session.get(ShopperEvent, envelope.event_id)
        assert row is not None
        assert row.processed is False
        assert row.processed_at is None

        committed_after = await consumer._consumer.committed(topic_partition)
        assert committed_after == committed_before
        assert committed_after != message.offset + 1
    finally:
        await db_session.execute(delete(ShopperEvent).where(ShopperEvent.shopper_id == shopper_id))
        await db_session.commit()


async def test_duplicate_delivery_is_skipped_and_offset_still_not_committed(
    started_producer: EventProducer, consumer: ShopperEventConsumer, db_session
):
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    try:
        envelope = _session_envelope(merchant_id, shopper_id)
        await started_producer.publish(
            settings.kafka_shopper_events_topic, envelope, key=f"{merchant_id}:{shopper_id}"
        )
        await started_producer.publish(
            settings.kafka_shopper_events_topic, envelope, key=f"{merchant_id}:{shopper_id}"
        )

        first_message = await _drain_until_event(consumer, envelope.event_id)
        await consumer._handle_message(first_message)
        
        second_message = await consumer._consumer.getone()
        topic_partition = TopicPartition(second_message.topic, second_message.partition)
        committed_before = await consumer._consumer.committed(topic_partition)

        await consumer._handle_message(second_message)

        # Should be exactly 1 row
        rows = (
            (await db_session.execute(select(ShopperEvent).where(ShopperEvent.event_id == envelope.event_id)))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].processed is False

        # Still no commit
        committed_after = await consumer._consumer.committed(topic_partition)
        assert committed_after == committed_before
        assert committed_after != second_message.offset + 1
    finally:
        await db_session.execute(delete(ShopperEvent).where(ShopperEvent.shopper_id == shopper_id))
        await db_session.commit()
