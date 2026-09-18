"""Integration smoke test against live local Kafka + Postgres for the product event consumer.

Requires `docker-compose up kafka postgres` running locally. Skips itself if
either is unreachable, mirroring the other tests/kafka smoke tests.
"""

import uuid
from datetime import datetime, timezone

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from sqlalchemy import delete, select

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.kafka.consumer import ProductEventConsumer
from app.kafka.producer import EventProducer
from app.models.event import ProductEvent
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType


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
async def raw_consumer():
    consumer = AIOKafkaConsumer(
        settings.kafka_product_events_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"consumer-smoke-test-{uuid.uuid4()}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    try:
        await consumer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield consumer
    await consumer.stop()


@pytest.fixture
def product_ref():
    """A synthetic (merchant_id, product_id) pair.

    No operational Merchant/Product rows are created: product_events.merchant_id
    and product_id are lineage/correlation identifiers, not enforced foreign
    keys, so persistence must succeed independently of the operational rows.
    """
    return uuid.uuid4(), uuid.uuid4()


async def test_consumer_starts_and_stops_against_live_kafka():
    consumer = ProductEventConsumer()
    try:
        await consumer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    assert consumer.is_started is True
    await consumer.stop()
    assert consumer.is_started is False


async def test_duplicate_delivery_persists_exactly_one_row(
    started_producer: EventProducer, raw_consumer: AIOKafkaConsumer, product_ref: tuple[uuid.UUID, uuid.UUID]
):
    # Each async test runs on its own event loop, but the engine's connection
    # pool is a module-level singleton - dispose it first, before any
    # AsyncSessionLocal use in this test (including inside _handle_message),
    # so a stale connection bound to a previous test's loop is never reused.
    await engine.dispose()

    merchant_id, product_id = product_ref
    envelope = ProductEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=ProductEventType.PRODUCT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        product_id=product_id,
        payload={"product_name": "Smoke Test Product", "category": None, "vendor": None, "status": "active"},
        source="consumer-smoke-test",
    )

    await started_producer.publish(settings.kafka_product_events_topic, envelope, key=f"{merchant_id}:{product_id}")
    await started_producer.publish(settings.kafka_product_events_topic, envelope, key=f"{merchant_id}:{product_id}")

    consumer_under_test = ProductEventConsumer()
    for _ in range(2):
        message = await raw_consumer.getone()
        await consumer_under_test._handle_message(message)

    async with AsyncSessionLocal() as session:
        rows = (
            (await session.execute(select(ProductEvent).where(ProductEvent.event_id == envelope.event_id)))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].processed is False
        assert rows[0].processed_at is None

        await session.execute(delete(ProductEvent).where(ProductEvent.event_id == envelope.event_id))
        await session.commit()
