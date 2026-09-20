"""Standalone entrypoint for the merchant event Kafka consumer.

Runs independently of the FastAPI app: starts the merchant event consumer,
which validates, persists, and business-processes each Merchant event,
marks it processed, and commits its Kafka offset - until interrupted or a
processing failure stops the loop (see MerchantEventConsumer's docstring).

Usage (from backend/):
    uv run python -m scripts.run_merchant_event_consumer
"""

import asyncio
import logging

from app.kafka.consumer import merchant_event_consumer
from app.kafka.producer import event_producer

logger = logging.getLogger(__name__)


async def _run() -> None:
    await event_producer.start()
    try:
        await merchant_event_consumer.start()
        try:
            await merchant_event_consumer.run_forever()
        finally:
            await merchant_event_consumer.stop()
    finally:
        await event_producer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Merchant event consumer stopped by user")


if __name__ == "__main__":
    main()
