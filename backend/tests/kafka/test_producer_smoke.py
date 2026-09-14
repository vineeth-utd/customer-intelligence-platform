"""Integration smoke test against a live local Kafka broker.

Requires `docker-compose up kafka` to be running on localhost:9092. Skips
itself if the broker is unreachable, since this is the one check in Unit 3.1
that depends on external infrastructure rather than being a pure unit test.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from app.config.settings import settings
from app.kafka.producer import EventProducer
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType


@pytest.fixture
async def started_producer():
    producer = EventProducer()
    try:
        await producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield producer
    await producer.stop()


async def test_publish_reaches_the_merchant_topic(started_producer: EventProducer):
    envelope = MerchantEventEnvelope(
        event_id=uuid4(),
        event_type=MerchantEventType.MERCHANT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=uuid4(),
        payload={"plan": "starter"},
        source="smoke-test",
    )

    consumer = AIOKafkaConsumer(
        settings.kafka_merchant_events_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        await started_producer.publish(settings.kafka_merchant_events_topic, envelope)
        message = await consumer.getone()
        assert envelope.model_dump_json().encode("utf-8") == message.value
    finally:
        await consumer.stop()
