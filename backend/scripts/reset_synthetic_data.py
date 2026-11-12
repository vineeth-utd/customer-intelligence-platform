"""Standalone CLI script to cleanly reset all synthetic data in the platform.

Usage (from backend/):
    python scripts/reset_synthetic_data.py [--yes]
"""

import argparse
import asyncio
import logging
import sys

from app.db.session import AsyncSessionLocal
from app.kafka.producer import reset_kafka_topics
from app.services.maintenance import reset_synthetic_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run(reset_kafka: bool = True) -> None:
    async with AsyncSessionLocal() as session:
        await reset_synthetic_data(session)

    if reset_kafka:
        try:
            logger.info("Purging and recreating Kafka event topics...")
            await reset_kafka_topics()
            logger.info("Kafka event topics reset successfully.")
        except Exception as e:
            logger.warning("Could not reset Kafka topics (is Kafka running?): %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset all synthetic data in the Customer Intelligence Platform."
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately with reset.",
    )
    parser.add_argument(
        "--reset-kafka",
        action="store_true",
        default=True,
        help="Purge and recreate Kafka event topics and DLQs (default: True).",
    )
    parser.add_argument(
        "--no-kafka",
        dest="reset_kafka",
        action="store_false",
        help="Skip Kafka topic reset.",
    )
    args = parser.parse_args()

    if not args.yes:
        confirm = input(
            "WARNING: This will erase all synthetic merchants, products, shoppers, campaigns, "
            "events, metrics, journeys, and derived intelligence. Are you sure? [y/N]: "
        )
        if confirm.strip().lower() not in ("y", "yes"):
            logger.info("Reset cancelled by user.")
            sys.exit(0)

    try:
        asyncio.run(_run(reset_kafka=args.reset_kafka))
        logger.info("Synthetic data reset completed successfully.")
    except Exception as e:
        logger.error("Reset failed.", exc_info=e)
        sys.exit(1)


if __name__ == "__main__":
    main()

