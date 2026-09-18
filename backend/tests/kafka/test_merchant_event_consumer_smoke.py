"""Integration smoke test against live local Kafka + Postgres for the merchant event consumer.

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
from app.kafka.consumer import MerchantEventConsumer
from app.kafka.producer import EventProducer
from app.models.event import MerchantEvent
from app.models.merchant import Merchant
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from app.services.merchant import UnresolvedReferenceError


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
    instance = MerchantEventConsumer(group_id=f"consumer-smoke-test-{uuid.uuid4()}")
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield instance
    await instance.stop()


@pytest.fixture
async def merchant():
    # Each async test runs on its own event loop, but the engine's connection
    # pool is a module-level singleton - dispose it first so a stale
    # connection bound to a previous test's loop is never reused here.
    await engine.dispose()

    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")

    merchant_row = Merchant(
        merchant_id=uuid.uuid4(),
        shopify_store_id=f"store-{uuid.uuid4().hex[:8]}",
        merchant_name="Consumer Smoke Test Merchant",
        email="consumer-smoke@example.com",
        country="US",
        timezone="America/New_York",
        app_install_status="installed",
    )
    session.add(merchant_row)
    await session.commit()
    yield merchant_row
    await session.execute(delete(MerchantEvent).where(MerchantEvent.merchant_id == merchant_row.merchant_id))
    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_row.merchant_id))
    await session.commit()
    await session.close()


async def _drain_until_event(consumer: MerchantEventConsumer, event_id: uuid.UUID, max_messages: int = 5000):
    """Fast-forward past any unrelated backlog on the shared topic.

    A fresh unique group_id with auto_offset_reset="earliest" replays the
    entire topic history, which may contain messages from unrelated prior
    test runs. Commit straight past anything that isn't the message we're
    looking for, without running it through persistence/processing.
    """
    for _ in range(max_messages):
        message = await consumer._consumer.getone()
        envelope = consumer._validate(message)
        if envelope is not None and envelope.event_id == event_id:
            return message
        await consumer._commit_message(message)
    raise AssertionError(f"event {event_id} not found within {max_messages} messages")


def _login_envelope(merchant_id: uuid.UUID, event_id: uuid.UUID | None = None) -> MerchantEventEnvelope:
    return MerchantEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=MerchantEventType.MERCHANT_LOGIN,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        payload={"login_channel": "admin_dashboard"},
        source="consumer-smoke-test",
    )


async def test_consumer_starts_and_stops_against_live_kafka():
    instance = MerchantEventConsumer()
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    assert instance.is_started is True
    await instance.stop()
    assert instance.is_started is False


async def test_successful_event_is_processed_and_offset_committed(
    started_producer: EventProducer, consumer: MerchantEventConsumer, merchant: Merchant
):
    envelope = _login_envelope(merchant.merchant_id)
    await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))

    message = await _drain_until_event(consumer, envelope.event_id)
    await consumer._handle_message(message)

    async with AsyncSessionLocal() as session:
        row = await session.get(MerchantEvent, envelope.event_id)
    assert row.processed is True
    assert row.processed_at is not None

    async with AsyncSessionLocal() as session:
        updated_merchant = await session.get(Merchant, merchant.merchant_id)
    assert updated_merchant.last_active_at is not None

    committed = await consumer._consumer.committed(TopicPartition(message.topic, message.partition))
    assert committed == message.offset + 1


async def test_duplicate_delivery_after_processing_is_skipped_and_offset_still_committed(
    started_producer: EventProducer, consumer: MerchantEventConsumer, merchant: Merchant
):
    envelope = _login_envelope(merchant.merchant_id)
    await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))
    await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))

    first_message = await _drain_until_event(consumer, envelope.event_id)
    await consumer._handle_message(first_message)
    second_message = await consumer._consumer.getone()
    await consumer._handle_message(second_message)

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(MerchantEvent).where(MerchantEvent.event_id == envelope.event_id))).scalars().all()
    assert len(rows) == 1
    assert rows[0].processed is True

    committed = await consumer._consumer.committed(TopicPartition(second_message.topic, second_message.partition))
    assert committed == second_message.offset + 1


async def test_processing_failure_does_not_commit_offset(
    started_producer: EventProducer, consumer: MerchantEventConsumer, merchant: Merchant
):
    # SUBSCRIPTION_RENEWED with no active subscription on file triggers
    # UnresolvedReferenceError in business processing.
    envelope = MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=MerchantEventType.SUBSCRIPTION_RENEWED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant.merchant_id,
        payload={
            "plan_key": "starter",
            "billing_cycle": "monthly",
            "amount_paid": 19,
            "renewal_at": datetime.now(timezone.utc).isoformat(),
        },
        source="consumer-smoke-test",
    )
    await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))

    message = await _drain_until_event(consumer, envelope.event_id)
    topic_partition = TopicPartition(message.topic, message.partition)
    committed_before = await consumer._consumer.committed(topic_partition)

    with pytest.raises(UnresolvedReferenceError):
        await consumer._handle_message(message)

    async with AsyncSessionLocal() as session:
        row = await session.get(MerchantEvent, envelope.event_id)
    assert row is not None
    assert row.processed is False

    committed_after = await consumer._consumer.committed(topic_partition)
    assert committed_after == committed_before
    assert committed_after != message.offset + 1
