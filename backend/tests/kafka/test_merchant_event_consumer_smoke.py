"""Integration smoke test against live local Kafka + Postgres for the merchant event consumer.

Requires `docker-compose up kafka postgres` running locally. Skips itself if
either is unreachable, mirroring the other tests/kafka smoke tests.
"""

import uuid
from datetime import datetime, timezone

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from sqlalchemy import delete, select, text

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.kafka.consumer import MerchantEventConsumer
from app.kafka.producer import EventProducer
from app.models.event import MerchantEvent
from app.models.merchant import Merchant
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


@pytest.fixture
async def raw_consumer():
    consumer = AIOKafkaConsumer(
        settings.kafka_merchant_events_topic,
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


async def test_consumer_starts_and_stops_against_live_kafka():
    consumer = MerchantEventConsumer()
    try:
        await consumer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    assert consumer.is_started is True
    await consumer.stop()
    assert consumer.is_started is False


async def test_duplicate_delivery_persists_exactly_one_row(
    started_producer: EventProducer, raw_consumer: AIOKafkaConsumer, merchant: Merchant
):
    envelope = MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=MerchantEventType.MERCHANT_LOGIN,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant.merchant_id,
        payload={"login_channel": "admin_dashboard"},
        source="consumer-smoke-test",
    )

    await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))
    await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))

    consumer_under_test = MerchantEventConsumer()
    for _ in range(2):
        message = await raw_consumer.getone()
        await consumer_under_test._handle_message(message)

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(select(MerchantEvent).where(MerchantEvent.event_id == envelope.event_id))
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].processed is False
    assert rows[0].processed_at is None
