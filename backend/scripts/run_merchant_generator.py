"""Standalone entrypoint for the synthetic merchant lifecycle event generator.

Runs independently of the FastAPI app: starts the shared Kafka producer,
publishes an initial synthetic merchant population, then periodically ticks
the generator and publishes whatever events it produces until every merchant
reaches its terminal (uninstalled) state or the process is interrupted.

Usage (from backend/):
    uv run python -m scripts.run_merchant_generator [--population-size N] [--interval-seconds S] [--seed N]
"""

import argparse
import asyncio
import logging

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.data_access.merchant import count_merchants
from app.generators.merchant import MerchantLifecycleGenerator
from app.kafka.producer import event_producer
from app.schemas.events.envelope import MerchantEventEnvelope

logger = logging.getLogger(__name__)

async def _get_existing_merchant_count() -> int:
    async with AsyncSessionLocal() as session:
        return await count_merchants(session)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic merchant lifecycle event generator.")
    parser.add_argument("--population-size", type=int, default=settings.merchant_generator_population_size)
    parser.add_argument("--interval-seconds", type=float, default=settings.merchant_generator_tick_interval_seconds)
    parser.add_argument("--seed", type=int, default=settings.merchant_generator_seed)
    return parser.parse_args()


async def _publish_all(envelopes: list[MerchantEventEnvelope]) -> None:
    for envelope in envelopes:
        await event_producer.publish(settings.kafka_merchant_events_topic, envelope, key=str(envelope.merchant_id))


async def _run(population_size: int, interval_seconds: float, seed: int | None) -> None:
    existing_count = await _get_existing_merchant_count()
    generator = MerchantLifecycleGenerator(population_size=population_size, seed=seed, start_index=existing_count)

    await event_producer.start()
    try:
        initial_envelopes = generator.generate_population()
        await _publish_all(initial_envelopes)
        logger.info("Published initial population of %d merchants (start index %d, %d events)", population_size, existing_count, len(initial_envelopes))

        while not generator.all_terminal():
            await asyncio.sleep(interval_seconds)
            envelopes = generator.tick()
            if envelopes:
                await _publish_all(envelopes)
                logger.info("Published %d merchant events", len(envelopes))

        logger.info("All merchants reached a terminal state; generator run complete")
    finally:
        await event_producer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    try:
        asyncio.run(_run(args.population_size, args.interval_seconds, args.seed))
    except KeyboardInterrupt:
        logger.info("Merchant generator stopped by user")


if __name__ == "__main__":
    main()
