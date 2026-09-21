"""Integration smoke test against live local Kafka + Postgres for the product event consumer.

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
from app.kafka.consumer import ProductEventConsumer
from app.kafka.producer import EventProducer
from app.models.event import ProductEvent
from app.models.merchant import Merchant
from app.models.product import Product, ProductVariant
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType
from app.services.product import UnresolvedReferenceError


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


@pytest.fixture
async def consumer():
    # A unique group_id per test avoids interference from other tests'/runs'
    # committed offsets on the shared topic - with auto_offset_reset="earliest"
    # a brand-new group always starts from the beginning of the topic.
    instance = ProductEventConsumer(group_id=f"consumer-smoke-test-{uuid.uuid4()}")
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
        merchant_name="Product Consumer Smoke Test Merchant",
        email="product-consumer-smoke@example.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
    )
    session.add(merchant_row)
    await session.commit()
    yield merchant_row
    await session.execute(delete(ProductEvent).where(ProductEvent.merchant_id == merchant_row.merchant_id))
    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_row.merchant_id))
    await session.commit()
    await session.close()


async def _drain_until_event(consumer: ProductEventConsumer, event_id: uuid.UUID, max_messages: int = 5000):
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


def _created_envelope(
    merchant_id: uuid.UUID, product_id: uuid.UUID, event_id: uuid.UUID | None = None
) -> ProductEventEnvelope:
    return ProductEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=ProductEventType.PRODUCT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        product_id=product_id,
        payload={"product_name": "Smoke Test Product", "category": None, "vendor": None, "status": "active"},
        source="consumer-smoke-test",
    )


async def _cleanup_product(product_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ProductVariant).where(ProductVariant.product_id == product_id))
        await session.execute(delete(Product).where(Product.product_id == product_id))
        await session.execute(delete(ProductEvent).where(ProductEvent.product_id == product_id))
        await session.commit()


async def test_consumer_starts_and_stops_against_live_kafka():
    instance = ProductEventConsumer()
    try:
        await instance.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    assert instance.is_started is True
    await instance.stop()
    assert instance.is_started is False


async def test_successful_event_is_processed_and_offset_committed(
    started_producer: EventProducer, consumer: ProductEventConsumer, merchant: Merchant
):
    product_id = uuid.uuid4()
    try:
        envelope = _created_envelope(merchant.merchant_id, product_id)
        await started_producer.publish(
            settings.kafka_product_events_topic, envelope, key=f"{merchant.merchant_id}:{product_id}"
        )

        message = await _drain_until_event(consumer, envelope.event_id)
        await consumer._handle_message(message)

        async with AsyncSessionLocal() as session:
            row = await session.get(ProductEvent, envelope.event_id)
        assert row.processed is True
        assert row.processed_at is not None

        async with AsyncSessionLocal() as session:
            product = await session.get(Product, product_id)
        assert product is not None
        assert product.product_name == "Smoke Test Product"

        committed = await consumer._consumer.committed(TopicPartition(message.topic, message.partition))
        assert committed == message.offset + 1
    finally:
        await _cleanup_product(product_id)


async def test_duplicate_delivery_after_processing_is_skipped_and_offset_still_committed(
    started_producer: EventProducer, consumer: ProductEventConsumer, merchant: Merchant
):
    product_id = uuid.uuid4()
    try:
        envelope = _created_envelope(merchant.merchant_id, product_id)
        await started_producer.publish(
            settings.kafka_product_events_topic, envelope, key=f"{merchant.merchant_id}:{product_id}"
        )
        await started_producer.publish(
            settings.kafka_product_events_topic, envelope, key=f"{merchant.merchant_id}:{product_id}"
        )

        first_message = await _drain_until_event(consumer, envelope.event_id)
        await consumer._handle_message(first_message)
        second_message = await consumer._consumer.getone()
        await consumer._handle_message(second_message)

        async with AsyncSessionLocal() as session:
            rows = (
                (await session.execute(select(ProductEvent).where(ProductEvent.event_id == envelope.event_id)))
                .scalars()
                .all()
            )
        assert len(rows) == 1
        assert rows[0].processed is True

        async with AsyncSessionLocal() as session:
            products = (await session.execute(select(Product).where(Product.product_id == product_id))).scalars().all()
        assert len(products) == 1

        committed = await consumer._consumer.committed(TopicPartition(second_message.topic, second_message.partition))
        assert committed == second_message.offset + 1
    finally:
        await _cleanup_product(product_id)


async def test_processing_failure_commits_offset_after_dlq(
    started_producer: EventProducer, consumer: ProductEventConsumer, merchant: Merchant
):
    # PRODUCT_VARIANT_UPDATED referencing a variant_id that was never created
    # triggers UnresolvedReferenceError in business processing.
    product_id = uuid.uuid4()
    missing_variant_id = uuid.uuid4()
    try:
        envelope = ProductEventEnvelope(
            event_id=uuid.uuid4(),
            event_type=ProductEventType.PRODUCT_VARIANT_UPDATED,
            event_version=1,
            event_timestamp=datetime.now(timezone.utc),
            merchant_id=merchant.merchant_id,
            product_id=product_id,
            payload={"variant_id": str(missing_variant_id), "changed_values": {"price": "10.00"}},
            source="consumer-smoke-test",
        )
        await started_producer.publish(
            settings.kafka_product_events_topic, envelope, key=f"{merchant.merchant_id}:{product_id}"
        )

        message = await _drain_until_event(consumer, envelope.event_id)
        topic_partition = TopicPartition(message.topic, message.partition)
        committed_before = await consumer._consumer.committed(topic_partition)

        await consumer._handle_message(message)

        async with AsyncSessionLocal() as session:
            row = await session.get(ProductEvent, envelope.event_id)
        assert row is not None
        assert row.processed is False

        async with AsyncSessionLocal() as session:
            variant = await session.get(ProductVariant, missing_variant_id)
        assert variant is None

        committed_after = await consumer._consumer.committed(topic_partition)
        assert committed_after == message.offset + 1
    finally:
        await _cleanup_product(product_id)
