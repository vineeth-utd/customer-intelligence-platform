"""Standalone entrypoint for the synthetic shopper behavior generator.

Loads active merchants, products, and variants from PostgreSQL through the established
DAL boundary, injects them as lightweight contexts into ShopperBehaviorGenerator,
and continuously publishes shopper lifecycle events. It periodically reloads the
catalog to reconcile inventory and observe new products without dropping shopper state.

Usage (from backend/):
    uv run python -m scripts.run_shopper_generator \
        [--shoppers-per-merchant N] \
        [--tick-interval-seconds S] \
        [--reload-interval-ticks N] \
        [--seed N]
"""

import argparse
import asyncio
import logging
import sys

from app.config.settings import settings
from app.data_access.product import get_active_merchant_catalogs
from app.db.session import AsyncSessionLocal
from app.generators.shopper import (
    MerchantCatalogContext,
    ProductContext,
    ShopperBehaviorGenerator,
    VariantContext,
)
from app.kafka.producer import event_producer
from app.schemas.events.envelope import ShopperEventEnvelope

logger = logging.getLogger(__name__)

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic shopper behavior generator.")
    parser.add_argument("--shoppers-per-merchant", type=int, default=50)
    parser.add_argument("--tick-interval-seconds", type=float, default=1.0)
    parser.add_argument("--reload-interval-ticks", type=int, default=60)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()

async def _load_merchant_catalogs() -> list[MerchantCatalogContext]:
    """Load the live operational catalog from the database."""
    async with AsyncSessionLocal() as session:
        merchants = await get_active_merchant_catalogs(session)
        
    catalogs = []
    for m in merchants:
        products = []
        for p in m.products:
            variants = [
                VariantContext(variant_id=v.variant_id, price=v.price, inventory_quantity=v.inventory_quantity)
                for v in p.variants
            ]
            if variants:
                products.append(ProductContext(
                    product_id=p.product_id, 
                    product_name=p.product_name,
                    category=p.category,
                    variants=variants
                ))
        enabled_features: set[str] = set()
        
        # Collect entitled features from the active subscription(s)
        for sub in m.subscriptions:
            for pf in sub.plan.plan_features:
                enabled_features.add(pf.feature.feature_key)
                
        # Intersect with explicitly enabled merchant features
        merchant_enabled = {mf.feature.feature_key for mf in m.merchant_features}
        usable_features = enabled_features.intersection(merchant_enabled)
        
        if products:
            catalogs.append(MerchantCatalogContext(
                merchant_id=m.merchant_id, 
                products=products,
                enabled_features=usable_features
            ))
            
    return catalogs

async def _publish_all(envelopes: list[ShopperEventEnvelope]) -> None:
    for env in envelopes:
        key = f"{env.merchant_id}:{env.shopper_id}"
        await event_producer.publish(settings.kafka_shopper_events_topic, env, key=key)

async def _run(
    shoppers_per_merchant: int,
    tick_interval_seconds: float,
    reload_interval_ticks: int,
    seed: int | None,
) -> None:
    generator = ShopperBehaviorGenerator(
        shoppers_per_merchant=shoppers_per_merchant,
        seed=seed,
    )

    catalogs = await _load_merchant_catalogs()
    if not catalogs:
        logger.error(
            "No active merchants with active products found in the database. "
            "Run the merchant and product generators first."
        )
        sys.exit(1)
        
    generator.update_catalog(catalogs)
    logger.info("Loaded %d active merchant catalog(s)", len(catalogs))

    await event_producer.start()
    try:
        ticks = 0
        while True:
            envelopes = generator.tick()
            if envelopes:
                await _publish_all(envelopes)
                logger.info("Published %d shopper events (tick %d)", len(envelopes), ticks)
                
            await asyncio.sleep(tick_interval_seconds)
            ticks += 1
            
            if ticks % reload_interval_ticks == 0:
                logger.info("Reloading catalog from database to reconcile generator state...")
                catalogs = await _load_merchant_catalogs()
                generator.update_catalog(catalogs)
                
    finally:
        await event_producer.stop()

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    try:
        asyncio.run(_run(
            args.shoppers_per_merchant,
            args.tick_interval_seconds,
            args.reload_interval_ticks,
            args.seed,
        ))
    except KeyboardInterrupt:
        logger.info("Shopper generator stopped by user")

if __name__ == "__main__":
    main()
