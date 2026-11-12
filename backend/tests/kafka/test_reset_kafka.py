"""Unit tests for Kafka topic provisioning and resetting."""

from unittest.mock import AsyncMock, patch
import pytest

from app.config.settings import settings
from app.kafka.producer import EVENT_TOPICS, EventProducer, reset_kafka_topics


@pytest.mark.asyncio
async def test_reset_kafka_topics_defaults_to_settings():
    mock_admin = AsyncMock()

    with (
        patch("app.kafka.producer.AIOKafkaAdminClient", return_value=mock_admin),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await reset_kafka_topics("localhost:9092")

        mock_admin.start.assert_called_once()
        mock_admin.delete_topics.assert_called_once_with(list(EVENT_TOPICS))
        mock_sleep.assert_called_once_with(1.0)
        mock_admin.create_topics.assert_called_once()
        created_topics = mock_admin.create_topics.call_args[0][0]
        assert len(created_topics) == len(EVENT_TOPICS)
        for t in created_topics:
            assert t.num_partitions == settings.kafka_default_partitions
            assert t.replication_factor == settings.kafka_default_replication_factor
        mock_admin.close.assert_called_once()


@pytest.mark.asyncio
async def test_reset_kafka_topics_with_explicit_overrides():
    mock_admin = AsyncMock()

    with (
        patch("app.kafka.producer.AIOKafkaAdminClient", return_value=mock_admin),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await reset_kafka_topics("localhost:9092", num_partitions=4, replication_factor=2)

        created_topics = mock_admin.create_topics.call_args[0][0]
        for t in created_topics:
            assert t.num_partitions == 4
            assert t.replication_factor == 2


@pytest.mark.asyncio
async def test_ensure_topics_uses_settings():
    mock_admin = AsyncMock()
    producer = EventProducer()

    with patch("app.kafka.producer.AIOKafkaAdminClient", return_value=mock_admin):
        await producer._ensure_topics()

        created_topics = mock_admin.create_topics.call_args[0][0]
        assert len(created_topics) == len(EVENT_TOPICS)
        for t in created_topics:
            assert t.num_partitions == settings.kafka_default_partitions
            assert t.replication_factor == settings.kafka_default_replication_factor
