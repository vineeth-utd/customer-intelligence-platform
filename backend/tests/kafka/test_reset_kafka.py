"""Unit tests for Kafka topic resetting."""

from unittest.mock import AsyncMock, patch
import pytest

from app.kafka.producer import EVENT_TOPICS, reset_kafka_topics


@pytest.mark.asyncio
async def test_reset_kafka_topics_deletes_and_recreates_topics():
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
        created_names = {t.name for t in created_topics}
        assert created_names == set(EVENT_TOPICS)
        mock_admin.close.assert_called_once()

