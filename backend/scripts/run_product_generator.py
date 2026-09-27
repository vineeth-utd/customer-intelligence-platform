"""Standalone entrypoint for the synthetic product catalog event generator.

Loads installed merchants from PostgreSQL through the established DAL boundary,
injects them as lightweight contexts into ProductCatalogGenerator, then
publishes an initial catalog batch followed by periodic lifecycle ticks until
all products are archived or the process is interrupted.

Usage (from backend/):
    uv run python -m scripts.run_product_generator \\
        [--products-per-merchant N] \\
        [--variants-per-product N] \\
        [--interval-seconds S] \\
        [--seed N]
"""

import argparse
import asyncio
import logging
import sys

from app.config.settings import settings
from app.data_access.merchant import list_installed_merchants
from app.db.session import AsyncSessionLocal
from app.generators.product import MerchantContext, ProductCatalogGenerator
from app.kafka.producer import event_producer
from app.schemas.events.envelope import ProductEventEnvelope

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic product catalog event generator.")
    parser.add_argument("--products-per-merchant", type=int, default=settings.product_generator_products_per_merchant)
    parser.add_argument("--variants-per-product", type=int, default=settings.product_generator_variants_per_product)
    parser.add_argument("--interval-seconds", type=float, default=settings.product_generator_tick_interval_seconds)
    parser.add_argument("--seed", type=int, default=settings.product_generator_seed)
    return parser.parse_args()


async def _load_merchant_contexts() -> list[MerchantContext]:
    """Load installed merchants from PostgreSQL and return lightweight contexts."""
    async with AsyncSessionLocal() as session:
        merchants = await list_installed_merchants(session)
    return [MerchantContext(merchant_id=m.merchant_id, merchant_name=m.merchant_name) for m in merchants]



async def _publish_all(envelopes: list[ProductEventEnvelope]) -> None:
    for envelope in envelopes:
        key = f"{envelope.merchant_id}:{envelope.product_id}"
        await event_producer.publish(settings.kafka_product_events_topic, envelope, key=key)


async def _run(
    products_per_merchant: int,
    variants_per_product: int,
    interval_seconds: float,
    seed: int | None,
) -> None:
    merchant_contexts = await _load_merchant_contexts()
    if not merchant_contexts:
        logger.error(
            "No installed merchants found in the database. "
            "Run the merchant generator first so that merchant records exist."
        )
        sys.exit(1)

    logger.info("Loaded %d installed merchant(s) as generator contexts", len(merchant_contexts))

    generator = ProductCatalogGenerator(
        merchant_contexts=merchant_contexts,
        products_per_merchant=products_per_merchant,
        variants_per_product=variants_per_product,
        seed=seed,
    )

    await event_producer.start()
    try:
        initial_envelopes = generator.generate_catalog()
        await _publish_all(initial_envelopes)
        logger.info(
            "Published initial catalog: %d products across %d merchant(s) (%d events total)",
            products_per_merchant * len(merchant_contexts),
            len(merchant_contexts),
            len(initial_envelopes),
        )

        while not generator.all_terminal():
            await asyncio.sleep(interval_seconds)
            envelopes = generator.tick()
            if envelopes:
                await _publish_all(envelopes)
                logger.info("Published %d product lifecycle events", len(envelopes))

        logger.info("All products reached a terminal state; generator run complete")
    finally:
        await event_producer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    try:
        asyncio.run(_run(args.products_per_merchant, args.variants_per_product, args.interval_seconds, args.seed))
    except KeyboardInterrupt:
        logger.info("Product generator stopped by user")


if __name__ == "__main__":
    main()
