import logging

from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError, for_code

from app.config.settings import settings
from app.schemas.events.envelope import BaseEventEnvelope

logger = logging.getLogger(__name__)

EVENT_TOPICS = (
    settings.kafka_merchant_events_topic,
    settings.kafka_shopper_events_topic,
    settings.kafka_campaign_events_topic,
    settings.kafka_product_events_topic,
)


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

    async def _ensure_topics(self) -> None:
        admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
        await admin.start()
        try:
            new_topics = [NewTopic(name=topic, num_partitions=1, replication_factor=1) for topic in EVENT_TOPICS]
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
