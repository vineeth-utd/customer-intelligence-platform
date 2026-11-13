import asyncio
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError, for_code

from app.config.settings import settings
from app.schemas.events.envelope import BaseEventEnvelope, DeadLetterRecord

logger = logging.getLogger(__name__)


def get_event_topics() -> tuple[str, ...]:
    """Return active platform event topics and DLQs based on current settings."""
    return (
        settings.kafka_merchant_events_topic,
        settings.kafka_merchant_dlq_topic,
        settings.kafka_shopper_events_topic,
        settings.kafka_shopper_dlq_topic,
        settings.kafka_campaign_events_topic,
        settings.kafka_campaign_dlq_topic,
        settings.kafka_product_events_topic,
        settings.kafka_product_dlq_topic,
    )


class _DynamicEventTopics:
    """Dynamic proxy for EVENT_TOPICS reflecting live settings (e.g. test isolation)."""

    def __iter__(self):
        return iter(get_event_topics())

    def __len__(self):
        return len(get_event_topics())

    def __contains__(self, item: object) -> bool:
        return item in get_event_topics()

    def __getitem__(self, item: int) -> str:
        return get_event_topics()[item]

    def __repr__(self) -> str:
        return repr(get_event_topics())


EVENT_TOPICS = _DynamicEventTopics()


class EventProducer:
    """Foundation Kafka producer: connects, provisions the domain event
    topics, and publishes validated event envelopes.

    No domain code calls publish() yet in Unit 3.1 - this is scaffolding for
    the merchant/shopper/campaign generator units.
    """

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        try:
            await producer.start()
        except Exception:
            await producer.stop()
            raise
        self._producer = producer
        await self._ensure_topics()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    @property
    def is_started(self) -> bool:
        return self._producer is not None

    async def publish(self, topic: str, envelope: BaseEventEnvelope, key: str | None = None) -> None:
        if self._producer is None:
            raise RuntimeError("EventProducer is not started; Kafka publishing is unavailable")
        value = envelope.model_dump_json().encode("utf-8")
        key_bytes = key.encode("utf-8") if key is not None else None
        await self._producer.send_and_wait(topic, value=value, key=key_bytes)

    async def publish_record(self, topic: str, record: DeadLetterRecord) -> None:
        if self._producer is None:
            raise RuntimeError("EventProducer is not started; Kafka publishing is unavailable")
        value = record.model_dump_json().encode("utf-8")
        await self._producer.send_and_wait(topic, value=value)

    async def _ensure_topics(self) -> None:
        admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
        await admin.start()
        try:
            new_topics = [
                NewTopic(
                    name=topic,
                    num_partitions=settings.kafka_default_partitions,
                    replication_factor=settings.kafka_default_replication_factor,
                )
                for topic in get_event_topics()
            ]
            try:
                response = await admin.create_topics(new_topics)
            except TopicAlreadyExistsError:
                return
            for entry in response.topic_errors:
                topic, error_code = entry[0], entry[1]
                if error_code == 0:
                    continue
                error_cls = for_code(error_code)
                if error_cls is TopicAlreadyExistsError:
                    continue
                logger.warning("Failed to create Kafka topic %s: %s", topic, error_cls.__name__)
        finally:
            await admin.close()


event_producer = EventProducer()


async def reset_kafka_topics(
    bootstrap_servers: str | None = None,
    num_partitions: int | None = None,
    replication_factor: int | None = None,
    topics: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Delete and recreate all platform event topics and DLQs to ensure a clean Kafka state."""
    servers = bootstrap_servers or settings.kafka_bootstrap_servers
    partitions = num_partitions if num_partitions is not None else settings.kafka_default_partitions
    replicas = replication_factor if replication_factor is not None else settings.kafka_default_replication_factor
    target_topics = list(topics) if topics is not None else list(get_event_topics())

    admin = AIOKafkaAdminClient(bootstrap_servers=servers)
    await admin.start()
    try:
        try:
            await admin.delete_topics(target_topics)
            logger.info("Deleted Kafka event topics: %s", target_topics)
        except Exception as e:
            logger.debug("Could not delete some Kafka topics: %s", e)

        # Allow broker time to finalize topic deletion
        await asyncio.sleep(1.0)

        new_topics = [
            NewTopic(name=topic, num_partitions=partitions, replication_factor=replicas)
            for topic in target_topics
        ]
        await admin.create_topics(new_topics)
        logger.info(
            "Recreated clean Kafka event topics (partitions=%d, replication_factor=%d).",
            partitions,
            replicas,
        )
    finally:
        await admin.close()

