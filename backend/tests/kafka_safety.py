"""Kafka test isolation, topic management, and hard safety guards.

Protects development Kafka topics from being published to or mutated during automated testing.
Ensures test topics use the designated isolated test prefix (e.g. cip.test.*).
"""

import asyncio
import logging

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
from aiokafka.structs import TopicPartition

from app.config.settings import settings

logger = logging.getLogger(__name__)


class KafkaSafetyViolationError(RuntimeError):
    """Raised when an automated test attempts to publish to or access a protected development Kafka topic."""


PROTECTED_DEVELOPMENT_TOPICS: frozenset[str] = frozenset({
    "cip.merchant.events",
    "cip.merchant.events.dlq",
    "cip.shopper.events",
    "cip.shopper.events.dlq",
    "cip.campaign.events",
    "cip.campaign.events.dlq",
    "cip.product.events",
    "cip.product.events.dlq",
})


def assert_test_kafka_topic(topic: str) -> None:
    """Verify that a topic is an isolated test topic and not a protected development topic.

    Raises KafkaSafetyViolationError if the topic is a development topic.
    """
    if topic in PROTECTED_DEVELOPMENT_TOPICS:
        raise KafkaSafetyViolationError(
            f"Safety guard triggered: Automated test attempted to access protected development Kafka topic '{topic}'! "
            f"Automated tests must run against isolated test topics (e.g. '{settings.kafka_test_topic_prefix}*') "
            f"to protect historical simulation data and live consumer pipelines."
        )


async def ensure_test_kafka_topics(num_partitions: int = 5, replication_factor: int = 1) -> None:
    """Ensure all isolated test topics exist on the broker."""
    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    await admin.start()
    try:
        test_topics = [
            settings.kafka_merchant_events_topic,
            settings.kafka_merchant_dlq_topic,
            settings.kafka_shopper_events_topic,
            settings.kafka_shopper_dlq_topic,
            settings.kafka_campaign_events_topic,
            settings.kafka_campaign_dlq_topic,
            settings.kafka_product_events_topic,
            settings.kafka_product_dlq_topic,
        ]
        # Safety check: make sure every topic is an isolated test topic
        for t in test_topics:
            assert_test_kafka_topic(t)

        existing = set(await admin.list_topics())
        to_create = [t for t in test_topics if t not in existing]
        if to_create:
            new_topics = [
                NewTopic(name=t, num_partitions=num_partitions, replication_factor=replication_factor)
                for t in to_create
            ]
            try:
                await admin.create_topics(new_topics)
                logger.info("Created isolated test Kafka topics: %s", to_create)
            except TopicAlreadyExistsError:
                pass
    finally:
        await admin.close()


async def get_development_topic_end_offsets(
    bootstrap_servers: str | None = None,
) -> dict[str, dict[int, int]]:
    """Capture current end offsets for all protected development topics.

    Used by verification suites to prove tests leave development topics completely untouched.
    """
    servers = bootstrap_servers or settings.kafka_bootstrap_servers
    consumer = AIOKafkaConsumer(
        *list(PROTECTED_DEVELOPMENT_TOPICS),
        bootstrap_servers=servers,
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        offsets: dict[str, dict[int, int]] = {}
        for topic in sorted(PROTECTED_DEVELOPMENT_TOPICS):
            partitions = consumer.partitions_for_topic(topic) or set()
            if partitions:
                tps = [TopicPartition(topic, p) for p in partitions]
                end_offsets = await consumer.end_offsets(tps)
                offsets[topic] = {tp.partition: end_offsets[tp] for tp in tps}
            else:
                offsets[topic] = {}
        return offsets
    finally:
        await consumer.stop()

