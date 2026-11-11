"""Standalone entrypoint for the unified synthetic historical simulation engine.

Generates a globally interleaved, causally ordered business event timeline covering
Merchants, Products, Campaigns, and Shoppers across a historical interval, and publishes
all validated envelopes chronologically to Kafka.

Usage (from backend/):
    uv run python -m scripts.run_simulation \\
        --mode historical \\
        --start-date 2026-08-01 \\
        --end-date 2026-11-01 \\
        [--seed 42] \\
        [--merchants 5] \\
        [--products-per-merchant 8] \\
        [--variants-per-product 3] \\
        [--shoppers-per-merchant 50] \\
        [--campaigns-per-merchant 3]
"""

import argparse
import asyncio
from datetime import date, datetime, time, timezone
import logging
import sys

from app.config.settings import settings
from app.generators.config import HistoricalSimulationConfig
from app.generators.historical_orchestrator import HistoricalSimulationOrchestrator
from app.kafka.producer import event_producer
from app.schemas.events.envelope import (
    BaseEventEnvelope,
    CampaignEventEnvelope,
    MerchantEventEnvelope,
    ProductEventEnvelope,
    ShopperEventEnvelope,
)

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified Customer Intelligence Platform Historical Simulation Runner")
    parser.add_argument(
        "--mode",
        choices=["historical"],
        default="historical",
        help="Simulation mode (historical is the authoritative entrypoint in Unit 4.9b-1).",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        required=True,
        help="Simulation start date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        required=True,
        help="Simulation end date (YYYY-MM-DD).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed.")
    parser.add_argument("--merchants", type=int, default=5, help="Number of synthetic merchants to simulate.")
    parser.add_argument(
        "--products-per-merchant", type=int, default=8, help="Number of products to create per merchant."
    )
    parser.add_argument(
        "--variants-per-product", type=int, default=3, help="Number of variants to create per product."
    )
    parser.add_argument(
        "--shoppers-per-merchant", type=int, default=50, help="Number of synthetic shoppers to simulate per merchant."
    )
    parser.add_argument(
        "--campaigns-per-merchant",
        type=int,
        default=3,
        help="Number of marketing campaigns to simulate per merchant.",
    )
    return parser.parse_args()


async def _publish_envelopes(envelopes: list[BaseEventEnvelope]) -> None:
    published_counts: dict[str, int] = {
        "merchant": 0,
        "product": 0,
        "shopper": 0,
        "campaign": 0,
    }

    for envelope in envelopes:
        if isinstance(envelope, MerchantEventEnvelope):
            topic = settings.kafka_merchant_events_topic
            key = str(envelope.merchant_id)
            published_counts["merchant"] += 1
        elif isinstance(envelope, ProductEventEnvelope):
            topic = settings.kafka_product_events_topic
            key = f"{envelope.merchant_id}:{envelope.product_id}"
            published_counts["product"] += 1
        elif isinstance(envelope, ShopperEventEnvelope):
            topic = settings.kafka_shopper_events_topic
            key = f"{envelope.merchant_id}:{envelope.shopper_id}"
            published_counts["shopper"] += 1
        elif isinstance(envelope, CampaignEventEnvelope):
            topic = settings.kafka_campaign_events_topic
            key = str(envelope.campaign_id)
            published_counts["campaign"] += 1
        else:
            logger.warning(f"Unknown envelope type: {type(envelope)}")
            continue

        await event_producer.publish(topic, envelope, key=key)

    logger.info(
        "Kafka publishing complete: %d merchant, %d product, %d shopper, %d campaign events (%d total).",
        published_counts["merchant"],
        published_counts["product"],
        published_counts["shopper"],
        published_counts["campaign"],
        len(envelopes),
    )


async def _run(args: argparse.Namespace) -> None:
    start_dt = datetime.combine(args.start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(args.end_date, time.max, tzinfo=timezone.utc)

    if start_dt >= end_dt:
        logger.error(f"start-date ({args.start_date}) must be strictly before end-date ({args.end_date}).")
        sys.exit(1)

    config = HistoricalSimulationConfig(
        start_datetime=start_dt,
        end_datetime=end_dt,
        seed=args.seed,
        merchant_count=args.merchants,
        products_per_merchant=args.products_per_merchant,
        variants_per_product=args.variants_per_product,
        shoppers_per_merchant=args.shoppers_per_merchant,
        campaigns_per_merchant=args.campaigns_per_merchant,
    )

    logger.info(
        "Starting historical timeline generation: %s to %s (seed=%d, merchants=%d, shoppers/m=%d)",
        start_dt.isoformat(),
        end_dt.isoformat(),
        config.seed,
        config.merchant_count,
        config.shoppers_per_merchant,
    )

    orchestrator = HistoricalSimulationOrchestrator(config)
    envelopes = orchestrator.generate_timeline()

    if not envelopes:
        logger.warning("No envelopes generated by orchestrator.")
        return

    first_ts = envelopes[0].event_timestamp.isoformat()
    last_ts = envelopes[-1].event_timestamp.isoformat()
    logger.info(
        "Generated %d chronologically sorted events spanning %s -> %s.",
        len(envelopes),
        first_ts,
        last_ts,
    )

    logger.info("Connecting to Kafka to publish historical events...")
    await event_producer.start()
    try:
        await _publish_envelopes(envelopes)
    finally:
        await event_producer.stop()

    logger.info("Historical simulation generation and publication completed successfully.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = _parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        logger.info("Historical simulation stopped by user.")


if __name__ == "__main__":
    main()

