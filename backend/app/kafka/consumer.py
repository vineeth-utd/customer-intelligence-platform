import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Generic, Literal, TypeVar

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord, OffsetAndMetadata, TopicPartition
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.data_access.campaign_events import get_campaign_event, insert_campaign_event, mark_campaign_event_processed
from app.data_access.merchant_events import get_merchant_event, insert_merchant_event, mark_merchant_event_processed
from app.data_access.product_events import get_product_event, insert_product_event, mark_product_event_processed
from app.data_access.shopper_events import get_shopper_event, insert_shopper_event, mark_shopper_event_processed
from app.db.session import AsyncSessionLocal
from app.schemas.events.envelope import (
    CampaignEventEnvelope,
    MerchantEventEnvelope,
    ProductEventEnvelope,
    ShopperEventEnvelope,
)
from app.schemas.events.registry import get_payload_schema
from app.services.merchant import process_merchant_event
from app.services.product import process_product_event
from app.services.shopper import process_shopper_event
from app.services.campaign import process_campaign_event

logger = logging.getLogger(__name__)

EnvelopeT = TypeVar("EnvelopeT", bound=BaseModel)

class BaseEventConsumer(Generic[EnvelopeT]):
    """Base Kafka consumer for event topics.

    Per message: validate -> persist into event log (own committed
    transaction) -> if not already processed, run domain business
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
    the primary key) and business handlers are idempotent state-setters,
    so reprocessing an unfinished event is harmless.
    """

    def __init__(
        self,
        topic: str,
        group_id: str,
        envelope_model: type[EnvelopeT],
        insert_event_fn: Callable[[AsyncSession, EnvelopeT], Awaitable[bool]],
        get_event_fn: Callable[[AsyncSession, uuid.UUID], Awaitable[Any]],
        process_event_fn: Callable[[AsyncSession, EnvelopeT], Awaitable[None]] | None = None,
        mark_processed_fn: Callable[[AsyncSession, uuid.UUID, datetime], Awaitable[None]] | None = None,
        domain_name: str = "",
        dlq_topic: str | None = None,
        business_exceptions: tuple[type[Exception], ...] = (),
    ) -> None:
        self._topic = topic
        self._group_id = group_id
        self._envelope_model = envelope_model
        self._insert_event_fn = insert_event_fn
        self._get_event_fn = get_event_fn
        self._process_event_fn = process_event_fn
        self._mark_processed_fn = mark_processed_fn
        self._domain_name = domain_name
        self._dlq_topic = dlq_topic
        self._business_exceptions = business_exceptions
        self._consumer: AIOKafkaConsumer | None = None

    def get_context_id(self, envelope: EnvelopeT) -> uuid.UUID:
        raise NotImplementedError

    async def start(self) -> None:
        consumer = AIOKafkaConsumer(
            self._topic,
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
            raise RuntimeError(f"{self.__class__.__name__} is not started; cannot consume messages")
        async for message in self._consumer:
            await self._handle_message(message)

    async def _handle_message(self, message: ConsumerRecord) -> None:
        envelope = self._validate(message)
        if envelope is None:
            if self._dlq_topic:
                await self._publish_dlq(
                    message,
                    failure_stage="validation",
                    error_type="ValidationError",
                    error_message="Message failed schema validation",
                )
            await self._commit_message(message)
            return

        async with AsyncSessionLocal() as session:
            inserted = await self._insert_event_fn(session, envelope)

        if inserted:
            logger.info("Persisted %s event %s (%s)", self._domain_name, envelope.event_id, getattr(envelope.event_type, "value", envelope.event_type))
        else:
            logger.info("Skipped duplicate %s event %s (%s)", self._domain_name, envelope.event_id, getattr(envelope.event_type, "value", envelope.event_type))

        if self._process_event_fn is None or self._mark_processed_fn is None:
            return

        async with AsyncSessionLocal() as session:
            existing = await self._get_event_fn(session, envelope.event_id)
            already_processed = existing is not None and existing.processed

        if already_processed:
            logger.info("Skipped already-processed %s event %s (%s)", self._domain_name, envelope.event_id, getattr(envelope.event_type, "value", envelope.event_type))
        else:
            try:
                async with AsyncSessionLocal() as session:
                    await self._process_event_fn(session, envelope)
                    await self._mark_processed_fn(session, envelope.event_id, datetime.now(timezone.utc))
                    await session.commit()
            except self._business_exceptions as e:
                if self._dlq_topic:
                    logger.warning(
                        "Business processing failed for %s event %s (%s); publishing to DLQ",
                        self._domain_name,
                        envelope.event_id,
                        getattr(envelope.event_type, "value", envelope.event_type),
                    )
                    await self._publish_dlq(
                        message,
                        failure_stage="processing",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        event_id=envelope.event_id,
                        event_type=getattr(envelope.event_type, "value", envelope.event_type),
                    )
                else:
                    raise
            except Exception:
                context_id = self.get_context_id(envelope)
                logger.error(
                    "Failed to process %s event %s (%s) for context %s; offset not committed",
                    self._domain_name,
                    envelope.event_id,
                    getattr(envelope.event_type, "value", envelope.event_type),
                    context_id,
                    exc_info=True,
                )
                raise
            else:
                logger.info("Processed %s event %s (%s)", self._domain_name, envelope.event_id, getattr(envelope.event_type, "value", envelope.event_type))

        await self._commit_message(message)

    async def _publish_dlq(
        self,
        message: ConsumerRecord,
        failure_stage: Literal["validation", "processing"],
        error_type: str,
        error_message: str,
        event_id: uuid.UUID | None = None,
        event_type: str | None = None,
    ) -> None:
        if not self._dlq_topic:
            return

        from app.kafka.producer import event_producer
        from app.schemas.events.envelope import DeadLetterRecord

        if failure_stage == "validation" and (event_id is None or event_type is None):
            try:
                raw = json.loads(message.value)
                if isinstance(raw, dict):
                    if event_id is None:
                        raw_id = raw.get("event_id")
                        if raw_id:
                            event_id = uuid.UUID(str(raw_id))
                    if event_type is None:
                        event_type = raw.get("event_type")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                pass

        b64_msg = base64.b64encode(message.value).decode("ascii")

        record = DeadLetterRecord(
            original_topic=message.topic,
            original_partition=message.partition,
            original_offset=message.offset,
            consumer_group_id=self._group_id,
            failure_stage=failure_stage,
            error_type=error_type,
            error_message=error_message,
            failed_at=datetime.now(timezone.utc),
            original_message_base64=b64_msg,
            original_event_id=event_id,
            event_type=event_type,
        )

        await event_producer.publish_dlq(self._dlq_topic, record)

    async def _commit_message(self, message: ConsumerRecord) -> None:
        if self._consumer is None:
            raise RuntimeError(f"{self.__class__.__name__} is not started; cannot commit offsets")
        topic_partition = TopicPartition(message.topic, message.partition)
        await self._consumer.commit({topic_partition: OffsetAndMetadata(message.offset + 1, "")})

    def _validate(self, message: ConsumerRecord) -> EnvelopeT | None:
        try:
            envelope = self._envelope_model.model_validate_json(message.value)
        except ValidationError:
            logger.error(
                "Rejected malformed %s event message at %s[%s]@%s",
                self._domain_name,
                message.topic,
                message.partition,
                message.offset,
                exc_info=True,
            )
            return None

        event_type_val = getattr(envelope.event_type, "value", envelope.event_type)
        payload_schema = get_payload_schema(event_type_val, envelope.event_version)
        if payload_schema is None:
            logger.error(
                "Rejected %s event %s: no registered payload schema for (%s, %d)",
                self._domain_name,
                envelope.event_id,
                event_type_val,
                envelope.event_version,
            )
            return None

        try:
            payload_schema.model_validate(envelope.payload)
        except ValidationError:
            logger.error(
                "Rejected %s event %s: payload does not match schema for (%s, %d)",
                self._domain_name,
                envelope.event_id,
                event_type_val,
                envelope.event_version,
                exc_info=True,
            )
            return None

        return envelope

class MerchantEventConsumer(BaseEventConsumer[MerchantEventEnvelope]):
    """Kafka consumer for the merchant event topic."""
    def __init__(self, *, group_id: str | None = None) -> None:
        super().__init__(
            topic=settings.kafka_merchant_events_topic,
            group_id=group_id or settings.kafka_merchant_consumer_group_id,
            envelope_model=MerchantEventEnvelope,
            insert_event_fn=insert_merchant_event,
            get_event_fn=get_merchant_event,
            process_event_fn=process_merchant_event,
            mark_processed_fn=mark_merchant_event_processed,
            domain_name="merchant",
        )

    def get_context_id(self, envelope: MerchantEventEnvelope) -> uuid.UUID:
        return envelope.merchant_id

merchant_event_consumer = MerchantEventConsumer()


class ProductEventConsumer(BaseEventConsumer[ProductEventEnvelope]):
    """Kafka consumer for the product event topic."""
    def __init__(self, *, group_id: str | None = None) -> None:
        super().__init__(
            topic=settings.kafka_product_events_topic,
            group_id=group_id or settings.kafka_product_consumer_group_id,
            envelope_model=ProductEventEnvelope,
            insert_event_fn=insert_product_event,
            get_event_fn=get_product_event,
            process_event_fn=process_product_event,
            mark_processed_fn=mark_product_event_processed,
            domain_name="product",
        )

    def get_context_id(self, envelope: ProductEventEnvelope) -> uuid.UUID:
        return envelope.product_id

product_event_consumer = ProductEventConsumer()


class ShopperEventConsumer(BaseEventConsumer[ShopperEventEnvelope]):
    """Kafka consumer for the shopper event topic."""
    def __init__(self, *, group_id: str | None = None) -> None:
        super().__init__(
            topic=settings.kafka_shopper_events_topic,
            group_id=group_id or settings.kafka_shopper_consumer_group_id,
            envelope_model=ShopperEventEnvelope,
            insert_event_fn=insert_shopper_event,
            get_event_fn=get_shopper_event,
            process_event_fn=process_shopper_event,
            mark_processed_fn=mark_shopper_event_processed,
            domain_name="shopper",
        )

    def get_context_id(self, envelope: ShopperEventEnvelope) -> uuid.UUID:
        return envelope.shopper_id

shopper_event_consumer = ShopperEventConsumer()


class CampaignEventConsumer(BaseEventConsumer[CampaignEventEnvelope]):
    """Kafka consumer for the campaign event topic."""
    def __init__(self, *, group_id: str | None = None) -> None:
        super().__init__(
            topic=settings.kafka_campaign_events_topic,
            group_id=group_id or settings.kafka_campaign_consumer_group_id,
            envelope_model=CampaignEventEnvelope,
            insert_event_fn=insert_campaign_event,
            get_event_fn=get_campaign_event,
            process_event_fn=process_campaign_event,
            mark_processed_fn=mark_campaign_event_processed,
            domain_name="campaign",
        )

    def get_context_id(self, envelope: CampaignEventEnvelope) -> uuid.UUID:
        return envelope.campaign_id

campaign_event_consumer = CampaignEventConsumer()

