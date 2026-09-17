"""Standalone entrypoint for the merchant event Kafka consumer.

Runs independently of the FastAPI app: starts the merchant event consumer
and persists validated events into merchant_events with their initial
(unprocessed) state until interrupted. Deterministic business-service
routing, operational-table updates, and processed-state completion are not
implemented yet (Unit 3.4); this script only validates and persists.

Usage (from backend/):
    uv run python -m scripts.run_merchant_event_consumer
"""

import asyncio
import logging

from app.kafka.consumer import merchant_event_consumer

logger = logging.getLogger(__name__)


async def _run() -> None:
    await merchant_event_consumer.start()
    try:
        await merchant_event_consumer.run_forever()
    finally:
        await merchant_event_consumer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Merchant event consumer stopped by user")


if __name__ == "__main__":
    main()
