"""Integration smoke test against live local Kafka + Postgres for the campaign event consumer.

Requires `docker-compose up kafka postgres` running locally. Skips itself if
either is unreachable.
"""

import uuid
from datetime import datetime, timezone

import pytest
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition
from sqlalchemy import delete, select, text

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.kafka.consumer import CampaignEventConsumer
from app.kafka.producer import EventProducer
from app.models.event import CampaignEvent
from app.schemas.events.envelope import CampaignEventEnvelope
from app.schemas.events.event_types import CampaignEventType


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
    instance = CampaignEventConsumer(group_id=f"consumer-smoke-test-{uuid.uuid4()}")
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield instance
    await instance.stop()


@pytest.fixture(autouse=True)
async def check_db():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")
    await session.close()


async def _drain_until_event(consumer: CampaignEventConsumer, event_id: uuid.UUID, max_messages: int = 5000):
    for _ in range(max_messages):
        message = await consumer._consumer.getone()
        envelope = consumer._validate(message)
        if envelope is not None and envelope.event_id == event_id:
            return message
        await consumer._commit_message(message)
    raise AssertionError(f"event {event_id} not found within {max_messages} messages")


def _created_envelope(
    merchant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    shopper_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> CampaignEventEnvelope:
    return CampaignEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        campaign_id=campaign_id,
        shopper_id=shopper_id,
        payload={
            "campaign_name": "Smoke Test Campaign",
            "campaign_type": "promotional",
            "campaign_medium": "email",
            "segment_id": str(uuid.uuid4()),
            "status": "draft",
            "start_at": None,
            "end_at": None,
        },
        source="consumer-smoke-test",
    )


async def _cleanup_campaign(campaign_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(CampaignEvent).where(CampaignEvent.campaign_id == campaign_id))
        await session.commit()


async def test_consumer_starts_and_stops_against_live_kafka():
    instance = CampaignEventConsumer()
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    assert instance.is_started is True
    await instance.stop()
    assert instance.is_started is False


async def test_valid_event_persists_without_offset_advancement_and_remains_unprocessed(
    started_producer: EventProducer, consumer: CampaignEventConsumer
):
    merchant_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    try:
        envelope = _created_envelope(merchant_id, campaign_id, shopper_id=None)
        await started_producer.publish(
            settings.kafka_campaign_events_topic, envelope, key=str(campaign_id)
        )

        message = await _drain_until_event(consumer, envelope.event_id)
        topic_partition = TopicPartition(message.topic, message.partition)
        committed_before = await consumer._consumer.committed(topic_partition)

        # 1. Processing fails with UnresolvedReferenceError because merchant doesn't exist
        with pytest.raises(Exception):
            await consumer._handle_message(message)

        # 2. Event is persisted
        async with AsyncSessionLocal() as session:
            row = await session.get(CampaignEvent, envelope.event_id)
        assert row is not None
        assert row.event_type == CampaignEventType.CAMPAIGN_CREATED.value
        assert row.merchant_id == merchant_id
        assert row.campaign_id == campaign_id
        assert row.shopper_id is None
        # 3. State remains unprocessed because transaction rolled back
        assert row.processed is False
        assert row.processed_at is None

        # 4. Offset is NOT advanced
        committed_after = await consumer._consumer.committed(topic_partition)
        assert committed_after == committed_before
        assert committed_after != message.offset + 1
    finally:
        await _cleanup_campaign(campaign_id)


async def test_duplicate_event_is_persisted_idempotently_without_offset_advancement(
    started_producer: EventProducer, consumer: CampaignEventConsumer
):
    merchant_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    try:
        envelope = _created_envelope(merchant_id, campaign_id, shopper_id=uuid.uuid4())
        await started_producer.publish(
            settings.kafka_campaign_events_topic, envelope, key=str(campaign_id)
        )
        await started_producer.publish(
            settings.kafka_campaign_events_topic, envelope, key=str(campaign_id)
        )

        first_message = await _drain_until_event(consumer, envelope.event_id)
        topic_partition = TopicPartition(first_message.topic, first_message.partition)
        committed_before = await consumer._consumer.committed(topic_partition)

        with pytest.raises(Exception):
            await consumer._handle_message(first_message)

        second_message = await consumer._consumer.getone()
        with pytest.raises(Exception):
            await consumer._handle_message(second_message)

        async with AsyncSessionLocal() as session:
            rows = (
                (await session.execute(select(CampaignEvent).where(CampaignEvent.event_id == envelope.event_id)))
                .scalars()
                .all()
            )
        assert len(rows) == 1
        assert rows[0].processed is False
        assert rows[0].shopper_id == envelope.shopper_id

        committed_after = await consumer._consumer.committed(topic_partition)
        assert committed_after == committed_before
        assert committed_after != second_message.offset + 1
    finally:
        await _cleanup_campaign(campaign_id)


async def test_poison_message_commits_offset_past_invalid_message(
    consumer: CampaignEventConsumer
):
    poison_bytes = f'{{"not_json": "{uuid.uuid4()}"'.encode("utf-8")
    raw_producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    try:
        await raw_producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")

    try:
        await raw_producer.send_and_wait(settings.kafka_campaign_events_topic, poison_bytes)
    finally:
        await raw_producer.stop()

    for _ in range(5000):
        message = await consumer._consumer.getone()
        if message.value == poison_bytes:
            break
        await consumer._commit_message(message)
    else:
        pytest.fail("Poison message not found in topic")

    topic_partition = TopicPartition(message.topic, message.partition)
    await consumer._handle_message(message)

    committed_after = await consumer._consumer.committed(topic_partition)
    assert committed_after == message.offset + 1
