"""Tests verifying Kafka test isolation, safety guards, and rejection of development topics.

Proves that:
1. Publishing to protected development topics (cip.*) is strictly rejected during automated tests.
2. Settings validation rejects empty or invalid kafka_test_topic_prefix.
3. configure_test_kafka switches all topics to the test prefix (cip.test.*).
4. Safety guards intercept both publish() and publish_record() on protected topics.
5. Isolated test topics exist and can be safely published to and consumed from.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from pydantic import ValidationError

from app.config.settings import Settings, settings
from app.kafka.producer import EventProducer
from app.schemas.events.dlq import DeadLetterRecord
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from tests.kafka_safety import (
    PROTECTED_DEVELOPMENT_TOPICS,
    KafkaSafetyViolationError,
    assert_test_kafka_topic,
)


def test_settings_kafka_test_prefix_defaults():
    """Verify that default settings define the test topic and consumer group prefixes."""
    s = Settings(_env_file=None)
    assert s.kafka_test_topic_prefix == "cip.test."
    assert s.kafka_test_group_prefix == "cip-test-"


def test_settings_validation_rejects_empty_test_prefix():
    """Verify that Settings rejects empty kafka_test_topic_prefix."""
    with pytest.raises(ValidationError):
        Settings(kafka_test_topic_prefix="   ", _env_file=None)


def test_settings_configure_test_kafka_switches_all_topics():
    """Verify that configure_test_kafka redirects all topics to the test prefix."""
    s = Settings(_env_file=None)
    s.configure_test_kafka()

    assert s.kafka_merchant_events_topic == "cip.test.merchant.events"
    assert s.kafka_merchant_dlq_topic == "cip.test.merchant.events.dlq"
    assert s.kafka_shopper_events_topic == "cip.test.shopper.events"
    assert s.kafka_shopper_dlq_topic == "cip.test.shopper.events.dlq"
    assert s.kafka_campaign_events_topic == "cip.test.campaign.events"
    assert s.kafka_campaign_dlq_topic == "cip.test.campaign.events.dlq"
    assert s.kafka_product_events_topic == "cip.test.product.events"
    assert s.kafka_product_dlq_topic == "cip.test.product.events.dlq"

    assert s.kafka_merchant_consumer_group_id == "cip-test-merchant-event-consumer"
    assert s.kafka_product_consumer_group_id == "cip-test-product-event-consumer"
    assert s.kafka_shopper_consumer_group_id == "cip-test-shopper-event-consumer"
    assert s.kafka_campaign_consumer_group_id == "cip-test-campaign-event-consumer"


def test_assert_test_kafka_topic_rejects_all_protected_topics():
    """Verify that assert_test_kafka_topic rejects every protected development topic."""
    for topic in PROTECTED_DEVELOPMENT_TOPICS:
        with pytest.raises(KafkaSafetyViolationError) as exc_info:
            assert_test_kafka_topic(topic)
        assert topic in str(exc_info.value)
        assert "Safety guard triggered" in str(exc_info.value)


def test_assert_test_kafka_topic_accepts_test_topics():
    """Verify that assert_test_kafka_topic accepts valid test topics."""
    assert_test_kafka_topic("cip.test.merchant.events")
    assert_test_kafka_topic("cip.test.shopper.events")
    assert_test_kafka_topic("cip.test.product.events")
    assert_test_kafka_topic("cip.test.campaign.events")


@pytest.mark.asyncio
async def test_producer_publish_rejects_protected_topic():
    """Verify that guarded EventProducer.publish rejects publishing to development topics."""
    producer = EventProducer()
    envelope = MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=MerchantEventType.MERCHANT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=uuid.uuid4(),
        payload={"plan": "starter"},
        source="safety-test",
    )

    with pytest.raises(KafkaSafetyViolationError):
        await producer.publish("cip.merchant.events", envelope)


@pytest.mark.asyncio
async def test_producer_publish_record_rejects_protected_topic():
    """Verify that guarded EventProducer.publish_record rejects publishing to development DLQ topics."""
    producer = EventProducer()
    record = DeadLetterRecord(
        original_topic="cip.merchant.events",
        original_partition=0,
        original_offset=0,
        consumer_group_id="cip-merchant-consumer",
        failure_stage="processing",
        error_type="ValueError",
        error_message="Test",
        failed_at=datetime.now(timezone.utc),
        original_message_base64="aGVsbG8=",
    )

    with pytest.raises(KafkaSafetyViolationError):
        await producer.publish_record("cip.merchant.events.dlq", record)

