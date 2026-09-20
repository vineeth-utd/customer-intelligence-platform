import uuid
import json
import base64
from datetime import datetime, timezone

import pytest
from aiokafka import TopicPartition, AIOKafkaConsumer
from sqlalchemy import select, delete, text

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.kafka.consumer import ShopperEventConsumer
from app.kafka.producer import EventProducer
from app.models.merchant import Merchant
from app.models.product import Product, ProductVariant
from app.models.event import ShopperEvent
from app.schemas.events import ShopperEventEnvelope, ShopperEventType
from app.schemas.events.payloads.shopper import SessionStartedPayload, PurchaseCompletedPayload, OrderItemPayload

@pytest.fixture
async def started_producer():
    from aiokafka.errors import KafkaConnectionError
    from app.kafka.producer import event_producer
    try:
        await event_producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield event_producer
    await event_producer.stop()

@pytest.fixture
async def consumer():
    from aiokafka.errors import KafkaConnectionError
    instance = ShopperEventConsumer(group_id=f"consumer-dlq-test-{uuid.uuid4()}")
    
    try:
        await instance.start()
        
        # Seek to end to avoid reading thousands of old messages
        partitions = instance._consumer.assignment()
        if not partitions:
            # Let it assign
            await instance._consumer.topics()
            import asyncio
            for _ in range(10):
                partitions = instance._consumer.assignment()
                if partitions:
                    break
                await asyncio.sleep(0.1)
        if partitions:
            await instance._consumer.seek_to_end(*partitions)
            
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

@pytest.fixture
async def merchant(db_session):
    merchant_row = Merchant(
        merchant_id=uuid.uuid4(),
        shopify_store_id=f"store-{uuid.uuid4().hex[:8]}",
        merchant_name="DLQ Test Merchant",
        email="dlq-test@example.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
    )
    db_session.add(merchant_row)
    await db_session.commit()
    yield merchant_row
    from app.models.shopper import Shopper
    await db_session.execute(delete(ShopperEvent).where(ShopperEvent.merchant_id == merchant_row.merchant_id))
    await db_session.execute(delete(Shopper).where(Shopper.merchant_id == merchant_row.merchant_id))
    await db_session.execute(text(f"DELETE FROM product_variants WHERE product_id IN (SELECT product_id FROM products WHERE merchant_id = '{merchant_row.merchant_id}')"))
    await db_session.execute(delete(Product).where(Product.merchant_id == merchant_row.merchant_id))
    await db_session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_row.merchant_id))
    await db_session.commit()

@pytest.fixture
async def product_variant_no_inventory(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    prod = Product(
        merchant_id=merchant.merchant_id,
        product_id=product_id,
        product_name="DLQ Test Product",
        status="active",
        vendor="Vendor",
    )
    db_session.add(prod)
    var = ProductVariant(
        product_id=product_id,
        variant_id=variant_id,
        variant_name="DLQ Test Variant",
        sku="SKU-123",
        price="10.00",
        inventory_quantity=0,  # Zero inventory
        status="active"
    )
    db_session.add(var)
    await db_session.commit()
    yield prod, var

async def _drain_until_event(consumer: ShopperEventConsumer, event_id: uuid.UUID, max_messages: int = 5000):
    for _ in range(max_messages):
        message = await consumer._consumer.getone()
        envelope = consumer._validate(message)
        if envelope is not None and envelope.event_id == event_id:
            return message
    raise AssertionError(f"event {event_id} not found within {max_messages} messages")


async def test_shopper_insufficient_inventory_triggers_dlq(
    started_producer: EventProducer, consumer: ShopperEventConsumer, db_session, merchant, product_variant_no_inventory
):
    merchant_id = merchant.merchant_id
    shopper_id = uuid.uuid4()
    prod, var = product_variant_no_inventory
    
    # 1. Publish PURCHASE_COMPLETED requiring quantity 1
    event_id = uuid.uuid4()
    payload_obj = PurchaseCompletedPayload(
        order_id=uuid.uuid4(),
        total_amount="10.00",
        items=[
            OrderItemPayload(
                product_id=prod.product_id,
                variant_id=var.variant_id,
                quantity=1,
                unit_price="10.00"
            )
        ]
    )
    envelope = ShopperEventEnvelope(
        event_id=event_id,
        event_type=ShopperEventType.PURCHASE_COMPLETED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        payload=payload_obj.model_dump(mode="json"),
        source="consumer-dlq-test",
    )
    await started_producer.publish(
        settings.kafka_shopper_events_topic, envelope, key=f"{merchant_id}:{shopper_id}"
    )

    message = await _drain_until_event(consumer, event_id)
    topic_partition = TopicPartition(message.topic, message.partition)
    
    # Run consumer handle message (which should process, fail business logic, catch InsufficientInventoryError,
    # publish to DLQ, and commit offset)
    await consumer._handle_message(message)

    # 2. Verify raw shopper_event persists and processed=False
    row = await db_session.get(ShopperEvent, event_id)
    assert row is not None
    assert row.processed is False
    assert row.processed_at is None

    # 3. Original Shopper offset advances
    committed_after = await consumer._consumer.committed(topic_partition)
    assert committed_after == message.offset + 1

    # 4. Read from DLQ topic to verify DeadLetterRecord
    dlq_consumer = AIOKafkaConsumer(
        settings.kafka_shopper_dlq_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"dlq-reader-{uuid.uuid4()}",
        auto_offset_reset="earliest"
    )
    await dlq_consumer.start()
    try:
        found_dlq = False
        for _ in range(500):
            try:
                import asyncio
                dlq_msg = await asyncio.wait_for(dlq_consumer.getone(), timeout=2.0)
            except asyncio.TimeoutError:
                break
            from app.schemas.events.dlq import DeadLetterRecord
            record = DeadLetterRecord.model_validate_json(dlq_msg.value)
            if record.original_topic == settings.kafka_shopper_events_topic and record.original_offset == message.offset and record.original_partition == message.partition:
                found_dlq = True
                assert record.failure_stage == "processing"
                assert record.error_type == "InsufficientInventoryError"
                assert record.original_event_id == event_id
                assert record.event_type == "PURCHASE_COMPLETED"
                # Recover original bytes
                original_bytes = base64.b64decode(record.original_message_base64)
                assert original_bytes == message.value
                break
        assert found_dlq, "DLQ message not found"
    finally:
        await dlq_consumer.stop()

    # 5. Consumer remains usable: publish and process a subsequent valid Shopper event
    next_event_id = uuid.uuid4()
    next_envelope = ShopperEventEnvelope(
        event_id=next_event_id,
        event_type=ShopperEventType.SESSION_STARTED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        payload=SessionStartedPayload(referrer="test", email="test@test.com").model_dump(mode="json"),
        source="consumer-dlq-test",
    )
    await started_producer.publish(
        settings.kafka_shopper_events_topic, next_envelope, key=f"{merchant_id}:{shopper_id}"
    )
    next_message = await _drain_until_event(consumer, next_event_id)
    await consumer._handle_message(next_message)
    
    next_row = await db_session.get(ShopperEvent, next_event_id)
    assert next_row is not None
    assert next_row.processed is True
