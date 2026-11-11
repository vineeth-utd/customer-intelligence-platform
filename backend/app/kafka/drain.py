import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.structs import TopicPartition
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.models.event import CampaignEvent, MerchantEvent, ProductEvent, ShopperEvent

logger = logging.getLogger(__name__)

DOMAIN_KAFKA_MAPPING: dict[str, dict[str, str]] = {
    "merchant": {
        "topic": settings.kafka_merchant_events_topic,
        "group_id": settings.kafka_merchant_consumer_group_id,
        "table": "merchant_events",
    },
    "product": {
        "topic": settings.kafka_product_events_topic,
        "group_id": settings.kafka_product_consumer_group_id,
        "table": "product_events",
    },
    "shopper": {
        "topic": settings.kafka_shopper_events_topic,
        "group_id": settings.kafka_shopper_consumer_group_id,
        "table": "shopper_events",
    },
    "campaign": {
        "topic": settings.kafka_campaign_events_topic,
        "group_id": settings.kafka_campaign_consumer_group_id,
        "table": "campaign_events",
    },
}


async def capture_topic_end_offsets(
    bootstrap_servers: str | None = None,
) -> dict[str, dict[int, int]]:
    """Capture current high-water marks (log end offsets) for all canonical event topics.

    Returns a dict mapping topic -> {partition: end_offset}.
    """
    servers = bootstrap_servers or settings.kafka_bootstrap_servers
    consumer = AIOKafkaConsumer(bootstrap_servers=servers)
    await consumer.start()

    try:
        topic_end_offsets: dict[str, dict[int, int]] = {}
        partitions_to_query: list[TopicPartition] = []

        await consumer.topics()
        for domain, info in DOMAIN_KAFKA_MAPPING.items():
            topic = info["topic"]
            partitions = consumer.partitions_for_topic(topic) or {0}
            for p in partitions:
                partitions_to_query.append(TopicPartition(topic, p))

        if not partitions_to_query:
            return {}

        end_offsets_result = await consumer.end_offsets(partitions_to_query)
        for tp, offset in end_offsets_result.items():
            if tp.topic not in topic_end_offsets:
                topic_end_offsets[tp.topic] = {}
            topic_end_offsets[tp.topic][tp.partition] = offset

        return topic_end_offsets
    finally:
        try:
            await consumer.stop()
        except (asyncio.CancelledError, Exception):
            pass


async def get_consumer_group_offsets(
    group_id: str,
    bootstrap_servers: str | None = None,
) -> dict[TopicPartition, int]:
    """Retrieve committed offsets for a consumer group using AIOKafkaAdminClient."""
    servers = bootstrap_servers or settings.kafka_bootstrap_servers
    admin = AIOKafkaAdminClient(bootstrap_servers=servers)
    await admin.start()
    try:
        committed = await admin.list_consumer_group_offsets(group_id)
        return {tp: (om.offset if om is not None else 0) for tp, om in committed.items()}
    finally:
        try:
            await admin.close()
        except (asyncio.CancelledError, Exception):
            pass


async def check_consumer_offsets(
    target_offsets: dict[str, dict[int, int]],
    bootstrap_servers: str | None = None,
) -> tuple[bool, dict[str, int]]:
    """Check whether each consumer group has committed up to or past the target offsets.

    Returns:
        (is_fully_drained, lag_by_domain)
    """
    servers = bootstrap_servers or settings.kafka_bootstrap_servers
    admin = AIOKafkaAdminClient(bootstrap_servers=servers)
    await admin.start()

    try:
        lag_by_domain: dict[str, int] = {}
        all_drained = True

        for domain, info in DOMAIN_KAFKA_MAPPING.items():
            topic = info["topic"]
            group_id = info["group_id"]
            targets_for_topic = target_offsets.get(topic, {})

            if not targets_for_topic:
                lag_by_domain[domain] = 0
                continue

            try:
                committed_map = await admin.list_consumer_group_offsets(group_id)
            except Exception as e:
                logger.warning("Failed to fetch offsets for group %s: %s", group_id, e)
                lag_by_domain[domain] = sum(targets_for_topic.values())
                all_drained = False
                continue

            domain_lag = 0
            for partition, target_end in targets_for_topic.items():
                tp = TopicPartition(topic, partition)
                om = committed_map.get(tp)
                committed_offset = om.offset if om is not None else 0
                if committed_offset < target_end:
                    domain_lag += (target_end - committed_offset)

            lag_by_domain[domain] = domain_lag
            if domain_lag > 0:
                all_drained = False

        return all_drained, lag_by_domain
    finally:
        try:
            await admin.close()
        except (asyncio.CancelledError, Exception):
            pass


async def verify_no_unprocessed_events(session: AsyncSession) -> tuple[bool, dict[str, int]]:
    """Check database event log tables for any unprocessed event rows (processed == False).

    Returns:
        (is_clean, unprocessed_counts_by_domain)
    """
    unprocessed_counts: dict[str, int] = {}
    is_clean = True

    checks = [
        ("merchant", select(func.count()).select_from(MerchantEvent).where(MerchantEvent.processed.is_(False))),
        ("product", select(func.count()).select_from(ProductEvent).where(ProductEvent.processed.is_(False))),
        ("shopper", select(func.count()).select_from(ShopperEvent).where(ShopperEvent.processed.is_(False))),
        ("campaign", select(func.count()).select_from(CampaignEvent).where(CampaignEvent.processed.is_(False))),
    ]

    for domain, stmt in checks:
        count = await session.scalar(stmt) or 0
        unprocessed_counts[domain] = count
        if count > 0:
            is_clean = False

    return is_clean, unprocessed_counts


async def wait_for_drain(
    target_offsets: dict[str, dict[int, int]] | None = None,
    timeout: float = 120.0,
    poll_interval: float = 2.0,
    bootstrap_servers: str | None = None,
) -> None:
    """Wait until all consumer groups reach the target offsets and verify no unprocessed events remain.

    If target_offsets is None, captures current end offsets as target.
    """
    if target_offsets is None:
        target_offsets = await capture_topic_end_offsets(bootstrap_servers=bootstrap_servers)

    logger.info("Waiting for consumer drain against target offsets: %s", target_offsets)
    deadline = asyncio.get_running_loop().time() + timeout

    while True:
        is_drained, lag_by_domain = await check_consumer_offsets(
            target_offsets=target_offsets,
            bootstrap_servers=bootstrap_servers,
        )

        if is_drained:
            logger.info("Kafka consumer groups reached target offsets. Verifying database event log...")
            async with AsyncSessionLocal() as session:
                is_clean, unprocessed = await verify_no_unprocessed_events(session)
                if not is_clean:
                    raise RuntimeError(
                        f"Kafka offsets drained, but database contains unprocessed events: {unprocessed}"
                    )
            logger.info("Consumer drain and event processing verified successfully.")
            return

        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise TimeoutError(
                f"Consumer drain timed out after {timeout}s. Remaining lag by domain: {lag_by_domain}"
            )

        logger.info("Consumer lag remaining: %s. Polling again in %.1fs...", lag_by_domain, poll_interval)
        await asyncio.sleep(min(poll_interval, remaining))
