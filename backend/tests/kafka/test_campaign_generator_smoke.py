"""Integration smoke test against a live local Kafka broker for the campaign generator.

Requires `docker-compose up kafka` to be running on localhost:9092.
"""

import uuid
import pytest
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from app.config.settings import settings
from app.generators.campaign import CampaignLifecycleGenerator, MerchantContext
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


async def test_generated_campaign_reaches_the_campaign_topic(started_producer: EventProducer):
    merchant_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    
    ctx = MerchantContext(
        merchant_id=merchant_id,
        segment_ids=[segment_id],
        shopper_ids=[shopper_id],
        orders=[],
    )

    generator = CampaignLifecycleGenerator(concurrency_per_merchant=1, seed=42)
    generator.update_contexts([ctx])
    
    envelopes = []
    # Force at least one event
    for _ in range(50):
        envs = generator.tick()
        envelopes.extend(envs)
        if envs:
            break
            
    assert len(envelopes) > 0

    consumer = AIOKafkaConsumer(
        settings.kafka_campaign_events_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        for envelope in envelopes:
            await started_producer.publish(settings.kafka_campaign_events_topic, envelope, key=str(envelope.campaign_id))

        received = [(await consumer.getone()).value for _ in envelopes]
        assert received == [envelope.model_dump_json().encode("utf-8") for envelope in envelopes]
    finally:
        await consumer.stop()

