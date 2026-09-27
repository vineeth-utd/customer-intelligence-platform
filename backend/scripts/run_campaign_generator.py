"""Standalone entrypoint for the synthetic campaign event generator.

Loads active merchants, segments, shoppers, and orders to construct context.
Periodically refreshes context to discover new shoppers and orders.
Generates deterministic campaign lifecycle events (draft -> active -> completed)
and channel engagement flows (delivery -> open -> click -> convert).

Usage (from backend/):
    uv run python -m scripts.run_campaign_generator \
        [--concurrency-per-merchant N] \
        [--interval-seconds S] \
        [--refresh-interval-seconds S] \
        [--seed N]
"""

import argparse
import asyncio
import logging
import uuid
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.data_access.merchant import list_installed_merchants
from app.data_access.segment import get_merchant_segments
from app.data_access.shopper import list_merchant_shoppers
from app.data_access.order import list_merchant_orders
from app.generators.campaign import CampaignLifecycleGenerator, MerchantContext, OrderContext
from app.kafka.producer import event_producer
from app.schemas.events.envelope import CampaignEventEnvelope

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic campaign lifecycle event generator.")
    parser.add_argument("--concurrency-per-merchant", type=int, default=2)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--refresh-interval-seconds", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


async def _load_merchant_context(session: AsyncSession, merchant_id: uuid.UUID) -> MerchantContext:
    segments = await get_merchant_segments(session, merchant_id)
    shopper_ids = await list_merchant_shoppers(session, merchant_id)
    orders = await list_merchant_orders(session, merchant_id)
    
    order_contexts = [
        OrderContext(order_id=o.order_id, shopper_id=o.shopper_id, placed_at=o.placed_at) 
        for o in orders
    ]
    
    return MerchantContext(
        merchant_id=merchant_id,
        segment_ids=[s.segment_id for s in segments],
        shopper_ids=shopper_ids,
        orders=order_contexts,
    )


async def _publish_all(envelopes: list[CampaignEventEnvelope]) -> None:
    for envelope in envelopes:
        # Key by campaign_id to ensure ordering per campaign
        await event_producer.publish(settings.kafka_campaign_events_topic, envelope, key=str(envelope.campaign_id))


async def _load_all_contexts() -> list[MerchantContext]:
    contexts = []
    async with AsyncSessionLocal() as session:
        merchants = await list_installed_merchants(session)
        for merchant in merchants:
            ctx = await _load_merchant_context(session, merchant.merchant_id)
            if not ctx.segment_ids:
                logger.warning(f"Merchant {merchant.merchant_id} has no initialized segments. Campaigns will not spawn.")
            contexts.append(ctx)
    return contexts


async def _run(concurrency: int, interval_seconds: float, refresh_interval_seconds: float, seed: int | None) -> None:
    generator = CampaignLifecycleGenerator(concurrency_per_merchant=concurrency, seed=seed)

    contexts = await _load_all_contexts()
    if not contexts:
        logger.warning("No installed merchants found. Exiting.")
        sys.exit(0)
        
    generator.update_contexts(contexts)
    logger.info(f"Loaded context for {len(contexts)} merchants.")

    await event_producer.start()
    try:
        last_refresh = asyncio.get_running_loop().time()
        
        while True:
            now = asyncio.get_running_loop().time()
            if now - last_refresh >= refresh_interval_seconds:
                new_contexts = await _load_all_contexts()
                generator.update_contexts(new_contexts)
                last_refresh = now
                logger.info("Refreshed DB context for generator.")

            await asyncio.sleep(interval_seconds)
            
            envelopes = generator.tick()
            if envelopes:
                await _publish_all(envelopes)
                logger.info(f"Published {len(envelopes)} campaign events")
                
    finally:
        await event_producer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    try:
        asyncio.run(_run(args.concurrency_per_merchant, args.interval_seconds, args.refresh_interval_seconds, args.seed))
    except KeyboardInterrupt:
        logger.info("Campaign generator stopped by user")


if __name__ == "__main__":
    main()
