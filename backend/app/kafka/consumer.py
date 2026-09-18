import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord, OffsetAndMetadata, TopicPartition
from pydantic import ValidationError

from app.config.settings import settings
from app.data_access.merchant_events import get_merchant_event, insert_merchant_event, mark_merchant_event_processed
from app.db.session import AsyncSessionLocal
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.registry import get_payload_schema
from app.services.merchant import process_merchant_event

logger = logging.getLogger(__name__)


class MerchantEventConsumer:
    """Kafka consumer for the merchant event topic.

    Per message: validate -> persist into merchant_events (own committed
    transaction) -> if not already processed, run Merchant business
    processing and mark processed=true/processed_at in one transaction ->
    commit the Kafka offset for that message.

    A message that fails validation can never succeed on redelivery, so it
    is logged and its offset is committed past (forward progress). A
    message that fails business processing is logged and re-raised without
    committing its offset - the consumer stops rather than skipping ahead,
    since Kafka's per-partition offset commit is a single monotonic
    watermark and there is no dead-letter mechanism to preserve the ability
    to redeliver a skipped message later. Restarting the consumer resumes
    from the last committed offset, redelivering the failed message.
    Redelivery in general is safe: persistence is idempotent (event_id is
    the merchant_events primary key) and 3.4B's handlers are idempotent
    state-setters, so reprocessing an unfinished event is harmless.
    """

    def __init__(self, *, group_id: str | None = None) -> None:
        self._group_id = group_id or settings.kafka_merchant_consumer_group_id
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        consumer = AIOKafkaConsumer(
            settings.kafka_merchant_events_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self._group_id,
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
            # Malformed/unregistered messages can never succeed on
            # redelivery - commit past them so a poison message doesn't
            # block the partition indefinitely.
            await self._commit_message(message)
            return

        async with AsyncSessionLocal() as session:
            inserted = await insert_merchant_event(session, envelope)

        if inserted:
            logger.info("Persisted merchant event %s (%s)", envelope.event_id, envelope.event_type.value)
        else:
            logger.info("Skipped duplicate merchant event %s (%s)", envelope.event_id, envelope.event_type.value)

        async with AsyncSessionLocal() as session:
            existing = await get_merchant_event(session, envelope.event_id)
            already_processed = existing is not None and existing.processed

        if already_processed:
            logger.info("Skipped already-processed merchant event %s (%s)", envelope.event_id, envelope.event_type.value)
        else:
            try:
                async with AsyncSessionLocal() as session:
                    await process_merchant_event(session, envelope)
                    await mark_merchant_event_processed(session, envelope.event_id, datetime.now(timezone.utc))
                    await session.commit()
            except Exception:
                logger.error(
                    "Failed to process merchant event %s (%s) for merchant %s; offset not committed",
                    envelope.event_id,
                    envelope.event_type.value,
                    envelope.merchant_id,
                    exc_info=True,
                )
                raise
            logger.info("Processed merchant event %s (%s)", envelope.event_id, envelope.event_type.value)

        await self._commit_message(message)

    async def _commit_message(self, message: ConsumerRecord) -> None:
        if self._consumer is None:
            raise RuntimeError("MerchantEventConsumer is not started; cannot commit offsets")
        topic_partition = TopicPartition(message.topic, message.partition)
        await self._consumer.commit({topic_partition: OffsetAndMetadata(message.offset + 1, "")})

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
