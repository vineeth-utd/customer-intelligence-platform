import logging

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord
from pydantic import ValidationError

from app.config.settings import settings
from app.data_access.merchant_events import insert_merchant_event
from app.db.session import AsyncSessionLocal
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.registry import get_payload_schema

logger = logging.getLogger(__name__)


class MerchantEventConsumer:
    """Foundation Kafka consumer for the merchant event topic.

    Validates each incoming message against the versioned envelope/payload
    contracts and persists accepted events into merchant_events with their
    initial (unprocessed) state. Deterministic business-service routing,
    operational-table updates, and processed-state completion are out of
    scope here (Unit 3.4).

    Offset commits are deferred entirely to Unit 3.4: this class never calls
    commit(), so every run re-reads the full topic from the beginning. That
    is safe because persistence is idempotent (event_id is the
    merchant_events primary key), and it avoids advancing offsets in a way
    that would let 3.4's business processing silently miss events that were
    persisted here but never actually business-processed.
    """

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        consumer = AIOKafkaConsumer(
            settings.kafka_merchant_events_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_merchant_consumer_group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
        except Exception:
            await consumer.stop()
            raise
        self._consumer = consumer

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    @property
    def is_started(self) -> bool:
        return self._consumer is not None

    async def run_forever(self) -> None:
        if self._consumer is None:
            raise RuntimeError("MerchantEventConsumer is not started; cannot consume messages")
        async for message in self._consumer:
            await self._handle_message(message)

    async def _handle_message(self, message: ConsumerRecord) -> None:
        envelope = self._validate(message)
        if envelope is None:
            return

        async with AsyncSessionLocal() as session:
            inserted = await insert_merchant_event(session, envelope)

        if inserted:
            logger.info("Persisted merchant event %s (%s)", envelope.event_id, envelope.event_type.value)
        else:
            logger.info("Skipped duplicate merchant event %s (%s)", envelope.event_id, envelope.event_type.value)

    def _validate(self, message: ConsumerRecord) -> MerchantEventEnvelope | None:
        try:
            envelope = MerchantEventEnvelope.model_validate_json(message.value)
        except ValidationError:
            logger.error(
                "Rejected malformed merchant event message at %s[%s]@%s",
                message.topic,
                message.partition,
                message.offset,
                exc_info=True,
            )
            return None

        payload_schema = get_payload_schema(envelope.event_type.value, envelope.event_version)
        if payload_schema is None:
            logger.error(
                "Rejected merchant event %s: no registered payload schema for (%s, %d)",
                envelope.event_id,
                envelope.event_type.value,
                envelope.event_version,
            )
            return None

        try:
            payload_schema.model_validate(envelope.payload)
        except ValidationError:
            logger.error(
                "Rejected merchant event %s: payload does not match schema for (%s, %d)",
                envelope.event_id,
                envelope.event_type.value,
                envelope.event_version,
                exc_info=True,
            )
            return None

        return envelope


merchant_event_consumer = MerchantEventConsumer()
