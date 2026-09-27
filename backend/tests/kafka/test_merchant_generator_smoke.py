"""Integration smoke test against a live local Kafka broker for the merchant generator.

Requires `docker-compose up kafka` to be running on localhost:9092. Skips
itself if the broker is unreachable, mirroring tests/kafka/test_producer_smoke.py.
"""

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from app.config.settings import settings
from app.generators.merchant import MerchantLifecycleGenerator
from app.kafka.producer import EventProducer


@pytest.fixture
async def started_producer():
    producer = EventProducer()
    try:
        await producer.start()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable at localhost:9092")
    yield producer
    await producer.stop()


async def test_generated_population_reaches_the_merchant_topic(started_producer: EventProducer):
    generator = MerchantLifecycleGenerator(population_size=2, seed=3)
    envelopes = generator.generate_population()

    consumer = AIOKafkaConsumer(
        settings.kafka_merchant_events_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        for envelope in envelopes:
            await started_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))

        received = [(await consumer.getone()).value for _ in envelopes]

        assert received == [envelope.model_dump_json().encode("utf-8") for envelope in envelopes]
    finally:
        await consumer.stop()
