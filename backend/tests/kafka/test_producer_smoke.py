"""Integration smoke test against a live local Kafka broker.

Requires `docker-compose up kafka` to be running on localhost:9092. Skips
itself if the broker is unreachable, since this is the one check in Unit 3.1
that depends on external infrastructure rather than being a pure unit test.
"""

import asyncio
from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition

from app.config.settings import settings
from app.kafka.producer import EventProducer
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from app.schemas.events.dlq import DeadLetterRecord


@pytest.fixture
async def started_producer():
    from app.kafka.producer import event_producer
    from aiokafka.errors import KafkaConnectionError
    import pytest
    try:
        await event_producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield event_producer
    await event_producer.stop()


async def _drain_until_matching_envelope(
    consumer: AIOKafkaConsumer,
    event_id: uuid4,
    timeout_seconds: float = 10.0,
    max_messages: int = 500,
):
    target_id_str = str(event_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    for _ in range(max_messages):
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            message = await asyncio.wait_for(consumer.getone(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        try:
            data = json.loads(message.value.decode("utf-8"))
            if data.get("event_id") == target_id_str:
                return message
        except Exception:
            pass
    raise AssertionError(f"event {event_id} not found within timeout/messages")


async def _drain_until_matching_dlq_record(
    consumer: AIOKafkaConsumer,
    error_message: str,
    timeout_seconds: float = 10.0,
    max_messages: int = 500,
):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    for _ in range(max_messages):
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            message = await asyncio.wait_for(consumer.getone(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        try:
            data = json.loads(message.value.decode("utf-8"))
            if data.get("error_message") == error_message:
                return message
        except Exception:
            pass
    raise AssertionError(f"DLQ record with error {error_message!r} not found within timeout/messages")


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
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        await started_producer.publish(settings.kafka_merchant_events_topic, envelope)
        message = await _drain_until_matching_envelope(consumer, envelope.event_id)
        assert envelope.model_dump_json().encode("utf-8") == message.value
    finally:
        await consumer.stop()

async def test_publish_record_reaches_dlq_topic(started_producer: EventProducer):
    record = DeadLetterRecord(
        original_topic=settings.kafka_merchant_events_topic,
        original_partition=0,
        original_offset=100,
        consumer_group_id=settings.kafka_merchant_consumer_group_id,
        failure_stage="processing",
        error_type="ValueError",
        error_message=f"Simulated DLQ error {uuid4()}",
        failed_at=datetime.now(timezone.utc),
        original_message_base64="aGVsbG8=",
    )

    consumer = AIOKafkaConsumer(
        settings.kafka_merchant_dlq_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        await started_producer.publish_record(settings.kafka_merchant_dlq_topic, record)
        message = await _drain_until_matching_dlq_record(consumer, record.error_message)
        assert record.model_dump_json().encode("utf-8") == message.value
    finally:
        await consumer.stop()

async def test_publish_surfaces_failures():
    producer = EventProducer()
    # Not started yet
    with pytest.raises(RuntimeError, match="not started"):
        await producer.publish_record("some_topic", DeadLetterRecord(
            original_topic="t", original_partition=0, original_offset=0,
            consumer_group_id="g", failure_stage="validation", error_type="E",
            error_message="M", failed_at=datetime.now(timezone.utc),
            original_message_base64="Yg==",
        ))
