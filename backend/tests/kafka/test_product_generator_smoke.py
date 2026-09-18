"""Integration smoke test against a live local Kafka broker for the product generator.

Requires `docker-compose up kafka` to be running on localhost:9092. Skips
itself if the broker is unreachable, mirroring
tests/kafka/test_merchant_generator_smoke.py.
"""

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from app.config.settings import settings
from app.generators.product import MerchantContext, ProductCatalogGenerator
from app.kafka.producer import EventProducer

import uuid


@pytest.fixture
async def started_producer():
    producer = EventProducer()
    try:
        await producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield producer
    await producer.stop()


async def test_generated_catalog_reaches_the_product_topic(started_producer: EventProducer):
    merchant_id = uuid.uuid4()
    ctx = MerchantContext(merchant_id=merchant_id, merchant_name="SmokeTestMerchant")
    generator = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=2,
        variants_per_product=1,
        seed=3,
    )
    envelopes = generator.generate_catalog()

    consumer = AIOKafkaConsumer(
        settings.kafka_product_events_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        for envelope in envelopes:
            key = f"{envelope.merchant_id}:{envelope.product_id}"
            await started_producer.publish(settings.kafka_product_events_topic, envelope, key=key)

        received = [(await consumer.getone()).value for _ in envelopes]

        assert received == [envelope.model_dump_json().encode("utf-8") for envelope in envelopes]
    finally:
        await consumer.stop()

